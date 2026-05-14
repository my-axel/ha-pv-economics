"""Pure PV economics calculation helpers.

This module must not import Home Assistant. It is the unit-test surface for
hourly energy, price correlation, yield, and amortization logic.
"""

from __future__ import annotations

from datetime import date
from typing import Any


def calculate_self_consumption(hourly_buckets: list[dict[str, Any]]) -> float:
    """Calculate total self-consumption kWh from hourly production/export data."""
    raise NotImplementedError


def calculate_self_consumption_rate(
    self_consumption_kwh: float,
    production_kwh: float,
) -> float | None:
    """Calculate self-consumption rate from self-consumption and production."""
    raise NotImplementedError


def calculate_self_sufficiency(
    self_consumption_kwh: float,
    grid_import_kwh: float,
) -> float | None:
    """Calculate self-sufficiency from self-consumption and grid import."""
    raise NotImplementedError


def calculate_savings(hourly_buckets: list[dict[str, Any]]) -> float:
    """Calculate electricity savings from hourly or fixed price data."""
    raise NotImplementedError


def calculate_feed_in_revenue(hourly_buckets: list[dict[str, Any]]) -> float:
    """Calculate feed-in revenue from hourly or fixed tariff data."""
    raise NotImplementedError


def calculate_total_yield(
    savings_eur: float,
    feed_in_revenue_eur: float,
    historical_offset: float,
) -> float:
    """Calculate total economic yield."""
    raise NotImplementedError


def calculate_amortization_progress_pct(
    total_yield: float,
    installation_cost: float,
) -> float | None:
    """Calculate amortization progress as a ratio."""
    raise NotImplementedError


def calculate_amortization_date(
    daily_yields: list[dict[str, Any]],
    installation_cost: float,
    total_yield: float,
    min_history_days: int,
    rolling_window_days: int,
    today: date,
) -> date | None:
    """Calculate projected or historical amortization date."""
    raise NotImplementedError
