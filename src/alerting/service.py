"""Alert service: evaluate rules, dedupe via cooldown, dispatch, persist.

This is v2.3/v2.4 (target-price + all-time-low + meaningful-drop), on top of
the dispatch protocol + delivery log from `src/alerting/`. All rules key on
EUR amounts - target uses the tracked product's own ``target_price`` (native
sticker), and all-time-low / meaningful-drop use ``price_eur_equivalent``
(v2.10). The service honors ``alert_cooldown_hours`` per (product, alert type)
and only records a delivery on success so a failed send retries next refresh.

Condition bucketing for ATL/meaningful-drop is intentionally NOT done yet
(``matching/anomaly.py`` also treats all conditions as one pool): see the
v2.11 note in `docs/moon/roadmaps/product_matching.md`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from statistics import median

from sqlalchemy import Engine

from alerting.dispatch import build_dispatchers
from alerting.messages import (
    build_all_time_low_message,
    build_meaningful_drop_message,
    build_target_message,
)
from alerting.models import (
    ALL_TIME_LOW,
    DEFAULT_MINIMUM_TRACKING_AGE_DAYS,
    MEANINGFUL_DROP,
    TARGET_PRICE,
    AlertDelivery,
)
from alerting.observations import (
    ListingHistory,
    listing_histories_for_product,
    product_eur_timeline,
)
from alerting.repository import AlertDeliveryRepository
from alerting.rules import (
    should_fire_all_time_low,
    should_fire_meaningful_drop,
    should_fire_target_alert,
)
from config.settings import Settings, get_settings
from storage.watchlist import TrackedProduct, TrackedProductRepository

logger = logging.getLogger(__name__)

DEFAULT_COOLDOWN_HOURS = 72.0


class AlertingService:
    """Evaluates + delivers alerts for tracked products."""

    def __init__(self, engine: Engine, settings: Settings | None = None) -> None:
        self.engine = engine
        self.settings = settings or get_settings()
        self.deliveries = AlertDeliveryRepository(engine)

    # -- public API ----------------------------------------------------------

    def evaluate_target_price(
        self,
        *,
        tracked_product_id: int,
        current_price: float | None,
        target_price: float | None,
        previous_price: float | None = None,
        product_label: str = "tracked product",
        site_key: str | None = None,
        target_currency: str | None = None,
        as_of: datetime | None = None,
    ) -> list[str]:
        """Evaluate + dispatch the target-price rule for a product-level price."""
        if not should_fire_target_alert(
            current_price=current_price,
            target_price=target_price,
            previous_price=previous_price,
        ):
            return []
        message = build_target_message(
            product_label,
            current_price=float(current_price or 0.0),
            target_price=float(target_price or 0.0),
            currency=target_currency,
        )
        return self._dispatch(
            tracked_product_id=tracked_product_id,
            alert_type=TARGET_PRICE,
            message=message,
            related_price=float(current_price or 0.0),
            target_price=float(target_price or 0.0),
            site_key=site_key,
            as_of=as_of,
        )

    def evaluate_tracked_product(
        self,
        tracked_product_id: int,
        *,
        as_of: datetime | None = None,
    ) -> dict[str, list[str]]:
        """Evaluate every shipped rule for one tracked product; return deliveries.

        Keyed by alert type -> list of delivered channel names. Target-price is
        product-level (best current EUR vs the saved target). all-time-low and
        meaningful-drop are per retailer (that listing's own history), exactly
        as `alerting.md` scopes them. Never raises: each rule is independent
        and dispatch is fail-closed.
        """
        tracked = TrackedProductRepository(self.engine).get(tracked_product_id)
        if tracked is None:
            logger.warning(
                "No tracked product %s; skipping alert evaluation", tracked_product_id
            )
            return {}
        histories = listing_histories_for_product(self.engine, tracked.product_id)
        if not histories:
            return {}

        results: dict[str, list[str]] = {}
        delivered = self._evaluate_target(tracked, histories, as_of=as_of)
        if delivered:
            results[TARGET_PRICE] = delivered
        for alert_type, channels in self._evaluate_listing_rules(
            tracked, histories, as_of=as_of
        ).items():
            if channels:
                results[alert_type] = channels
        return results

    # -- rule drivers --------------------------------------------------------

    def _evaluate_target(
        self,
        tracked: TrackedProduct,
        histories: list[ListingHistory],
        *,
        as_of: datetime | None,
    ) -> list[str]:
        if tracked.target_price is None:
            return []
        timeline = product_eur_timeline(histories)
        if not timeline:
            return []
        current_eur = timeline[-1][1]
        previous_eur = timeline[-2][1] if len(timeline) >= 2 else None
        return self.evaluate_target_price(
            tracked_product_id=tracked.id,
            current_price=current_eur,
            target_price=tracked.target_price,
            previous_price=previous_eur,
            product_label=tracked.query_text,
            target_currency=tracked.target_currency,
            as_of=as_of,
        )

    def _evaluate_listing_rules(
        self,
        tracked: TrackedProduct,
        histories: list[ListingHistory],
        *,
        as_of: datetime | None,
    ) -> dict[str, list[str]]:
        results: dict[str, list[str]] = {}
        for history in histories:
            if len(history.observations) < 2:
                continue
            current = history.observations[-1].eur_amount
            prior_eur = [obs.eur_amount for obs in history.observations[:-1]]

            prior_atl = min(prior_eur)
            if should_fire_all_time_low(
                current_eur=current,
                prior_atl_eur=prior_atl,
                min_percent=float(self.settings.alert_all_time_low_percent) / 100.0,
                min_amount=float(self.settings.alert_all_time_low_min_amount),
            ):
                message = build_all_time_low_message(
                    tracked.query_text,
                    history.site_display_name,
                    history.url,
                    new_price=current,
                    prior_atl=prior_atl,
                    currency="EUR",
                )
                delivered = self._dispatch(
                    tracked_product_id=tracked.id,
                    alert_type=ALL_TIME_LOW,
                    message=message,
                    related_price=current,
                    site_key=history.site_key,
                    as_of=as_of,
                )
                if delivered:
                    results[ALL_TIME_LOW] = results.get(ALL_TIME_LOW, []) + delivered

            if not self._minimum_tracking_age_met(tracked, as_of):
                continue
            window = self._historically_older_eur(history, as_of=as_of)
            if len(window) < 3:
                continue
            baseline_median = median(window)
            if should_fire_meaningful_drop(
                current_eur=current,
                window_eur=window,
                min_percent=float(self.settings.alert_drop_percent) / 100.0,
                min_amount=float(self.settings.alert_drop_min_amount),
            ):
                message = build_meaningful_drop_message(
                    tracked.query_text,
                    history.site_display_name,
                    history.url,
                    new_price=current,
                    baseline_median=baseline_median,
                    currency="EUR",
                )
                delivered = self._dispatch(
                    tracked_product_id=tracked.id,
                    alert_type=MEANINGFUL_DROP,
                    message=message,
                    related_price=current,
                    site_key=history.site_key,
                    as_of=as_of,
                )
                if delivered:
                    results[MEANINGFUL_DROP] = (
                        results.get(MEANINGFUL_DROP, []) + delivered
                    )
        return results

    def _historically_older_eur(
        self, history: ListingHistory, *, as_of: datetime | None
    ) -> list[float]:
        """EUR observations strictly before the current one, within the window."""
        reference = as_of or datetime.now()
        cutoff = reference - timedelta(days=self.settings.alert_rolling_window_days)
        return [
            obs.eur_amount
            for obs in history.observations[:-1]
            if obs.observed_at >= cutoff
        ]

    def _minimum_tracking_age_met(
        self, tracked: TrackedProduct, as_of: datetime | None
    ) -> bool:
        """The rolling-average (meaningful-drop) rule needs product history first."""
        reference = as_of or datetime.now()
        return reference - tracked.created_at >= timedelta(
            days=DEFAULT_MINIMUM_TRACKING_AGE_DAYS
        )

    # -- internal dispatch ---------------------------------------------------

    def _cooldown_hours(self) -> float:
        return float(self.settings.alert_cooldown_hours or DEFAULT_COOLDOWN_HOURS)

    def _dispatch(
        self,
        *,
        tracked_product_id: int,
        alert_type: str,
        message: str,
        related_price: float,
        target_price: float | None = None,
        site_key: str | None = None,
        as_of: datetime | None = None,
    ) -> list[str]:
        """Dispatch ``message`` to enabled channels, deduping via the cooldown.

        Returns the channels actually delivered. A delivery is recorded only on
        success so a failed send can retry on the next refresh.
        """
        recent = self.deliveries.recent_delivery_for(
            tracked_product_id=tracked_product_id,
            alert_type=alert_type,
            within_hours=self._cooldown_hours(),
            as_of=as_of,
        )
        if recent is not None:
            return []

        delivered: list[str] = []
        for dispatcher in build_dispatchers(self.settings):
            if not dispatcher.is_configured():
                logger.info("Channel %s not configured; skipping", dispatcher.name)
                continue
            if dispatcher.send(message):
                self.deliveries.record(
                    AlertDelivery(
                        tracked_product_id=tracked_product_id,
                        alert_type=alert_type,
                        channel=dispatcher.name,
                        message=message,
                        created_at=as_of or datetime.now(),
                        related_price=related_price,
                        target_price=target_price,
                        site_key=site_key,
                    )
                )
                delivered.append(dispatcher.name)
            else:
                logger.warning(
                    "Channel %s failed to deliver; not recorded", dispatcher.name
                )
        return delivered
