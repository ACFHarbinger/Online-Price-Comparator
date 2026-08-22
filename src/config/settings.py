"""Application configuration, loaded from environment / .env file."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from decimal import Decimal
from typing import Any, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

_overrides: ContextVar[dict[str, Any] | None] = ContextVar(
    "online_price_comparator_settings_overrides", default=None
)


class Settings(BaseSettings):
    """Runtime configuration for Online Price Comparator.

    All fields are optional so the tool runs with zero configuration:
    scrapers work without any keys, and unconfigured search-API providers
    are skipped rather than causing a startup failure.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"

    database_path: str = "data/price_comparator.db"
    enabled_scrapers: str = ""

    serpapi_key: str | None = None
    # Issue #40: eBay.de Browse API (OAuth2 client credentials)
    ebay_client_id: str | None = None
    ebay_client_secret: str | None = None
    ebay_marketplace_id: str = "EBAY_DE"
    google_cse_api_key: str | None = None
    google_cse_cx: str | None = None

    request_jitter_fraction: float = 0.20
    retry_max_attempts: int = 2
    retry_initial_backoff_seconds: float = 2.0
    retry_max_backoff_seconds: float = 30.0
    block_circuit_breaker_failures: int = 2
    block_circuit_breaker_cooldown_hours: float = 24.0
    response_cache_ttl_seconds: int = 600
    robots_cache_ttl_hours: float = 24.0

    # Headless-browser fallback (Playwright) for sites whose Cloudflare/
    # similar JS challenge blocks a plain httpx request. Off by default;
    # explicitly allowlisted per site. Renders the page with a plain,
    # honestly-identified browser and nothing more - no stealth plugins,
    # fingerprint spoofing, or CAPTCHA-solving. See
    # docs/moon/roadmaps/scrapers_and_retailers.md.
    browser_fallback_enabled: bool = False
    browser_fallback_sites: str = ""

    # False opens a real, visible browser window instead of a headless one,
    # for sites whose challenge doesn't auto-resolve and needs a human to
    # click through it - a person solving their own challenge, not
    # automated CAPTCHA-solving. The wait is extended accordingly so
    # there's real time to interact with it before the page is captured.
    browser_fallback_headless: bool = True
    browser_fallback_headless_wait_seconds: float = 5.0
    browser_fallback_manual_wait_seconds: float = 45.0

    # v1.7 (docs/moon/roadmaps/settings_and_config.md#runtime-settings---
    # planned-additions-v17) - runtime config only, no behavior reads these
    # yet. They document intent for v2.x work (watchlist scheduling, FX
    # normalization, alerting) that lands on top of this field set.
    display_currency: str = "EUR"
    fx_rate_provider: str = "ecb"
    fx_rate_cache_ttl_hours: int = 24
    default_results_per_source: int = 10
    max_results_per_source: int = 20
    monitoring_enabled: bool = False
    refresh_interval_hours: int = 12
    request_timeout_seconds: float = 15.0
    connect_timeout_seconds: float = 5.0
    default_min_request_interval_seconds: float = 5.0
    alerts_enabled: bool = True
    alert_drop_percent: float = 10.0
    alert_drop_min_amount: Decimal = Decimal("10.00")
    alert_rolling_window_days: int = 7
    alert_all_time_low_percent: float = 2.0
    alert_all_time_low_min_amount: Decimal = Decimal("5.00")
    alert_cooldown_hours: int = 72
    alert_channel: Literal["none", "telegram", "discord", "both"] = "none"
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    discord_webhook_url: str | None = None

    def enabled_scraper_keys(self) -> set[str] | None:
        """Return the configured scraper allowlist, or None to mean "all"."""
        keys = {key.strip() for key in self.enabled_scrapers.split(",") if key.strip()}
        return keys or None

    def browser_fallback_site_keys(self) -> set[str]:
        """Return the set of site keys allowed to use the browser fallback."""
        return {
            key.strip() for key in self.browser_fallback_sites.split(",") if key.strip()
        }


def get_settings() -> Settings:
    """Load settings from the environment / .env file.

    Applies any active in-process override from `override_settings` on top
    of the env-derived values - every scraper/provider calls this fresh
    rather than receiving a `Settings` instance from its caller, so this is
    the one place a per-request override (e.g. the dashboard's "show
    browser" checkbox) can reach them without threading a parameter through
    every layer.
    """
    settings = Settings()
    overrides = _overrides.get()
    if overrides:
        settings = settings.model_copy(update=overrides)
    return settings


@contextmanager
def override_settings(**overrides: Any) -> Iterator[None]:
    """Temporarily override specific `Settings` fields for this context only.

    Every `get_settings()` call made while this context is active (in this
    thread/async task - `ContextVar` does not leak across concurrent
    requests) sees the overridden values; nothing outside it is affected,
    and no `.env`/environment variable is touched.
    """
    token = _overrides.set(overrides)
    try:
        yield
    finally:
        _overrides.reset(token)
