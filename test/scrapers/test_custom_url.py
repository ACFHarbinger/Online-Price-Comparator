"""Tests for single-page custom URL fetcher and parser (v2.15 Tier A)."""

from __future__ import annotations

import httpx
import respx

from scrapers.custom_url import fetch_and_parse_custom_url

HTML_WITH_JSON_LD = """
<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": "AMD Ryzen 7 7800X3D CPU",
        "image": "https://example.com/img.jpg",
        "itemCondition": "https://schema.org/NewCondition",
        "offers": {
            "@type": "Offer",
            "priceCurrency": "EUR",
            "price": "399.99",
            "url": "https://example.com/item/1"
        }
    }
    </script>
</head>
<body><h1>AMD Ryzen 7 7800X3D CPU</h1></body>
</html>
"""

HTML_WITH_META_TAGS = """
<!DOCTYPE html>
<html>
<head>
    <title>Intel Core i7-14700K Desktop Processor</title>
    <meta property="og:title" content="Intel Core i7-14700K Desktop Processor" />
    <meta property="og:price:amount" content="419.00" />
    <meta property="og:price:currency" content="EUR" />
    <meta property="og:image" content="https://example.com/i7.jpg" />
</head>
<body><h1>Intel Core i7-14700K</h1></body>
</html>
"""

HTML_WITHOUT_PRICE = """
<!DOCTYPE html>
<html>
<head><title>Some Article without Price</title></head>
<body><h1>Just a blog post</h1></body>
</html>
"""


@respx.mock
def test_fetch_and_parse_custom_url_json_ld() -> None:
    url = "https://hardware-shop.fr/products/ryzen-7800x3d"
    respx.get(url).mock(return_value=httpx.Response(200, text=HTML_WITH_JSON_LD))

    raw = fetch_and_parse_custom_url(url)
    assert raw is not None
    assert raw.title == "AMD Ryzen 7 7800X3D CPU"
    assert raw.price_text == "399.99"
    assert raw.currency_hint == "EUR"
    assert raw.source == "hardware-shop_fr"
    assert raw.site_display_name == "Hardware-shop.fr"
    assert raw.image_url == "https://example.com/img.jpg"
    assert raw.extra.get("parser_source") == "json_ld"
    assert raw.extra.get("parser_confidence") == 1.0


@respx.mock
def test_fetch_and_parse_custom_url_meta_tags() -> None:
    url = "https://tech-store.de/item/14700k"
    respx.get(url).mock(return_value=httpx.Response(200, text=HTML_WITH_META_TAGS))

    raw = fetch_and_parse_custom_url(url)
    assert raw is not None
    assert raw.title == "Intel Core i7-14700K Desktop Processor"
    assert raw.price_text == "419.00"
    assert raw.currency_hint == "EUR"
    assert raw.source == "tech-store_de"
    assert raw.extra.get("parser_source") == "meta_tags"
    assert raw.extra.get("parser_confidence") == 0.6


@respx.mock
def test_fetch_and_parse_custom_url_no_price() -> None:
    url = "https://blog.com/post-1"
    respx.get(url).mock(return_value=httpx.Response(200, text=HTML_WITHOUT_PRICE))

    raw = fetch_and_parse_custom_url(url)
    assert raw is None


@respx.mock
def test_fetch_and_parse_custom_url_http_error() -> None:
    url = "https://error-shop.com/missing"
    respx.get(url).mock(return_value=httpx.Response(404))

    raw = fetch_and_parse_custom_url(url)
    assert raw is None


@respx.mock
def test_fetch_and_parse_custom_url_refuses_policy_blocked_domain() -> None:
    """Leboncoin is server-side-blocked (see #37) - no HTTP request is even made."""
    route = respx.get("https://www.leboncoin.fr/ad/informatique/12345")

    raw = fetch_and_parse_custom_url("https://www.leboncoin.fr/ad/informatique/12345")

    assert raw is None
    assert not route.called
