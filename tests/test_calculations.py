"""Unit tests for calculations.py pure functions."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from custom_components.pv_economics.calculations import (
    aggregate_daily,
    aggregate_daily_yields,
    aggregate_period_yields,
    calculate_amortization_date,
    calculate_amortization_progress_pct,
    calculate_feed_in_revenue,
    calculate_hourly_self_consumption,
    calculate_savings,
    calculate_self_consumption,
    calculate_self_consumption_rate,
    calculate_self_sufficiency,
    calculate_total_yield,
    compute_hourly_deltas,
    compute_hourly_feed_in,
    compute_hourly_savings,
)

UTC = timezone.utc


def _ts(hour: int) -> datetime:
    """Return a UTC datetime for a fixed test date at the given hour."""
    return datetime(2024, 6, 1, hour, 0, 0, tzinfo=UTC)


def _bucket(hour: int, total: float | None) -> dict:
    return {"start": _ts(hour), "sum": total, "mean": None}


# ---------------------------------------------------------------------------
# compute_hourly_deltas
# ---------------------------------------------------------------------------


def test_compute_hourly_deltas_basic() -> None:
    buckets = [_bucket(0, 100.0), _bucket(1, 101.5), _bucket(2, 103.0)]
    result = compute_hourly_deltas(buckets)
    assert len(result) == 2
    assert result[0] == (_ts(1), 1.5)
    assert result[1] == (_ts(2), 1.5)


def test_compute_hourly_deltas_skips_first_bucket() -> None:
    buckets = [_bucket(0, 50.0), _bucket(1, 52.0)]
    result = compute_hourly_deltas(buckets)
    assert len(result) == 1
    assert result[0][0] == _ts(1)


def test_compute_hourly_deltas_clamps_negative() -> None:
    # Negative delta (e.g. stats rollover edge) must be clamped to 0
    buckets = [_bucket(0, 100.0), _bucket(1, 99.0)]
    result = compute_hourly_deltas(buckets)
    assert result[0][1] == 0.0


def test_compute_hourly_deltas_skips_none_sum() -> None:
    buckets = [_bucket(0, 100.0), {"start": _ts(1), "sum": None, "mean": None}, _bucket(2, 102.0)]
    result = compute_hourly_deltas(buckets)
    # Hour 1 has None predecessor or None current; both adjacent pairs skip
    assert all(kwh >= 0 for _, kwh in result)


def test_compute_hourly_deltas_empty() -> None:
    assert compute_hourly_deltas([]) == []
    assert compute_hourly_deltas([_bucket(0, 10.0)]) == []


# ---------------------------------------------------------------------------
# calculate_hourly_self_consumption
# ---------------------------------------------------------------------------


def test_calculate_hourly_self_consumption_basic() -> None:
    prod = [(_ts(1), 3.0), (_ts(2), 2.0)]
    exp = [(_ts(1), 1.0), (_ts(2), 2.5)]
    result = calculate_hourly_self_consumption(prod, exp)
    # Hour 1: 3 - 1 = 2, hour 2: max(0, 2 - 2.5) = 0
    assert result == [(_ts(1), 2.0), (_ts(2), 0.0)]


def test_calculate_hourly_self_consumption_no_common_timestamps() -> None:
    prod = [(_ts(1), 3.0)]
    exp = [(_ts(2), 1.0)]
    result = calculate_hourly_self_consumption(prod, exp)
    assert result == []


def test_calculate_hourly_self_consumption_export_exceeds_production() -> None:
    prod = [(_ts(1), 1.0)]
    exp = [(_ts(1), 5.0)]
    result = calculate_hourly_self_consumption(prod, exp)
    assert result == [(_ts(1), 0.0)]


# ---------------------------------------------------------------------------
# calculate_self_consumption
# ---------------------------------------------------------------------------


def test_calculate_self_consumption() -> None:
    sc_hourly = [(_ts(1), 2.0), (_ts(2), 1.5), (_ts(3), 0.5)]
    assert calculate_self_consumption(sc_hourly) == pytest.approx(4.0)


def test_calculate_self_consumption_empty() -> None:
    assert calculate_self_consumption([]) == 0.0


# ---------------------------------------------------------------------------
# calculate_self_consumption_rate
# ---------------------------------------------------------------------------


def test_calculate_self_consumption_rate_normal() -> None:
    result = calculate_self_consumption_rate(8.0, 10.0)
    assert result == pytest.approx(0.8)


def test_calculate_self_consumption_rate_zero_production() -> None:
    assert calculate_self_consumption_rate(0.0, 0.0) is None


def test_calculate_self_consumption_rate_full_self_consumption() -> None:
    assert calculate_self_consumption_rate(10.0, 10.0) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# calculate_self_sufficiency
# ---------------------------------------------------------------------------


def test_calculate_self_sufficiency_normal() -> None:
    # sc=8, import=2 → 8/(8+2) = 0.8
    result = calculate_self_sufficiency(8.0, 2.0)
    assert result == pytest.approx(0.8)


def test_calculate_self_sufficiency_zero_denominator() -> None:
    assert calculate_self_sufficiency(0.0, 0.0) is None


def test_calculate_self_sufficiency_fully_self_sufficient() -> None:
    assert calculate_self_sufficiency(10.0, 0.0) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# compute_hourly_savings
# ---------------------------------------------------------------------------


def test_compute_hourly_savings_fixed() -> None:
    sc = [(_ts(1), 2.0), (_ts(2), 3.0)]
    result = compute_hourly_savings(sc, fixed_price_ct=30.0)
    assert result == [(_ts(1), pytest.approx(0.60)), (_ts(2), pytest.approx(0.90))]


def test_compute_hourly_savings_dynamic() -> None:
    sc = [(_ts(1), 2.0), (_ts(2), 3.0)]
    prices = [(_ts(1), 30.0), (_ts(2), 40.0)]
    result = compute_hourly_savings(sc, hourly_prices=prices)
    assert result[0][1] == pytest.approx(0.60)
    assert result[1][1] == pytest.approx(1.20)


def test_compute_hourly_savings_dynamic_missing_price_hour() -> None:
    sc = [(_ts(1), 2.0), (_ts(2), 3.0)]
    prices = [(_ts(1), 30.0)]  # hour 2 price missing
    result = compute_hourly_savings(sc, hourly_prices=prices)
    assert len(result) == 1
    assert result[0][0] == _ts(1)


def test_compute_hourly_savings_raises_without_mode() -> None:
    with pytest.raises(ValueError):
        compute_hourly_savings([(_ts(1), 1.0)])


# ---------------------------------------------------------------------------
# compute_hourly_feed_in
# ---------------------------------------------------------------------------


def test_compute_hourly_feed_in_fixed() -> None:
    exp = [(_ts(1), 4.0)]
    result = compute_hourly_feed_in(exp, fixed_tariff_ct=8.0)
    assert result == [(_ts(1), pytest.approx(0.32))]


def test_compute_hourly_feed_in_dynamic() -> None:
    exp = [(_ts(1), 4.0), (_ts(2), 2.0)]
    tariffs = [(_ts(1), 8.0), (_ts(2), 9.0)]
    result = compute_hourly_feed_in(exp, hourly_tariffs=tariffs)
    assert result[0][1] == pytest.approx(0.32)
    assert result[1][1] == pytest.approx(0.18)


def test_compute_hourly_feed_in_raises_without_mode() -> None:
    with pytest.raises(ValueError):
        compute_hourly_feed_in([(_ts(1), 1.0)])


# ---------------------------------------------------------------------------
# calculate_savings / calculate_feed_in_revenue
# ---------------------------------------------------------------------------


def test_calculate_savings() -> None:
    hourly = [(_ts(1), 1.5), (_ts(2), 2.5)]
    assert calculate_savings(hourly) == pytest.approx(4.0)


def test_calculate_feed_in_revenue() -> None:
    hourly = [(_ts(1), 0.32), (_ts(2), 0.18)]
    assert calculate_feed_in_revenue(hourly) == pytest.approx(0.50)


# ---------------------------------------------------------------------------
# aggregate_daily_yields
# ---------------------------------------------------------------------------


def test_aggregate_daily_yields_single_day() -> None:
    savings = [(_ts(10), 1.0), (_ts(11), 0.5)]
    feed_in = [(_ts(10), 0.3)]
    result = aggregate_daily_yields(savings, feed_in)
    assert len(result) == 1
    assert result[0][0] == date(2024, 6, 1)
    assert result[0][1] == pytest.approx(1.8)


def test_aggregate_daily_yields_multiple_days() -> None:
    day1 = datetime(2024, 6, 1, 10, tzinfo=UTC)
    day2 = datetime(2024, 6, 2, 10, tzinfo=UTC)
    savings = [(day1, 1.0), (day2, 2.0)]
    feed_in = [(day1, 0.5), (day2, 0.3)]
    result = aggregate_daily_yields(savings, feed_in)
    assert result[0] == (date(2024, 6, 1), pytest.approx(1.5))
    assert result[1] == (date(2024, 6, 2), pytest.approx(2.3))


def test_aggregate_daily_yields_sorted() -> None:
    day2 = datetime(2024, 6, 2, 10, tzinfo=UTC)
    day1 = datetime(2024, 6, 1, 10, tzinfo=UTC)
    result = aggregate_daily_yields([(day2, 1.0), (day1, 2.0)], [])
    assert result[0][0] < result[1][0]


# ---------------------------------------------------------------------------
# aggregate_daily
# ---------------------------------------------------------------------------


def test_aggregate_daily_single_hour() -> None:
    result = aggregate_daily([(_ts(10), 1.5)])
    assert result == [(date(2024, 6, 1), pytest.approx(1.5))]


def test_aggregate_daily_multiple_hours_same_day() -> None:
    hourly = [(_ts(8), 1.0), (_ts(12), 2.0), (_ts(18), 0.5)]
    result = aggregate_daily(hourly)
    assert len(result) == 1
    assert result[0][1] == pytest.approx(3.5)


def test_aggregate_daily_multiple_days() -> None:
    day2_ts = datetime(2024, 6, 2, 10, tzinfo=UTC)
    result = aggregate_daily([(_ts(10), 1.0), (day2_ts, 2.0)])
    assert result[0] == (date(2024, 6, 1), pytest.approx(1.0))
    assert result[1] == (date(2024, 6, 2), pytest.approx(2.0))


def test_aggregate_daily_empty() -> None:
    assert aggregate_daily([]) == []


def test_aggregate_daily_timezone_shifts_day_boundary() -> None:
    # 23:30 UTC on June 1 = 01:30 local time on June 2 in UTC+2.
    # With tz=UTC+2 the value must land on June 2, not June 1.
    tz_plus2 = timezone(timedelta(hours=2))
    ts_utc = datetime(2024, 6, 1, 23, 30, tzinfo=UTC)
    result_utc = aggregate_daily([(ts_utc, 1.0)])
    result_local = aggregate_daily([(ts_utc, 1.0)], tz=tz_plus2)
    assert result_utc == [(date(2024, 6, 1), pytest.approx(1.0))]
    assert result_local == [(date(2024, 6, 2), pytest.approx(1.0))]


def test_aggregate_daily_timezone_no_shift_during_day() -> None:
    # 12:00 UTC = 14:00 UTC+2 — same calendar day in both timezones.
    tz_plus2 = timezone(timedelta(hours=2))
    ts_utc = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)
    assert aggregate_daily([(ts_utc, 1.0)], tz=tz_plus2) == [
        (date(2024, 6, 1), pytest.approx(1.0))
    ]


def test_aggregate_daily_yields_equals_combined_aggregate_daily() -> None:
    day2_ts = datetime(2024, 6, 2, 10, tzinfo=UTC)
    savings = [(_ts(10), 1.0), (day2_ts, 2.0)]
    feed_in = [(_ts(10), 0.5), (day2_ts, 0.3)]
    via_yields = aggregate_daily_yields(savings, feed_in)
    via_daily = aggregate_daily(savings + feed_in)
    assert via_yields == via_daily


# ---------------------------------------------------------------------------
# aggregate_period_yields
# ---------------------------------------------------------------------------

# Reference date: Saturday 2024-06-01, ISO week 22 of ISO year 2024.
# ISO week 22 runs Mon 2024-05-27 to Sun 2024-06-02.
_REF_DATE = date(2024, 6, 1)


def test_aggregate_period_yields_today() -> None:
    daily = [(_REF_DATE, 5.0)]
    result = aggregate_period_yields(daily, _REF_DATE)
    assert result["today"] == pytest.approx(5.0)
    assert result["this_week"] == pytest.approx(5.0)
    assert result["this_month"] == pytest.approx(5.0)
    assert result["this_year"] == pytest.approx(5.0)


def test_aggregate_period_yields_same_week_different_month() -> None:
    # May 27 is Monday of ISO week 22 – same week as June 1, but different month.
    daily = [(date(2024, 5, 27), 3.0), (_REF_DATE, 2.0)]
    result = aggregate_period_yields(daily, _REF_DATE)
    assert result["today"] == pytest.approx(2.0)
    assert result["this_week"] == pytest.approx(5.0)   # both days in W22
    assert result["this_month"] == pytest.approx(2.0)  # only June 1 is in June
    assert result["this_year"] == pytest.approx(5.0)


def test_aggregate_period_yields_same_month_different_week() -> None:
    daily = [(date(2024, 6, 15), 4.0)]  # week 24, not week 22
    result = aggregate_period_yields(daily, _REF_DATE)
    assert result["today"] == 0.0
    assert result["this_week"] == 0.0
    assert result["this_month"] == pytest.approx(4.0)
    assert result["this_year"] == pytest.approx(4.0)


def test_aggregate_period_yields_same_year_different_month() -> None:
    daily = [(date(2024, 3, 10), 7.0)]
    result = aggregate_period_yields(daily, _REF_DATE)
    assert result["today"] == 0.0
    assert result["this_week"] == 0.0
    assert result["this_month"] == 0.0
    assert result["this_year"] == pytest.approx(7.0)


def test_aggregate_period_yields_different_year() -> None:
    daily = [(date(2023, 6, 1), 10.0)]
    result = aggregate_period_yields(daily, _REF_DATE)
    assert result == {"today": 0.0, "this_week": 0.0, "this_month": 0.0, "this_year": 0.0}


def test_aggregate_period_yields_empty() -> None:
    result = aggregate_period_yields([], _REF_DATE)
    assert result == {"today": 0.0, "this_week": 0.0, "this_month": 0.0, "this_year": 0.0}


def test_aggregate_period_yields_multiple_entries_sum() -> None:
    # Several days in the same month but different weeks; all count for year+month.
    daily = [
        (date(2024, 6, 1), 1.0),   # today, W22
        (date(2024, 6, 10), 2.0),  # W24
        (date(2024, 6, 20), 3.0),  # W25
    ]
    result = aggregate_period_yields(daily, _REF_DATE)
    assert result["today"] == pytest.approx(1.0)
    assert result["this_week"] == pytest.approx(1.0)
    assert result["this_month"] == pytest.approx(6.0)
    assert result["this_year"] == pytest.approx(6.0)


def test_aggregate_period_yields_iso_week_spans_year_boundary() -> None:
    # ISO week 1 of 2025 starts Mon Dec 30, 2024.
    # today = Jan 2, 2025 (Thursday, ISO week 1 of 2025).
    # Dec 30 is calendar year 2024, so it does NOT count for this_year (2025).
    today = date(2025, 1, 2)
    daily = [
        (date(2024, 12, 30), 5.0),  # ISO W1/2025 but calendar year 2024
        (date(2025, 1, 2), 3.0),    # today
    ]
    result = aggregate_period_yields(daily, today)
    assert result["today"] == pytest.approx(3.0)
    # Dec 30 excluded from this_week because calendar year filter runs first
    assert result["this_week"] == pytest.approx(3.0)
    assert result["this_month"] == pytest.approx(3.0)
    assert result["this_year"] == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# calculate_total_yield
# ---------------------------------------------------------------------------


def test_calculate_total_yield() -> None:
    assert calculate_total_yield(500.0, 200.0, 100.0) == pytest.approx(800.0)


def test_calculate_total_yield_zero_offset() -> None:
    assert calculate_total_yield(500.0, 200.0, 0.0) == pytest.approx(700.0)


# ---------------------------------------------------------------------------
# calculate_amortization_progress_pct
# ---------------------------------------------------------------------------


def test_calculate_amortization_progress_pct_normal() -> None:
    result = calculate_amortization_progress_pct(500.0, 2000.0)
    assert result == pytest.approx(0.25)


def test_calculate_amortization_progress_pct_zero_cost() -> None:
    assert calculate_amortization_progress_pct(500.0, 0.0) is None


def test_calculate_amortization_progress_pct_over_100() -> None:
    result = calculate_amortization_progress_pct(2500.0, 2000.0)
    assert result == pytest.approx(1.25)


# ---------------------------------------------------------------------------
# calculate_amortization_date
# ---------------------------------------------------------------------------

_COMMISSIONING = date(2022, 1, 1)
_TODAY = date(2024, 6, 1)  # 882 days after commissioning


def _daily(day_offset: int, eur: float) -> tuple[date, float]:
    return (date.fromordinal(_COMMISSIONING.toordinal() + day_offset), eur)


def test_amortization_date_system_too_young() -> None:
    # System is only 10 days old (commissioning is 10 days before today)
    young_today = date(2022, 1, 11)
    result = calculate_amortization_date(
        [], 10000.0, 500.0, 0.0, _COMMISSIONING, 60, 365, young_today
    )
    assert result is None


def test_amortization_date_no_daily_data() -> None:
    result = calculate_amortization_date(
        [], 10000.0, 500.0, 0.0, _COMMISSIONING, 60, 365, _TODAY
    )
    assert result is None


def test_amortization_date_negative_avg_yield() -> None:
    daily = [_daily(100, -1.0), _daily(101, -0.5)]
    result = calculate_amortization_date(
        daily, 10000.0, 500.0, 0.0, _COMMISSIONING, 60, 365, _TODAY
    )
    assert result is None


def test_amortization_date_future_projection() -> None:
    # avg daily yield = 1.0 EUR, need 9500 EUR more → 9500 days from today
    daily = [_daily(i, 1.0) for i in range(100, 465)]  # 365 days of data
    result = calculate_amortization_date(
        daily, 10000.0, 500.0, 0.0, _COMMISSIONING, 60, 365, _TODAY
    )
    assert result is not None
    from datetime import timedelta
    assert result == _TODAY + timedelta(days=9500)


def test_amortization_date_already_amortized_in_ha_data() -> None:
    # Total yield = 10500 (>= 10000), break-even should be found in daily data
    # Simulate: days 1-100 each earn 100 EUR (offset 0), cross at day 100
    daily = [_daily(i, 100.0) for i in range(1, 106)]
    result = calculate_amortization_date(
        daily, 10000.0, 10500.0, 0.0, _COMMISSIONING, 60, 365, _TODAY
    )
    # cumulative: 100, 200, ..., 10000 at day 100
    assert result == date.fromordinal(_COMMISSIONING.toordinal() + 100)


def test_amortization_date_already_amortized_by_offset() -> None:
    # historical_offset alone covers the cost
    result = calculate_amortization_date(
        [], 5000.0, 6000.0, 6000.0, _COMMISSIONING, 60, 365, _TODAY
    )
    # Can't pinpoint exact date before HA data → None
    assert result is None


def test_amortization_date_projection_overflow_returns_none() -> None:
    # Tiny avg_daily yield with huge remaining cost → projection past year 9999
    daily = [_daily(i, 0.0001) for i in range(100, 200)]
    result = calculate_amortization_date(
        daily, 1_000_000.0, 0.0, 0.0, _COMMISSIONING, 60, 365, _TODAY
    )
    # days_remaining would be ~10 billion days → past date.max → None
    assert result is None


def test_amortization_date_offset_alone_covers_cost_with_ha_data() -> None:
    # Offset alone >= installation_cost; HA has data but break-even predates tracking
    daily = [_daily(i, 2.0) for i in range(100, 110)]
    result = calculate_amortization_date(
        daily, 5000.0, 5200.0, 5100.0, _COMMISSIONING, 60, 365, _TODAY
    )
    # 5100 >= 5000 → amortised before tracking started, exact date unknown
    assert result is None


def test_amortization_date_rolling_window_capped() -> None:
    # Only 100 days of data, avg = 2.0 EUR/day, need 1000 more EUR
    daily = [_daily(i, 2.0) for i in range(100, 200)]  # 100 days
    result = calculate_amortization_date(
        daily, 10000.0, 9000.0, 0.0, _COMMISSIONING, 60, 365, _TODAY
    )
    assert result is not None
    from datetime import timedelta
    assert result == _TODAY + timedelta(days=500)
