"""Pure PV economics calculation helpers.

This module must not import Home Assistant. It is the unit-test surface for
hourly energy, price correlation, yield, and amortization logic.
"""

from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, tzinfo
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
    tz: tzinfo | None = None,
) -> list[tuple[date, float]]:
    """Aggregate a single hourly series to (local date, total) per day, sorted.

    When tz is provided, timestamps are converted to that timezone before
    extracting the date so that the day boundary matches the local calendar.
    """
    daily: dict[date, float] = defaultdict(float)
    for ts, v in hourly:
        local_ts = ts.astimezone(tz) if tz is not None else ts
        daily[local_ts.date()] += v
    return sorted(daily.items())


def aggregate_daily_yields(
    hourly_savings: list[tuple[datetime, float]],
    hourly_feed_in: list[tuple[datetime, float]],
    tz: tzinfo | None = None,
) -> list[tuple[date, float]]:
    """Return (local date, yield) per calendar day, sorted chronologically."""
    return aggregate_daily(hourly_savings + hourly_feed_in, tz)


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

    Uses ISO weeks (Monday-Sunday). daily_yields dates must already be in the
    local calendar (i.e. produced by aggregate_daily with the local timezone).
    today must be the local date from the coordinator.
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


def aggregate_monthly_yields(
    daily_yields: list[tuple[date, float]],
    n_months: int = 13,
) -> list[dict[str, Any]]:
    """Return monthly yield aggregates for the last n_months, sorted chronologically.

    Each entry: {"month": "YYYY-MM", "yield": float}.
    Includes the current (incomplete) month as the last entry.
    """
    monthly: dict[str, float] = defaultdict(float)
    for day, y in daily_yields:
        monthly[f"{day.year}-{day.month:02d}"] += y
    sorted_months = sorted(monthly)[-n_months:]
    return [{"month": m, "yield": round(monthly[m], 2)} for m in sorted_months]


def compute_hourly_battery_from_power(
    power_stats: list[dict[str, Any]],
    positive_is_charge: bool,
    unit_is_kw: bool = False,
    bucket_hours: float = 1.0,
) -> tuple[list[tuple[datetime, float]], list[tuple[datetime, float]]]:
    """Derive hourly charge and discharge kWh from mean-power statistics.

    Returns (charge_hourly, discharge_hourly) as (datetime, kWh) lists.
    bucket_hours is 1.0 for hourly stats and 5/60 for 5-minute live stats.
    """
    scale = bucket_hours if unit_is_kw else bucket_hours / 1000.0
    charge: list[tuple[datetime, float]] = []
    discharge: list[tuple[datetime, float]] = []
    for bucket in power_stats:
        mean = bucket.get("mean")
        if mean is None:
            continue
        ts = bucket["start"]
        energy_kwh = mean * scale
        if positive_is_charge:
            charge.append((ts, max(0.0, energy_kwh)))
            discharge.append((ts, max(0.0, -energy_kwh)))
        else:
            charge.append((ts, max(0.0, -energy_kwh)))
            discharge.append((ts, max(0.0, energy_kwh)))
    return charge, discharge


def compute_hourly_battery_from_energy(
    charge_buckets: list[dict[str, Any]],
    discharge_buckets: list[dict[str, Any]],
) -> tuple[list[tuple[datetime, float]], list[tuple[datetime, float]]]:
    """Derive hourly charge and discharge kWh from cumulative-sum statistics."""
    return (
        compute_hourly_deltas(charge_buckets),
        compute_hourly_deltas(discharge_buckets),
    )


def adjust_sc_for_battery(
    sc_hourly: list[tuple[datetime, float]],
    charge_hourly: list[tuple[datetime, float]],
) -> list[tuple[datetime, float]]:
    """Subtract battery charging from hourly SC to avoid double-counting."""
    charge_by_ts = dict(charge_hourly)
    return [
        (ts, max(0.0, kwh - charge_by_ts.get(ts, 0.0)))
        for ts, kwh in sc_hourly
    ]


def calculate_amortization_progress_pct(
    total_yield: float,
    installation_cost: float,
) -> float | None:
    """Return amortization ratio (0.0-1.0+). None when installation_cost is zero."""
    if installation_cost == 0.0:
        return None
    return total_yield / installation_cost


def format_time_until(target: date, today: date) -> str | None:
    """Return a human-readable string for the time between today and target.

    Format: "Xy Xm Xd", omitting leading zero components (e.g. "5m 3d", "12d").
    Returns None when target is not in the future.
    """
    if target <= today:
        return None

    total_months = (target.year - today.year) * 12 + (target.month - today.month)

    # Anchor = today advanced by total_months calendar months, clamping the day
    # to the last day of the destination month when today.day doesn't exist there.
    def _advance_months(n: int) -> date:
        m0 = today.month - 1 + n
        y = today.year + m0 // 12
        m = m0 % 12 + 1
        d = min(today.day, monthrange(y, m)[1])
        return date(y, m, d)

    anchor = _advance_months(total_months)
    if anchor > target:
        total_months -= 1
        anchor = _advance_months(total_months)

    remaining_days = (target - anchor).days
    years = total_months // 12
    months = total_months % 12

    parts = []
    if years > 0:
        parts.append(f"{years}y")
    if months > 0:
        parts.append(f"{months}m")
    if remaining_days > 0 or not parts:
        parts.append(f"{remaining_days}d")

    return " ".join(parts)


def calculate_amortization_date(
    daily_yields: list[tuple[date, float]],
    installation_cost: float,
    total_yield: float,
    historical_offset: float,
    rolling_window_days: int,
    today: date,
) -> date | None:
    """Project or find the historical amortization date.

    Returns None when:
    - No daily yield data is available
    - The daily average yield is <= 0
    - The system is already amortized but the exact break-even date predates HA data

    Returns the historical break-even date when total_yield >= installation_cost
    and the crossover is traceable in daily_yields.

    Returns a projected future date otherwise.
    """
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


def _seasonal_monthly_averages(
    monthly_yields_history: list[dict[str, Any]],
    today: date,
) -> dict[int, float] | None:
    """Return per-calendar-month average yield (1=Jan … 12=Dec → EUR).

    Returns None when fewer than 12 complete months of history are available,
    or when not all 12 calendar months are represented.
    The current (incomplete) month is excluded from the calculation.
    """
    current_key = f"{today.year}-{today.month:02d}"
    complete = [e for e in monthly_yields_history if e["month"] != current_key]
    if len(complete) < 12:
        return None

    month_totals: dict[int, list[float]] = defaultdict(list)
    for e in complete:
        month_num = int(e["month"].split("-")[1])
        month_totals[month_num].append(e["yield"])

    if len(month_totals) < 12:
        return None

    return {m: sum(vals) / len(vals) for m, vals in month_totals.items()}


def calculate_monthly_performance_vs_expected(
    monthly_yields_history: list[dict[str, Any]],
    yield_this_month: float,
    today: date,
) -> float | None:
    """Return this month's yield deviation vs. seasonal expectation (%).

    Prorates the expected full-month yield to the number of days elapsed so the
    comparison is fair mid-month. Returns None when fewer than 12 complete months
    of history are available or the expected value is zero.
    """
    seasonal_avgs = _seasonal_monthly_averages(monthly_yields_history, today)
    if seasonal_avgs is None:
        return None

    expected_full_month = seasonal_avgs.get(today.month, 0.0)
    if expected_full_month <= 0:
        return None

    days_in_month = monthrange(today.year, today.month)[1]
    expected_prorated = expected_full_month * (today.day / days_in_month)
    if expected_prorated <= 0:
        return None

    return round((yield_this_month - expected_prorated) / expected_prorated * 100, 1)


def calculate_projected_yield_this_year(
    monthly_yields_history: list[dict[str, Any]],
    yield_this_year: float,
    avg_daily_yield: float | None,
    today: date,
) -> float | None:
    """Return projected total yield for the current calendar year.

    Combines actual year-to-date yield with a seasonal forecast for remaining
    days and months. Falls back to a flat avg_daily_yield projection when fewer
    than 12 complete months of history are available. Returns None when
    avg_daily_yield is unavailable or <= 0.
    """
    if not avg_daily_yield or avg_daily_yield <= 0:
        return None

    seasonal_avgs = _seasonal_monthly_averages(monthly_yields_history, today)
    total = yield_this_year

    # Remaining days in the current month (today itself is already in YTD)
    days_in_current_month = monthrange(today.year, today.month)[1]
    remaining_days_this_month = days_in_current_month - today.day
    if seasonal_avgs:
        daily_rate_this_month = seasonal_avgs[today.month] / days_in_current_month
    else:
        daily_rate_this_month = avg_daily_yield
    total += daily_rate_this_month * remaining_days_this_month

    # Complete future months (month+1 … December)
    for future_month in range(today.month + 1, 13):
        if seasonal_avgs:
            total += seasonal_avgs[future_month]
        else:
            total += avg_daily_yield * monthrange(today.year, future_month)[1]

    return round(total, 2)
