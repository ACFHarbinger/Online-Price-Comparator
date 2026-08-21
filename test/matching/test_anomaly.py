"""Tests for snapshot price-anomaly detection."""

from __future__ import annotations

from matching import detect_anomalies

_CPU_TITLE = "AMD Ryzen 9 9950X3D"
_KIT_TITLE = "AMD Ryzen 9 9950X3D Kit refrigeración líquida + placa base"


def test_n_less_than_two_never_flags() -> None:
    assert detect_anomalies([], []) == []

    single = detect_anomalies([609.82], [_CPU_TITLE])
    assert len(single) == 1
    assert single[0].is_anomalous is False
    assert single[0].reason is None
    assert single[0].basis is None


def test_iqr_high_fence_flags_bundle_price_at_n_ge_4() -> None:
    """The €2531 kit is a high-price outlier under the n>=4 IQR fence."""
    prices = [600.0, 610.0, 620.0, 630.0, 2531.51]
    titles = [_CPU_TITLE, _CPU_TITLE, _CPU_TITLE, _CPU_TITLE, _KIT_TITLE]
    results = detect_anomalies(prices, titles)

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
    assert results[4].basis.startswith("n=5,")


def test_iqr_low_fence_flags_extreme_undercut_at_n_ge_4() -> None:
    prices = [500.0, 510.0, 520.0, 530.0, 200.0]
    titles = [_CPU_TITLE] * 5
    results = detect_anomalies(prices, titles)

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
    results = detect_anomalies(prices, [_CPU_TITLE] * 5)
    assert all(item.is_anomalous is False for item in results)
    assert all(item.reason is None and item.basis is None for item in results)


def test_iqr_requires_both_fence_and_median_multiple() -> None:
    """Exceeding the IQR fence is not enough without the 1.75x / 0.60x median rule."""
    # 150 > high_fence (114) but 150 < 1.75x median (182) -> not a high anomaly.
    high_but_not_1_75x = detect_anomalies(
        [100.0, 102.0, 104.0, 106.0, 150.0],
        [_CPU_TITLE] * 5,
    )
    assert all(item.is_anomalous is False for item in high_but_not_1_75x)

    # 80 < low_fence (92) but 80 > 0.60x median (61.2) -> not a low anomaly.
    low_but_not_0_60x = detect_anomalies(
        [100.0, 102.0, 104.0, 106.0, 80.0],
        [_CPU_TITLE] * 5,
    )
    assert all(item.is_anomalous is False for item in low_but_not_0_60x)


def test_sparse_n3_flags_excluded_term_at_2_5x_median() -> None:
    """n=2/3 cannot use IQR; a 2.5x jump plus a kit/bundle term is flagged."""
    prices = [609.82, 615.00, 2531.51]
    titles = [_CPU_TITLE, _CPU_TITLE, _KIT_TITLE]
    results = detect_anomalies(prices, titles)

    assert [item.is_anomalous for item in results] == [False, False, True]
    assert results[2].reason is not None
    assert "2.5x" in results[2].reason
    assert "excluded term" in results[2].reason
    assert results[2].basis is not None
    assert results[2].basis.startswith("n=3,")


def test_sparse_n2_flags_excluded_term_at_2_5x_median() -> None:
    prices = [609.82, 2531.51]
    titles = [_CPU_TITLE, _KIT_TITLE]
    results = detect_anomalies(prices, titles)

    assert [item.is_anomalous for item in results] == [False, True]
    assert results[1].reason is not None
    assert "excluded term" in results[1].reason
    assert results[1].basis is not None
    assert results[1].basis.startswith("n=2,")


def test_sparse_expensive_exact_sku_without_bundle_signal_is_kept() -> None:
    """A genuinely expensive exact SKU with no kit/bundle term stays visible."""
    prices = [609.82, 615.00, 2531.51]
    titles = [_CPU_TITLE, _CPU_TITLE, _CPU_TITLE]
    results = detect_anomalies(prices, titles)

    assert all(item.is_anomalous is False for item in results)


def test_sparse_bundle_below_2_5x_is_not_flagged() -> None:
    prices = [609.82, 615.00, 800.00]
    titles = [_CPU_TITLE, _CPU_TITLE, _KIT_TITLE]
    results = detect_anomalies(prices, titles)
    assert all(item.is_anomalous is False for item in results)
