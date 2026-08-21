"""v2.10: persist_snapshot stores native sticker plus scrape-time EUR equivalent."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Engine, select

from fx.ecb import override_rates, rates_from_mapping
from models.listing import RawListing
from pipeline.snapshot import persist_snapshot
from storage.schema import price_history


def _listing(
    *,
    source: str,
    url: str,
    price_text: str,
    currency_hint: str,
    display: str,
) -> RawListing:
    return RawListing(
        source=source,
        source_kind="scraper",
        title="AMD Ryzen 9 9950X3D",
        url=url,
        price_text=price_text,
        currency_hint=currency_hint,
        image_url=None,
        site_display_name=display,
        fetched_at=datetime(2026, 8, 21, 12, 0, 0),
    )


def test_persist_snapshot_writes_native_and_eur_columns(
    in_memory_engine: Engine,
) -> None:
    table = rates_from_mapping({"USD": 1.10}, as_of=date(2026, 8, 21))
    listings = [
        _listing(
            source="amazon.es",
            url="https://amazon.es/dp/1",
            price_text="609,82 €",
            currency_hint="EUR",
            display="Amazon.es",
        ),
        _listing(
            source="newegg",
            url="https://newegg.com/p/1",
            price_text="$670.00",
            currency_hint="USD",
            display="Newegg",
        ),
    ]
    with override_rates(table):
        persist_snapshot("AMD Ryzen 9 9950X3D", listings, in_memory_engine)

    with in_memory_engine.connect() as conn:
        rows = conn.execute(
            select(
                price_history.c.currency,
                price_history.c.price_amount,
                price_history.c.price_native,
                price_history.c.currency_native,
                price_history.c.price_eur_equivalent,
                price_history.c.fx_rate_used,
                price_history.c.fx_rate_date,
            ).order_by(price_history.c.currency)
        ).all()

    by_currency = {row.currency: row for row in rows}
    assert set(by_currency) == {"EUR", "USD"}

    eur = by_currency["EUR"]
    assert eur.price_native == eur.price_amount
    assert eur.currency_native == "EUR"
    assert eur.price_eur_equivalent == eur.price_amount
    assert eur.fx_rate_used == 1.0

    usd = by_currency["USD"]
    assert usd.price_native == usd.price_amount
    assert usd.currency_native == "USD"
    assert usd.fx_rate_used == 1.10
    assert usd.fx_rate_date == date(2026, 8, 21)
    assert usd.price_eur_equivalent is not None
    assert abs(usd.price_eur_equivalent - (usd.price_amount / 1.10)) < 1e-9
