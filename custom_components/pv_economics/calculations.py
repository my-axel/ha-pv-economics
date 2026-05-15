"""Pure PV economics calculation helpers.

This module must not import Home Assistant. It is the unit-test surface for
hourly energy, price correlation, yield, and amortization logic.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from math import ceil
from typing import Any


def compute_hourly_deltas(
    buckets: list[dict[str, Any]],
) -> list[tuple[datetime, float]]:
    """Convert cumulative-sum buckets to (start, kwh) pairs.

    Skips the first bucket — it has no predecessor to diff against.
    Negative deltas (sensor resets already handled by HA) are clamped to 0.
    Buckets with None sum values are skipped.
    """
    result: list[tuple[datetime, float]] = []
    for i in range(1, len(buckets)):
        prev_sum = buckets[i - 1].get("sum")
        curr_sum = buckets[i].get("sum")
        if prev_sum is None or curr_sum is None:
            continue
        delta = max(0.0, curr_sum - prev_sum)
        result.append((buckets[i]["start"], delta))
    return result


def calculate_hourly_self_consumption(
    production_deltas: list[tuple[datetime, float]],
    export_deltas: list[tuple[datetime, float]],
) -> list[tuple[datetime, float]]:
    """Return per-hour self-consumption kWh aligned by timestamp.

    Only hours present in both series are included — missing buckets are
    skipped per spec. sc = max(0, production - export) per hour.
    """
    prod_by_ts = dict(production_deltas)
    exp_by_ts = dict(export_deltas)
    common = sorted(set(prod_by_ts) & set(exp_by_ts))
    return [(ts, max(0.0, prod_by_ts[ts] - exp_by_ts[ts])) for ts in common]


def calculate_self_consumption(
    sc_hourly: list[tuple[datetime, float]],
) -> float:
    """Sum hourly self-consumption to total kWh."""
    return sum(kwh for _, kwh in sc_hourly)


def calculate_self_consumption_rate(
    self_consumption_kwh: float,
    production_kwh: float,
) -> float | None:
    """Return self-consumption / production. None when production is zero."""
    if production_kwh == 0.0:
        return None
    return self_consumption_kwh / production_kwh


def calculate_self_sufficiency(
    self_consumption_kwh: float,
    grid_import_kwh: float,
) -> float | None:
    """Return self-consumption / (self-consumption + import). None when zero."""
    denominator = self_consumption_kwh + grid_import_kwh
    if denominator == 0.0:
        return None
    return self_consumption_kwh / denominator


def compute_hourly_savings(
    sc_hourly: list[tuple[datetime, float]],
    *,
    fixed_price_ct: float | None = None,
    hourly_prices: list[tuple[datetime, float]] | None = None,
) -> list[tuple[datetime, float]]:
    """Return per-hour electricity savings (currency unit matches ct/kWh input).

    Prices must be in ct/kWh. Provide exactly one of fixed_price_ct or
    hourly_prices. With hourly_prices, only hours present in both series
    are included.
    """
    if fixed_price_ct is not None:
        price_eur = fixed_price_ct / 100.0
        return [(ts, kwh * price_eur) for ts, kwh in sc_hourly]
    if hourly_prices is not None:
        price_by_ts = dict(hourly_prices)
        return [
            (ts, kwh * price_by_ts[ts] / 100.0)
            for ts, kwh in sc_hourly
            if ts in price_by_ts
        ]
    raise ValueError("Provide exactly one of fixed_price_ct or hourly_prices")


def compute_hourly_feed_in(
    export_deltas: list[tuple[datetime, float]],
    *,
    fixed_tariff_ct: float | None = None,
    hourly_tariffs: list[tuple[datetime, float]] | None = None,
) -> list[tuple[datetime, float]]:
    """Return per-hour feed-in revenue (currency unit matches ct/kWh input).

    Tariffs must be in ct/kWh. Provide exactly one of fixed_tariff_ct or
    hourly_tariffs. With hourly_tariffs, only hours present in both series
    are included.
    """
    if fixed_tariff_ct is not None:
        tariff_eur = fixed_tariff_ct / 100.0
        return [(ts, kwh * tariff_eur) for ts, kwh in export_deltas]
    if hourly_tariffs is not None:
        tariff_by_ts = dict(hourly_tariffs)
        return [
            (ts, kwh * tariff_by_ts[ts] / 100.0)
            for ts, kwh in export_deltas
            if ts in tariff_by_ts
        ]
    raise ValueError("Provide exactly one of fixed_tariff_ct or hourly_tariffs")


def calculate_savings(hourly_savings: list[tuple[datetime, float]]) -> float:
    """Sum hourly savings to total monetary value."""
    return sum(v for _, v in hourly_savings)


def calculate_feed_in_revenue(hourly_feed_in: list[tuple[datetime, float]]) -> float:
    """Sum hourly feed-in revenue to total monetary value."""
    return sum(v for _, v in hourly_feed_in)


def aggregate_daily(
    hourly: list[tuple[datetime, float]],
) -> list[tuple[date, float]]:
    """Aggregate a single hourly series to (UTC date, total) per day, sorted."""
    daily: dict[date, float] = defaultdict(float)
    for ts, v in hourly:
        daily[ts.date()] += v
    return sorted(daily.items())


def aggregate_daily_yields(
    hourly_savings: list[tuple[datetime, float]],
    hourly_feed_in: list[tuple[datetime, float]],
) -> list[tuple[date, float]]:
    """Return (date, yield) per UTC calendar day, sorted chronologically."""
    return aggregate_daily(hourly_savings + hourly_feed_in)


def calculate_total_yield(
    savings_eur: float,
    feed_in_revenue_eur: float,
    historical_offset: float,
) -> float:
    """Total economic yield including pre-integration earnings."""
    return savings_eur + feed_in_revenue_eur + historical_offset


def calculate_average_daily_yield(
    daily_yields: list[tuple[date, float]],
    rolling_window_days: int,
) -> float | None:
    """Return average daily yield over the rolling window. None when no data."""
    if not daily_yields:
        return None
    window = daily_yields[-rolling_window_days:]
    return sum(y for _, y in window) / len(window)


def aggregate_period_yields(
    daily_yields: list[tuple[date, float]],
    today: date,
) -> dict[str, float]:
    """Return yield sums for today, this week, this month, and this year.

    Uses ISO weeks (Monday–Sunday). daily_yields dates are UTC calendar dates;
    today should be the local date from the coordinator.
    """
    today_iso = today.isocalendar()
    yield_today = 0.0
    yield_week = 0.0
    yield_month = 0.0
    yield_year = 0.0
    for day, y in daily_yields:
        if day.year != today.year:
            continue
        yield_year += y
        if day.month == today.month:
            yield_month += y
        day_iso = day.isocalendar()
        if day_iso.year == today_iso.year and day_iso.week == today_iso.week:
            yield_week += y
            if day == today:
                yield_today += y
    return {
        "today": yield_today,
        "this_week": yield_week,
        "this_month": yield_month,
        "this_year": yield_year,
    }


def calculate_amortization_progress_pct(
    total_yield: float,
    installation_cost: float,
) -> float | None:
    """Return amortization ratio (0.0-1.0+). None when installation_cost is zero."""
    if installation_cost == 0.0:
        return None
    return total_yield / installation_cost


def calculate_amortization_date(
    daily_yields: list[tuple[date, float]],
    installation_cost: float,
    total_yield: float,
    historical_offset: float,
    commissioning_date: date,
    min_history_days: int,
    rolling_window_days: int,
    today: date,
) -> date | None:
    """Project or find the historical amortization date.

    Returns None when:
    - The system is younger than min_history_days (checked against commissioning_date)
    - No daily yield data is available
    - The daily average yield is <= 0
    - The system is already amortized but the exact break-even date predates HA data

    Returns the historical break-even date when total_yield >= installation_cost
    and the crossover is traceable in daily_yields.

    Returns a projected future date otherwise.
    """
    system_age_days = (today - commissioning_date).days
    if system_age_days < min_history_days:
        return None

    if total_yield >= installation_cost:
        if historical_offset >= installation_cost:
            # Already amortised before tracking started; exact date unknown.
            return None
        cumulative = historical_offset
        for day, yield_eur in daily_yields:
            cumulative += yield_eur
            if cumulative >= installation_cost:
                return day
        # Break-even predates HA data (offset alone covered it)
        return None

    if not daily_yields:
        return None

    window = daily_yields[-rolling_window_days:]
    window_total = sum(y for _, y in window)
    avg_daily = window_total / len(window)

    if avg_daily <= 0.0:
        return None

    days_remaining = ceil((installation_cost - total_yield) / avg_daily)
    target_ordinal = today.toordinal() + days_remaining
    if target_ordinal > date.max.toordinal():
        # Projection lands past year 9999 — too far out to be meaningful.
        return None
    return date.fromordinal(target_ordinal)
