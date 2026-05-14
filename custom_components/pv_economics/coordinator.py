"""Data update coordinator for PV Economics."""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .calculations import (
    aggregate_daily_yields,
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
from .const import (
    CONF_COMMISSIONING_DATE,
    CONF_ELECTRICITY_PRICE_ENTITY,
    CONF_ELECTRICITY_PRICE_MODE,
    CONF_ELECTRICITY_PRICE_VALUE,
    CONF_FEED_IN_TARIFF_ENTITY,
    CONF_FEED_IN_TARIFF_MODE,
    CONF_FEED_IN_TARIFF_VALUE,
    CONF_GRID_EXPORT_ENTITY,
    CONF_GRID_IMPORT_ENTITY,
    CONF_HISTORICAL_OFFSET,
    CONF_INSTALLATION_COST,
    CONF_MIN_HISTORY_DAYS,
    CONF_PV_PRODUCTION_ENTITY,
    CONF_ROLLING_WINDOW_DAYS,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_HISTORICAL_OFFSET,
    DEFAULT_MIN_HISTORY_DAYS,
    DEFAULT_ROLLING_WINDOW_DAYS,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    TARIFF_MODE_ENTITY,
    VALUE_AMORTIZATION_DATE,
    VALUE_AMORTIZATION_PROGRESS,
    VALUE_AMORTIZATION_PROGRESS_PCT,
    VALUE_FEED_IN_REVENUE,
    VALUE_IS_AMORTIZED,
    VALUE_NET_YIELD,
    VALUE_SELF_CONSUMPTION,
    VALUE_SELF_CONSUMPTION_RATE,
    VALUE_SELF_SUFFICIENCY,
    VALUE_TOTAL_SAVINGS,
    VALUE_TOTAL_YIELD,
)
from .statistics import async_get_hourly_statistics, async_has_statistics

_LOGGER = logging.getLogger(__name__)

_PRICE_FALLBACK_KEY = "_price_fallback"
_TARIFF_FALLBACK_KEY = "_tariff_fallback"


class PVEconomicsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for PV Economics data."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        update_interval_minutes = entry.options.get(
            CONF_UPDATE_INTERVAL_MINUTES,
            DEFAULT_UPDATE_INTERVAL_MINUTES,
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_interval_minutes),
            config_entry=entry,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch statistics and compute PV economics data."""
        cfg = {**self.config_entry.data, **self.config_entry.options}

        commissioning_date = date.fromisoformat(cfg[CONF_COMMISSIONING_DATE])
        installation_cost = float(cfg[CONF_INSTALLATION_COST])
        historical_offset = float(
            cfg.get(CONF_HISTORICAL_OFFSET, DEFAULT_HISTORICAL_OFFSET)
        )
        min_history_days = int(
            cfg.get(CONF_MIN_HISTORY_DAYS, DEFAULT_MIN_HISTORY_DAYS)
        )
        rolling_window_days = int(
            cfg.get(CONF_ROLLING_WINDOW_DAYS, DEFAULT_ROLLING_WINDOW_DAYS)
        )

        start = datetime.combine(commissioning_date, time.min).replace(
            tzinfo=dt_util.UTC
        )
        end = dt_util.utcnow()

        prod_id: str = cfg[CONF_PV_PRODUCTION_ENTITY]
        exp_id: str = cfg[CONF_GRID_EXPORT_ENTITY]
        imp_id: str | None = cfg.get(CONF_GRID_IMPORT_ENTITY)

        price_mode: str = cfg[CONF_ELECTRICITY_PRICE_MODE]
        tariff_mode: str = cfg[CONF_FEED_IN_TARIFF_MODE]
        price_entity: str | None = cfg.get(CONF_ELECTRICITY_PRICE_ENTITY)
        tariff_entity: str | None = cfg.get(CONF_FEED_IN_TARIFF_ENTITY)

        statistic_ids = [prod_id, exp_id]
        if imp_id:
            statistic_ids.append(imp_id)

        price_fallback = False
        tariff_fallback = False

        # Check whether entity-based price/tariff have statistics; warn + flag if not
        if price_mode == TARIFF_MODE_ENTITY and price_entity:
            if not await async_has_statistics(self.hass, price_entity):
                _LOGGER.warning(
                    "No long-term statistics for electricity price entity %s; "
                    "falling back to current state",
                    price_entity,
                )
                price_fallback = True
            else:
                statistic_ids.append(price_entity)

        if tariff_mode == TARIFF_MODE_ENTITY and tariff_entity:
            if not await async_has_statistics(self.hass, tariff_entity):
                _LOGGER.warning(
                    "No long-term statistics for feed-in tariff entity %s; "
                    "falling back to current state",
                    tariff_entity,
                )
                tariff_fallback = True
            else:
                statistic_ids.append(tariff_entity)

        stats = await async_get_hourly_statistics(self.hass, statistic_ids, start, end)

        prod_deltas = compute_hourly_deltas(stats.get(prod_id, []))
        exp_deltas = compute_hourly_deltas(stats.get(exp_id, []))

        sc_hourly = calculate_hourly_self_consumption(prod_deltas, exp_deltas)
        sc_total = calculate_self_consumption(sc_hourly)
        prod_total = sum(kwh for _, kwh in prod_deltas)
        sc_rate = calculate_self_consumption_rate(sc_total, prod_total)

        sc_sufficiency: float | None = None
        if imp_id:
            imp_deltas = compute_hourly_deltas(stats.get(imp_id, []))
            imp_total = sum(kwh for _, kwh in imp_deltas)
            sc_sufficiency = calculate_self_sufficiency(sc_total, imp_total)

        # Savings
        hourly_savings = self._compute_savings(
            sc_hourly,
            cfg,
            stats,
            price_mode,
            price_entity,
            price_fallback,
            sc_total,
        )

        # Feed-in revenue
        hourly_feed_in = self._compute_feed_in(
            exp_deltas,
            cfg,
            stats,
            tariff_mode,
            tariff_entity,
            tariff_fallback,
            sum(kwh for _, kwh in exp_deltas),
        )

        savings_eur = calculate_savings(hourly_savings)
        feed_in_eur = calculate_feed_in_revenue(hourly_feed_in)
        total_yield = calculate_total_yield(savings_eur, feed_in_eur, historical_offset)
        progress_pct = calculate_amortization_progress_pct(
            total_yield, installation_cost
        )

        daily_yields = aggregate_daily_yields(hourly_savings, hourly_feed_in)

        amort_date = calculate_amortization_date(
            daily_yields,
            installation_cost,
            total_yield,
            historical_offset,
            commissioning_date,
            min_history_days,
            rolling_window_days,
            date.today(),
        )

        return {
            VALUE_SELF_CONSUMPTION: round(sc_total, 3),
            VALUE_SELF_CONSUMPTION_RATE: (
                round(sc_rate * 100.0, 1) if sc_rate is not None else None
            ),
            VALUE_SELF_SUFFICIENCY: (
                round(sc_sufficiency * 100.0, 1) if sc_sufficiency is not None else None
            ),
            VALUE_TOTAL_SAVINGS: round(savings_eur, 2),
            VALUE_FEED_IN_REVENUE: round(feed_in_eur, 2),
            VALUE_TOTAL_YIELD: round(total_yield, 2),
            VALUE_NET_YIELD: round(total_yield - installation_cost, 2),
            VALUE_AMORTIZATION_PROGRESS: round(total_yield, 2),
            VALUE_AMORTIZATION_PROGRESS_PCT: (
                round(progress_pct * 100.0, 1) if progress_pct is not None else None
            ),
            VALUE_AMORTIZATION_DATE: amort_date,
            VALUE_IS_AMORTIZED: total_yield >= installation_cost,
            _PRICE_FALLBACK_KEY: price_fallback,
            _TARIFF_FALLBACK_KEY: tariff_fallback,
        }

    def _compute_savings(
        self,
        sc_hourly: list[tuple[datetime, float]],
        cfg: dict[str, Any],
        stats: dict[str, list[dict[str, Any]]],
        price_mode: str,
        price_entity: str | None,
        price_fallback: bool,
        sc_total_kwh: float,
    ) -> list[tuple[datetime, float]]:
        """Return per-hour savings in EUR."""
        if price_mode != TARIFF_MODE_ENTITY:
            return compute_hourly_savings(
                sc_hourly,
                fixed_price_ct=float(cfg[CONF_ELECTRICITY_PRICE_VALUE]),
            )

        if price_fallback or not price_entity:
            # Fall back to current state * total kWh
            state = self.hass.states.get(price_entity or "")
            if (
                price_entity
                and state
                and state.state not in ("unknown", "unavailable")
            ):
                try:
                    current_price = float(state.state)
                    savings_eur = sc_total_kwh * current_price / 100.0
                    return [(sc_hourly[0][0], savings_eur)] if sc_hourly else []
                except ValueError:
                    pass
            return []

        price_buckets = stats.get(price_entity, [])
        hourly_prices = [
            (row["start"], row["mean"])
            for row in price_buckets
            if row.get("mean") is not None
        ]
        return compute_hourly_savings(sc_hourly, hourly_prices=hourly_prices)

    def _compute_feed_in(
        self,
        exp_deltas: list[tuple[datetime, float]],
        cfg: dict[str, Any],
        stats: dict[str, list[dict[str, Any]]],
        tariff_mode: str,
        tariff_entity: str | None,
        tariff_fallback: bool,
        exp_total_kwh: float,
    ) -> list[tuple[datetime, float]]:
        """Return per-hour feed-in revenue in EUR."""
        if tariff_mode != TARIFF_MODE_ENTITY:
            return compute_hourly_feed_in(
                exp_deltas,
                fixed_tariff_ct=float(cfg[CONF_FEED_IN_TARIFF_VALUE]),
            )

        if tariff_fallback or not tariff_entity:
            state = self.hass.states.get(tariff_entity or "")
            if (
                tariff_entity
                and state
                and state.state not in ("unknown", "unavailable")
            ):
                try:
                    current_tariff = float(state.state)
                    revenue_eur = exp_total_kwh * current_tariff / 100.0
                    return [(exp_deltas[0][0], revenue_eur)] if exp_deltas else []
                except ValueError:
                    pass
            return []

        tariff_buckets = stats.get(tariff_entity, [])
        hourly_tariffs = [
            (row["start"], row["mean"])
            for row in tariff_buckets
            if row.get("mean") is not None
        ]
        return compute_hourly_feed_in(exp_deltas, hourly_tariffs=hourly_tariffs)
