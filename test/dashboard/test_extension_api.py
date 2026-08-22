"""Tests for the v2.20 v1 localhost extension-report endpoint."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import Engine

from dashboard.extension_api import register_extension_api
from storage.custom_urls import CustomListingUrl, CustomListingUrlRepository
from storage.watchlist import TrackedProductRepository


def _seed_tracked_custom_url(engine: Engine, query_text: str, url: str) -> None:
    tracked = TrackedProductRepository(engine).get_or_create(query_text)
    CustomListingUrlRepository(engine).add(
        CustomListingUrl(
            tracked_product_id=tracked.id,
            url=url,
            site_key="leboncoin",
            site_display_name="Leboncoin",
            added_at=datetime.now(UTC),
            status="active",
        )
    )


def _client(engine: Engine) -> FlaskClient:
    app = Flask(__name__)
    register_extension_api(app, engine)
    return app.test_client()


def test_extension_endpoint_imports_single_record(
    in_memory_engine: Engine,
) -> None:
    url = "https://www.leboncoin.fr/ad/555"
    query_text = "AMD Ryzen 9 9950X3D"
    _seed_tracked_custom_url(in_memory_engine, query_text, url)

    resp = _client(in_memory_engine).post(
        "/api/extension/import",
        data=json.dumps(
            {
                "records": [
                    {
                        "site_key": "leboncoin",
                        "site_display_name": "Leboncoin",
                        "url": url,
                        "title": "AMD Ryzen 9 9950X3D 9950X3D 16-Core Processor",
                        "price_text": "589,00 €",
                        "currency_hint": "EUR",
                    }
                ]
            }
        ),
        content_type="application/json",
    )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["imported"] == 1
    assert body["products"] == [query_text]
    assert body["skipped"] == []


def test_extension_endpoint_accepts_bare_list(
    in_memory_engine: Engine,
) -> None:
    url = "https://www.leboncoin.fr/ad/666"
    query_text = "AMD Ryzen 9 9950X3D"
    _seed_tracked_custom_url(in_memory_engine, query_text, url)

    resp = _client(in_memory_engine).post(
        "/api/extension/import",
        data=json.dumps(
            [
                {
                    "url": url,
                    "title": "AMD Ryzen 9 9950X3D 9950X3D 16-Core Processor",
                    "price_text": "549,00 €",
                    "currency_hint": "EUR",
                }
            ]
        ),
        content_type="application/json",
    )

    assert resp.status_code == 200
    assert resp.get_json()["imported"] == 1


def test_extension_endpoint_rejects_bad_body(in_memory_engine: Engine) -> None:
    client = _client(in_memory_engine)
    assert client.post("/api/extension/import", data="not json").status_code == 400
    assert (
        client.post(
            "/api/extension/import",
            data=json.dumps({"unexpected": True}),
            content_type="application/json",
        ).status_code
        == 400
    )


def test_extension_endpoint_rejects_non_loopback_request(
    in_memory_engine: Engine,
) -> None:
    """Even if the server were bound to 0.0.0.0, a LAN request must be refused."""
    resp = _client(in_memory_engine).post(
        "/api/extension/import",
        data=json.dumps([]),
        content_type="application/json",
        environ_overrides={"REMOTE_ADDR": "192.168.1.50"},
    )

    assert resp.status_code == 403


def test_extension_endpoint_skips_unattributed(in_memory_engine: Engine) -> None:
    resp = _client(in_memory_engine).post(
        "/api/extension/import",
        data=json.dumps(
            [
                {
                    "url": "https://www.leboncoin.fr/ad/999",
                    "title": "Some Product",
                    "price_text": "10,00 €",
                    "currency_hint": "EUR",
                }
            ]
        ),
        content_type="application/json",
    )

    assert resp.status_code == 200
    assert resp.get_json()["imported"] == 0
    assert len(resp.get_json()["skipped"]) == 1
