"""Manual KuantoKusta hint verification into the shared candidate queue."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Engine

from config.settings import Settings
from pipeline.kuantokusta_verification import verify_kuantokusta_hints_for_product
from scrapers.kuantokusta import RetailerUrlHint
from storage.candidates import CandidateListingRepository
from storage.watchlist import TrackedProductRepository


class _HintSource:
    def __init__(self, hints: list[RetailerUrlHint]) -> None:
        self._hints = hints

    def search(self, query: str, *, limit: int = 20) -> list[RetailerUrlHint]:
        return self._hints[:limit]


def _structured_product_html(title: str, price: str = "499.99") -> str:
    return f"""
    <script type="application/ld+json">
      {{"@type": "Product", "name": "{title}", "url": "/product",
       "image": "/image.jpg", "offers": {{"@type": "Offer",
       "price": "{price}", "priceCurrency": "EUR"}}}}
    </script>
    """


def test_verification_creates_pending_candidate_from_real_retailer_page(
    in_memory_engine: Engine,
) -> None:
    tracked = TrackedProductRepository(in_memory_engine).get_or_create(
        "AMD Ryzen 9 9950X3D"
    )
    now = datetime(2026, 8, 21, tzinfo=UTC)
    hint = RetailerUrlHint(
        title="Misleading aggregator price",
        destination_url="https://www.pcdiga.com/processador/9950x3d",
        discovered_at=now,
    )

    candidates = verify_kuantokusta_hints_for_product(
        tracked.id,
        in_memory_engine,
        Settings(),
        as_of=now,
        hint_sources=[_HintSource([hint])],
        fetch_html=lambda _url, _settings: _structured_product_html(
            "AMD Ryzen 9 9950X3D Processor"
        ),
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.site_key == "pcdiga"
    assert candidate.site_display_name == "PCDIGA"
    assert candidate.url == hint.destination_url
    assert candidate.title == "AMD Ryzen 9 9950X3D Processor"
    assert candidate.price_amount == 499.99
    assert candidate.status == "pending"
    persisted = CandidateListingRepository(in_memory_engine).list_pending(tracked.id)
    assert len(persisted) == 1
    assert persisted[0].id == candidate.id
    assert persisted[0].url == candidate.url
    assert persisted[0].price_amount == candidate.price_amount


def test_verification_never_creates_candidate_from_unmatched_retailer_page(
    in_memory_engine: Engine,
) -> None:
    tracked = TrackedProductRepository(in_memory_engine).get_or_create(
        "AMD Ryzen 9 9950X3D"
    )
    now = datetime(2026, 8, 21, tzinfo=UTC)
    hint = RetailerUrlHint(
        title="AMD Ryzen 9 9950X3D",
        destination_url="https://example.invalid/wrong-product",
        discovered_at=now,
    )

    candidates = verify_kuantokusta_hints_for_product(
        tracked.id,
        in_memory_engine,
        Settings(),
        as_of=now,
        hint_sources=[_HintSource([hint])],
        fetch_html=lambda _url, _settings: _structured_product_html("Gaming chair"),
    )

    assert candidates == []
    assert CandidateListingRepository(in_memory_engine).list_all(tracked.id) == []


def test_verification_skips_duplicate_destination_urls(
    in_memory_engine: Engine,
) -> None:
    tracked = TrackedProductRepository(in_memory_engine).get_or_create(
        "AMD Ryzen 9 9950X3D"
    )
    now = datetime(2026, 8, 21, tzinfo=UTC)
    hint = RetailerUrlHint(
        title="AMD Ryzen 9 9950X3D",
        destination_url="https://www.pcdiga.com/processador/9950x3d",
        discovered_at=now,
    )
    source = _HintSource([hint])

    def fetch(_url: str, _settings: Settings) -> str:
        return _structured_product_html("AMD Ryzen 9 9950X3D")

    first = verify_kuantokusta_hints_for_product(
        tracked.id,
        in_memory_engine,
        Settings(),
        as_of=now,
        hint_sources=[source],
        fetch_html=fetch,
    )
    second = verify_kuantokusta_hints_for_product(
        tracked.id,
        in_memory_engine,
        Settings(),
        as_of=now,
        hint_sources=[source],
        fetch_html=fetch,
    )

    assert len(first) == 1
    assert second == []
