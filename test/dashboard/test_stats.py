"""Unit tests for descriptive price series statistical attributes (v2.19)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from dashboard.stats import (
    coefficient_of_variation,
    compute_price_stats,
    iqr_percent_of_median,
    linear_regression_slope,
)
from storage.repository import (
    SitePricePoint,
    compute_price_trend,
    compute_price_volatility,
)


def test_coefficient_of_variation_sparse_and_edge_cases() -> None:
    assert coefficient_of_variation([]) is None
    assert coefficient_of_variation([100.0]) is None
    assert coefficient_of_variation([100.0, 100.0]) is None
    assert coefficient_of_variation([0.0, 0.0, 0.0]) is None

    # Identical non-zero values -> 0 volatility
    assert coefficient_of_variation([100.0, 100.0, 100.0]) == 0.0

    # Known values: [100, 200, 300] -> mean=200, pstdev=81.649658...
    cv = coefficient_of_variation([100.0, 200.0, 300.0])
    assert cv is not None
    assert cv == pytest.approx(0.408248, abs=0.0001)


def test_iqr_percent_of_median_sparse_and_edge_cases() -> None:
    assert iqr_percent_of_median([]) is None
    assert iqr_percent_of_median([100.0, 200.0]) is None
    assert iqr_percent_of_median([0.0, 0.0, 0.0, 0.0]) is None

    # [100, 100, 100, 100] -> IQR = 0 -> 0.0
    assert iqr_percent_of_median([100.0, 100.0, 100.0, 100.0]) == 0.0

    # [10, 20, 30, 40] -> median=25, q1=17.5, q3=32.5 -> iqr=15 -> 15/25 = 0.60
    iqr = iqr_percent_of_median([10.0, 20.0, 30.0, 40.0])
    assert iqr is not None
    assert iqr == pytest.approx(0.60, abs=0.001)


def test_linear_regression_slope() -> None:
    now = datetime(2026, 8, 21, 12, 0, 0)
    assert linear_regression_slope([]) is None
    assert (
        linear_regression_slope([(now, 100.0), (now + timedelta(days=1), 90.0)]) is None
    )

    # All timestamps identical -> denominator 0 -> None
    points_same_time = [(now, 100.0), (now, 90.0), (now, 80.0)]
    assert linear_regression_slope(points_same_time) is None

    # Price drops 10 EUR per day: 100 -> 90 -> 80 -> 70
    points_down = [
        (now, 100.0),
        (now + timedelta(days=1), 90.0),
        (now + timedelta(days=2), 80.0),
        (now + timedelta(days=3), 70.0),
    ]
    slope = linear_regression_slope(points_down)
    assert slope is not None
    assert slope == pytest.approx(-10.0, abs=0.001)

    # Price rises 5 EUR per day
    points_up = [
        (now, 50.0),
        (now + timedelta(days=1), 55.0),
        (now + timedelta(days=2), 60.0),
    ]
    slope_up = linear_regression_slope(points_up)
    assert slope_up is not None
    assert slope_up == pytest.approx(5.0, abs=0.001)


def test_compute_price_stats_sparse_vs_populated() -> None:
    now = datetime(2026, 8, 21, 12, 0, 0)

    # Sparse points (< MIN_OBSERVATIONS)
    sparse_points = [
        SitePricePoint(
            "amazon.es", "Amazon.es", 450.0, "EUR", now - timedelta(days=10)
        ),
        SitePricePoint(
            "pccomponentes", "PcComponentes", 440.0, "EUR", now - timedelta(days=5)
        ),
    ]
    res_sparse = compute_price_stats(sparse_points, window_days=30, reference=now)
    assert res_sparse.count == 2
    assert res_sparse.coefficient_of_variation is None
    assert res_sparse.trend_per_week is None

    # Populated points (4 points across 3 weeks)
    points = [
        SitePricePoint(
            "amazon.es", "Amazon.es", 500.0, "EUR", now - timedelta(days=21)
        ),
        SitePricePoint(
            "pccomponentes",
            "PcComponentes",
            480.0,
            "EUR",
            now - timedelta(days=14),
        ),
        SitePricePoint("amazon.es", "Amazon.es", 460.0, "EUR", now - timedelta(days=7)),
        SitePricePoint("pccomponentes", "PcComponentes", 440.0, "EUR", now),
        # Point outside 30d window
        SitePricePoint(
            "amazon.es", "Amazon.es", 600.0, "EUR", now - timedelta(days=45)
        ),
    ]
    res = compute_price_stats(points, window_days=30, reference=now)
    assert res.count == 4
    assert res.currency == "EUR"
    assert res.coefficient_of_variation is not None
    assert res.trend_per_week is not None
    # Dropping 20 EUR every 7 days -> trend_per_week should be approx -20.0
    assert res.trend_per_week == pytest.approx(-20.0, abs=0.5)
    assert res.trend_pct_per_week is not None
    assert res.trend_pct_per_week < 0


def test_compute_price_volatility_repository_helper() -> None:
    now = datetime(2026, 8, 21, 12, 0, 0)

    # Less than 4 points -> is_sparse
    obs_sparse = [
        (now - timedelta(days=10), 500.0, "EUR"),
        (now - timedelta(days=5), 480.0, "EUR"),
        (now, 460.0, "EUR"),
    ]
    vol_sparse = compute_price_volatility(obs_sparse, window_days=90)
    assert vol_sparse.is_sparse is True
    assert vol_sparse.cv_percent is None
    assert "not enough history" in vol_sparse.description

    # 4 points
    obs_full = [
        (now - timedelta(days=30), 500.0, "EUR"),
        (now - timedelta(days=20), 500.0, "EUR"),
        (now - timedelta(days=10), 500.0, "EUR"),
        (now, 500.0, "EUR"),
    ]
    vol_full = compute_price_volatility(obs_full, window_days=90)
    assert vol_full.is_sparse is False
    assert vol_full.cv_percent == 0.0
    assert "±0.0%" in vol_full.description


def test_compute_price_trend_repository_helper() -> None:
    now = datetime(2026, 8, 21, 12, 0, 0)

    # Time span < 2 days -> is_sparse
    obs_same_day = [
        (now, 500.0, "EUR"),
        (now + timedelta(hours=1), 490.0, "EUR"),
        (now + timedelta(hours=2), 480.0, "EUR"),
        (now + timedelta(hours=3), 470.0, "EUR"),
    ]
    trend_same_day = compute_price_trend(obs_same_day, window_days=30)
    assert trend_same_day.is_sparse is True
    assert trend_same_day.direction == "sparse"

    # Price decreasing by 10 EUR/day across 4 days -> -70 EUR/week
    obs_down = [
        (now - timedelta(days=3), 500.0, "EUR"),
        (now - timedelta(days=2), 490.0, "EUR"),
        (now - timedelta(days=1), 480.0, "EUR"),
        (now, 470.0, "EUR"),
    ]
    trend_down = compute_price_trend(obs_down, window_days=30)
    assert trend_down.is_sparse is False
    assert trend_down.direction == "down"
    assert trend_down.slope_per_week == pytest.approx(-70.0, abs=0.1)
    assert "↘" in trend_down.description
    assert "/wk" in trend_down.description

    # Price increasing
    obs_up = [
        (now - timedelta(days=3), 400.0, "EUR"),
        (now - timedelta(days=2), 410.0, "EUR"),
        (now - timedelta(days=1), 420.0, "EUR"),
        (now, 430.0, "EUR"),
    ]
    trend_up = compute_price_trend(obs_up, window_days=30)
    assert trend_up.is_sparse is False
    assert trend_up.direction == "up"
    assert "↗" in trend_up.description
