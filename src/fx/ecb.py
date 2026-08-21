"""ECB daily euro reference rates (v2.10).

Fetches https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml and
caches it for ``Settings.fx_rate_cache_ttl_hours``. Rates are quoted as
units of foreign currency per 1 EUR. Conversion to EUR is therefore
``native / rate``. Fail-closed: a fetch/parse failure returns no table so
callers persist native prices with a NULL EUR equivalent rather than
inventing a number.
"""

from __future__ import annotations

import logging
import threading
import xml.etree.ElementTree as ET
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import httpx

from config.settings import get_settings
from fetch.http_client import build_http_client

logger = logging.getLogger(__name__)

ECB_DAILY_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
_ECB_USER_AGENT = (
    "online-price-comparator/0.1 (personal watchlist; ECB eurofxref-daily)"
)

_cache_lock = threading.Lock()
_cached_table: RateTable | None = None
_cached_at: datetime | None = None
_overrides: ContextVar[RateTable | None] = ContextVar(
    "opc_fx_rate_overrides", default=None
)


@dataclass(frozen=True)
class RateTable:
    """One ECB daily snapshot: ``rates[currency]`` = units per 1 EUR."""

    as_of: date
    rates: dict[str, float]
    provider: str = "ecb"


@dataclass(frozen=True)
class Conversion:
    """Native sticker plus scrape-time EUR equivalent (None if no rate)."""

    price_native: float
    currency_native: str
    price_eur_equivalent: float | None
    fx_rate_used: float | None
    fx_rate_date: date | None


def parse_ecb_daily_xml(xml_text: str) -> RateTable:
    """Parse the ECB eurofxref-daily XML into a ``RateTable``.

    EUR is always present at 1.0. Raises ``ValueError`` if the document has
    no dated cube.
    """
    root = ET.fromstring(xml_text)
    as_of: date | None = None
    rates: dict[str, float] = {}
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        if tag != "Cube":
            continue
        time_attr = element.attrib.get("time")
        currency = element.attrib.get("currency")
        rate_attr = element.attrib.get("rate")
        if time_attr:
            as_of = date.fromisoformat(time_attr)
            continue
        if currency and rate_attr:
            try:
                rates[currency.strip().upper()] = float(rate_attr)
            except ValueError:
                continue
    if as_of is None:
        raise ValueError("ECB daily XML is missing a Cube time attribute")
    rates["EUR"] = 1.0
    return RateTable(as_of=as_of, rates=rates, provider="ecb")


def convert_to_eur(
    amount: float,
    currency: str,
    *,
    table: RateTable | None = None,
) -> Conversion:
    """Convert a native amount to EUR using an ECB rate table.

    EUR identity conversion never requires a network fetch. Other currencies
    use ``table`` if given, else the process cache / ECB fetch. Unknown or
    missing rates leave ``price_eur_equivalent`` NULL.
    """
    code = currency.strip().upper() or "EUR"
    if table is None:
        table = _overrides.get()
    if code == "EUR":
        rate_date = table.as_of if table is not None else datetime.now(UTC).date()
        return Conversion(amount, "EUR", amount, 1.0, rate_date)

    if table is None:
        table = get_ecb_rates()
    if table is None:
        return Conversion(amount, code, None, None, None)
    per_eur = table.rates.get(code)
    if per_eur is None or per_eur <= 0:
        logger.warning(
            "No ECB rate for %s on %s; storing native only", code, table.as_of
        )
        return Conversion(amount, code, None, None, None)
    return Conversion(amount, code, amount / per_eur, per_eur, table.as_of)


def get_ecb_rates() -> RateTable | None:
    """Return the cached ECB table, fetching it if the TTL has expired."""
    global _cached_table, _cached_at
    override = _overrides.get()
    if override is not None:
        return override

    settings = get_settings()
    ttl = timedelta(hours=max(1, settings.fx_rate_cache_ttl_hours))
    now = datetime.now(UTC)
    with _cache_lock:
        if (
            _cached_table is not None
            and _cached_at is not None
            and now - _cached_at < ttl
        ):
            return _cached_table

    table = _fetch_ecb_rates()
    with _cache_lock:
        if table is None:
            return _cached_table
        _cached_table = table
        _cached_at = now
    return table


def clear_rate_cache() -> None:
    """Drop the process-wide ECB cache (tests)."""
    global _cached_table, _cached_at
    with _cache_lock:
        _cached_table = None
        _cached_at = None


@contextmanager
def override_rates(table: RateTable) -> Iterator[None]:
    """Use a fixed rate table for this context (no HTTP)."""
    token = _overrides.set(table)
    try:
        yield
    finally:
        _overrides.reset(token)


def _fetch_ecb_rates() -> RateTable | None:
    try:
        with build_http_client(user_agent=_ECB_USER_AGENT) as client:
            response = client.get(ECB_DAILY_URL)
    except httpx.HTTPError:
        logger.warning(
            "ECB eurofxref fetch failed; EUR equivalent will be NULL", exc_info=True
        )
        return None
    if response.status_code != 200:
        logger.warning(
            "ECB eurofxref HTTP %s; EUR equivalent will be NULL",
            response.status_code,
        )
        return None
    try:
        return parse_ecb_daily_xml(response.text)
    except (ET.ParseError, ValueError, TypeError):
        logger.warning(
            "ECB eurofxref XML unusable; EUR equivalent will be NULL", exc_info=True
        )
        return None


def rates_from_mapping(
    rates: Mapping[str, float], *, as_of: date, provider: str = "ecb"
) -> RateTable:
    """Build a ``RateTable`` from an in-memory mapping (tests)."""
    normalized = {code.strip().upper(): float(rate) for code, rate in rates.items()}
    normalized["EUR"] = 1.0
    return RateTable(as_of=as_of, rates=normalized, provider=provider)
