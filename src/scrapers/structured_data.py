"""Schema.org Product/Offer extraction shared by scraper adapters."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import cast

from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class StructuredProduct:
    """Fields needed to turn a schema.org Product into a raw listing."""

    title: str
    price_text: str
    currency: str | None
    url: str
    image_url: str | None


def extract_structured_products(soup: BeautifulSoup) -> list[StructuredProduct]:
    """Return valid Product/Offer entries from JSON-LD scripts.

    A malformed script or incomplete Product is ignored so callers can fall
    through to their existing CSS parser.
    """
    products: list[StructuredProduct] = []
    for script in soup.select('script[type="application/ld+json"]'):
        raw = script.string or script.get_text()
        if not raw.strip():
            continue
        try:
            payload: object = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            LOGGER.debug("ignoring malformed JSON-LD", exc_info=True)
            continue
        for node in _object_nodes(payload):
            product = _parse_product(node)
            if product is not None:
                products.append(product)
    return products


def _object_nodes(value: object) -> list[dict[str, object]]:
    if isinstance(value, list):
        nodes: list[dict[str, object]] = []
        for item in value:
            nodes.extend(_object_nodes(item))
        return nodes
    if not isinstance(value, dict):
        return []
    node = cast(dict[str, object], value)
    graph = node.get("@graph")
    if graph is not None:
        return [node, *_object_nodes(graph)]
    return [node]


def _parse_product(node: dict[str, object]) -> StructuredProduct | None:
    if not _has_type(node.get("@type"), "Product"):
        return None
    title = _text(node.get("name"))
    product_url = _text(node.get("url"))
    image_url = _image_url(node.get("image"))
    for offer in _offers(node.get("offers")):
        price = _offer_price(offer)
        url = product_url or _text(offer.get("url"))
        if title and price and url:
            return StructuredProduct(
                title=title,
                price_text=price,
                currency=_text(offer.get("priceCurrency")),
                url=url,
                image_url=image_url,
            )
    return None


def _offers(value: object) -> list[dict[str, object]]:
    candidates = value if isinstance(value, list) else [value]
    offers: list[dict[str, object]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        offer = cast(dict[str, object], candidate)
        if _has_type(offer.get("@type"), "Offer") or "price" in offer:
            offers.append(offer)
    return offers


def _offer_price(offer: dict[str, object]) -> str:
    price = _text(offer.get("price"))
    if price:
        return price
    specification = offer.get("priceSpecification")
    if not isinstance(specification, dict):
        return ""
    return _text(cast(dict[str, object], specification).get("price"))


def _has_type(value: object, expected: str) -> bool:
    if isinstance(value, str):
        return value.rsplit("/", 1)[-1] == expected
    if isinstance(value, list):
        return any(_has_type(item, expected) for item in value)
    return False


def _text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, int | float) and not isinstance(value, bool):
        return str(value)
    return ""


def _image_url(value: object) -> str | None:
    if isinstance(value, list):
        for item in value:
            image = _image_url(item)
            if image:
                return image
        return None
    if isinstance(value, dict):
        image_object = cast(dict[str, object], value)
        return (
            _text(image_object.get("url"))
            or _text(image_object.get("contentUrl"))
            or None
        )
    return _text(value) or None
