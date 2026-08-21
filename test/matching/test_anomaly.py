"""Tests for snapshot price-anomaly detection."""

from __future__ import annotations

from collections.abc import Sequence

from matching import AnomalyResult, detect_anomalies

_CPU_TITLE = "AMD Ryzen 9 9950X3D"
_KIT_TITLE = "AMD Ryzen 9 9950X3D Kit refrigeración líquida + placa base"
_NEW = "new"
_USED = "used"


def _detect(
    prices: Sequence[float | None],
    titles: Sequence[str],
    conditions: Sequence[str | None] | None = None,
) -> list[AnomalyResult]:
    resolved = conditions if conditions is not None else [_NEW] * len(prices)
    return detect_anomalies(prices, titles, conditions=resolved)


def test_n_less_than_two_never_flags() -> None:
    assert _detect([], []) == []

    single = _detect([609.82], [_CPU_TITLE])
    assert len(single) == 1
    assert single[0].is_anomalous is False
    assert single[0].reason is None
    assert single[0].basis is None


def test_iqr_high_fence_flags_bundle_price_at_n_ge_4() -> None:
    """The €2531 kit is a high-price outlier under the n>=4 IQR fence."""
    prices = [600.0, 610.0, 620.0, 630.0, 2531.51]
    titles = [_CPU_TITLE, _CPU_TITLE, _CPU_TITLE, _CPU_TITLE, _KIT_TITLE]
    results = _detect(prices, titles)

    assert [item.is_anomalous for item in results] == [
        False,
        False,
        False,
        False,
        True,
    ]
    assert results[4].reason is not None
    assert "high-price outlier" in results[4].reason
    assert results[4].basis is not None
    assert "condition=new" in results[4].basis
    assert results[4].basis.startswith("n=5,")


def test_iqr_low_fence_flags_extreme_undercut_at_n_ge_4() -> None:
    prices = [500.0, 510.0, 520.0, 530.0, 200.0]
    titles = [_CPU_TITLE] * 5
    results = _detect(prices, titles)

    assert [item.is_anomalous for item in results] == [
        False,
        False,
        False,
        False,
        True,
    ]
    assert results[4].reason is not None
    assert "low-price outlier" in results[4].reason


def test_iqr_clustered_prices_are_not_flagged() -> None:
    prices = [100.0, 105.0, 110.0, 115.0, 120.0]
    results = _detect(prices, [_CPU_TITLE] * 5)
    assert all(item.is_anomalous is False for item in results)
    assert all(item.reason is None and item.basis is None for item in results)


def test_iqr_requires_both_fence_and_median_multiple() -> None:
    """Exceeding the IQR fence is not enough without the 1.75x / 0.60x median rule."""
    high_but_not_1_75x = _detect(
        [100.0, 102.0, 104.0, 106.0, 150.0],
        [_CPU_TITLE] * 5,
    )
    assert all(item.is_anomalous is False for item in high_but_not_1_75x)

    low_but_not_0_60x = _detect(
        [100.0, 102.0, 104.0, 106.0, 80.0],
        [_CPU_TITLE] * 5,
    )
    assert all(item.is_anomalous is False for item in low_but_not_0_60x)


def test_sparse_bucket_never_auto_hides() -> None:
    """n<4 in a condition bucket never auto-hides, even with a kit title."""
    prices = [609.82, 615.00, 2531.51]
    titles = [_CPU_TITLE, _CPU_TITLE, _KIT_TITLE]
    results = _detect(prices, titles)
    assert all(item.is_anomalous is False for item in results)

    n2 = _detect([609.82, 2531.51], [_CPU_TITLE, _KIT_TITLE])
    assert all(item.is_anomalous is False for item in n2)


def test_used_undercut_is_not_flagged_against_new_median() -> None:
    """A used listing is its own bucket and cannot trip the new-stock IQR fence."""
    prices = [600.0, 610.0, 620.0, 630.0, 200.0]
    titles = [_CPU_TITLE] * 5
    conditions = [_NEW, _NEW, _NEW, _NEW, _USED]
    results = _detect(prices, titles, conditions)
    assert [item.is_anomalous for item in results] == [
        False,
        False,
        False,
        False,
        False,
    ]


def test_iqr_runs_independently_per_condition_bucket() -> None:
    new_prices = [600.0, 610.0, 620.0, 630.0, 2531.51]
    used_prices = [200.0, 210.0, 220.0, 230.0, 50.0]
    prices = new_prices + used_prices
    titles = [_CPU_TITLE] * 10
    conditions = [_NEW] * 5 + [_USED] * 5
    results = _detect(prices, titles, conditions)
    assert [item.is_anomalous for item in results[:5]] == [
        False,
        False,
        False,
        False,
        True,
    ]
    assert results[4].basis is not None
    assert "condition=new" in results[4].basis
    assert [item.is_anomalous for item in results[5:]] == [
        False,
        False,
        False,
        False,
        True,
    ]
    assert results[9].basis is not None
    assert "condition=used" in results[9].basis


def test_unknown_and_missing_eur_never_enter_the_sample() -> None:
    prices: list[float | None] = [600.0, 610.0, 620.0, 630.0, 100.0, None]
    titles = [_CPU_TITLE] * 6
    conditions: list[str | None] = [_NEW, _NEW, _NEW, _NEW, "unknown", _NEW]
    results = _detect(prices, titles, conditions)
    assert results[4].is_anomalous is False
    assert results[5].is_anomalous is False
    # The four new prices are clustered; missing EUR and unknown are skipped
    # so n=4 new does not include 100.0.
    assert all(item.is_anomalous is False for item in results[:4])
