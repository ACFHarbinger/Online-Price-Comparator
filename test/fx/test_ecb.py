"""Tests for ECB daily-rate parsing, conversion, and fail-closed fetch."""

from __future__ import annotations

from datetime import date

import httpx
import pytest
import respx

from fx.ecb import (
    ECB_DAILY_URL,
    clear_rate_cache,
    convert_to_eur,
    get_ecb_rates,
    override_rates,
    parse_ecb_daily_xml,
    rates_from_mapping,
)

_SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
 xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
  <Cube>
    <Cube time="2026-08-21">
      <Cube currency="USD" rate="1.1000"/>
      <Cube currency="GBP" rate="0.8500"/>
    </Cube>
  </Cube>
</gesmes:Envelope>
"""


def test_parse_ecb_daily_xml_extracts_dated_rates() -> None:
    table = parse_ecb_daily_xml(_SAMPLE_XML)
    assert table.as_of == date(2026, 8, 21)
    assert table.provider == "ecb"
    assert table.rates["EUR"] == 1.0
    assert table.rates["USD"] == 1.1
    assert table.rates["GBP"] == 0.85


def test_convert_eur_is_identity() -> None:
    conversion = convert_to_eur(609.82, "eur")
    assert conversion.currency_native == "EUR"
    assert conversion.price_native == 609.82
    assert conversion.price_eur_equivalent == 609.82
    assert conversion.fx_rate_used == 1.0
    assert conversion.fx_rate_date is not None


def test_convert_usd_divides_by_ecb_rate() -> None:
    table = rates_from_mapping({"USD": 1.10}, as_of=date(2026, 8, 21))
    conversion = convert_to_eur(110.0, "USD", table=table)
    assert conversion.price_eur_equivalent == pytest.approx(100.0)
    assert conversion.fx_rate_used == 1.10
    assert conversion.fx_rate_date == date(2026, 8, 21)


def test_convert_unknown_currency_leaves_eur_null() -> None:
    table = rates_from_mapping({"USD": 1.10}, as_of=date(2026, 8, 21))
    conversion = convert_to_eur(50.0, "TRY", table=table)
    assert conversion.price_native == 50.0
    assert conversion.currency_native == "TRY"
    assert conversion.price_eur_equivalent is None
    assert conversion.fx_rate_used is None


def test_override_rates_avoids_http() -> None:
    table = rates_from_mapping({"GBP": 0.8}, as_of=date(2026, 1, 1))
    with override_rates(table):
        conversion = convert_to_eur(80.0, "GBP")
    assert conversion.price_eur_equivalent == 100.0


@respx.mock
def test_get_ecb_rates_parses_mocked_xml() -> None:
    clear_rate_cache()
    respx.get(ECB_DAILY_URL).mock(return_value=httpx.Response(200, text=_SAMPLE_XML))
    table = get_ecb_rates()
    assert table is not None
    assert table.as_of == date(2026, 8, 21)
    assert table.rates["USD"] == 1.1
    clear_rate_cache()


@respx.mock
def test_get_ecb_rates_fail_closed_on_http_error() -> None:
    clear_rate_cache()
    respx.get(ECB_DAILY_URL).mock(return_value=httpx.Response(503, text="nope"))
    assert get_ecb_rates() is None
    conversion = convert_to_eur(10.0, "USD")
    assert conversion.price_eur_equivalent is None
    clear_rate_cache()
