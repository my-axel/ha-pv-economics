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
    aggregate_daily,
    aggregate_daily_yields,
    aggregate_period_yields,
    calculate_amortization_date,
    calculate_amortization_progress_pct,
    calculate_average_daily_yield,
    calculate_feed_in_revenue,
    calculate_hourly_self_consumption,
    calculate_savings,
    calculate_self_consumption,
    calculate_self_consumption_rate,
    calculate_self_sufficiency,
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
    CONF_HISTORICAL_FEED_IN,
    CONF_HISTORICAL_SAVINGS,
    CONF_INSTALLATION_COST,
    CONF_MIN_HISTORY_DAYS,
    CONF_PV_PRODUCTION_ENTITY,
    CONF_ROLLING_WINDOW_DAYS,
    CONF_STATISTICS_START_DATE,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_HISTORICAL_FEED_IN,
    DEFAULT_HISTORICAL_SAVINGS,
    DEFAULT_MIN_HISTORY_DAYS,
    DEFAULT_ROLLING_WINDOW_DAYS,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    TARIFF_MODE_ENTITY,
    VALUE_AMORTIZATION_DATE,
    VALUE_AMORTIZATION_PROGRESS_PCT,
    VALUE_AVERAGE_DAILY_YIELD,
    VALUE_DAYS_TO_AMORTIZATION,
    VALUE_FEED_IN_REVENUE,
    VALUE_IS_AMORTIZED,
    VALUE_NET_YIELD,
    VALUE_SELF_CONSUMPTION,
    VALUE_SELF_CONSUMPTION_RATE,
    VALUE_SELF_SUFFICIENCY,
    VALUE_SYSTEM_AGE_DAYS,
    VALUE_TOTAL_SAVINGS,
    VALUE_TOTAL_YIELD,
    VALUE_FEED_IN_THIS_MONTH,
    VALUE_FEED_IN_THIS_WEEK,
    VALUE_FEED_IN_THIS_YEAR,
    VALUE_FEED_IN_TODAY,
    VALUE_SAVINGS_THIS_MONTH,
    VALUE_SAVINGS_THIS_WEEK,
    VALUE_SAVINGS_THIS_YEAR,
    VALUE_SAVINGS_TODAY,
    VALUE_YIELD_THIS_MONTH,
    VALUE_YIELD_THIS_WEEK,
    VALUE_YIELD_THIS_YEAR,
    VALUE_YIELD_TODAY,
)
from .statistics import async_get_hourly_statistics, async_has_statistics

_LOGGER = logging.getLogger(__name__)

_PRICE_FALLBACK_KEY = "_price_fallback"
_TARIFF_FALLBACK_KEY = "_tariff_fallback"
_SAVINGS_FROM_STATS_KEY = "_savings_from_statistics"
_FEED_IN_FROM_STATS_KEY = "_feed_in_from_statistics"
_HIST_SAVINGS_KEY = "_historical_savings"
_HIST_FEED_IN_KEY = "_historical_feed_in"
_STATS_FIRST_DATE_KEY = "_statistics_first_date"
_STATS_LAST_DATE_KEY = "_statistics_last_date"
_STATS_HOURS_KEY = "_statistics_hours"


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
        statistics_start = date.fromisoformat(cfg[CONF_STATISTICS_START_DATE])
        installation_cost = float(cfg[CONF_INSTALLATION_COST])
        historical_savings_eur = float(
            cfg.get(CONF_HISTORICAL_SAVINGS, DEFAULT_HISTORICAL_SAVINGS)
        )
        historical_feed_in_eur = float(
            cfg.get(CONF_HISTORICAL_FEED_IN, DEFAULT_HISTORICAL_FEED_IN)
        )
        min_history_days = int(
            cfg.get(CONF_MIN_HISTORY_DAYS, DEFAULT_MIN_HISTORY_DAYS)
        )
        rolling_window_days = int(
            cfg.get(CONF_ROLLING_WINDOW_DAYS, DEFAULT_ROLLING_WINDOW_DAYS)
        )

        start = datetime.combine(statistics_start, time.min).replace(
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
        sc_timestamps = {ts for ts, _ in sc_hourly}

        sc_total = calculate_self_consumption(sc_hourly)
        # Use only production hours that fall within the SC period so that
        # the denominator covers the same timespan as the numerator.
        prod_in_sc_period = sum(kwh for ts, kwh in prod_deltas if ts in sc_timestamps)
        sc_rate = calculate_self_consumption_rate(sc_total, prod_in_sc_period)

        sc_sufficiency: float | None = None
        if imp_id:
            imp_deltas = compute_hourly_deltas(stats.get(imp_id, []))
            # Same period constraint: only count import during SC hours.
            imp_in_sc_period = sum(kwh for ts, kwh in imp_deltas if ts in sc_timestamps)
            sc_sufficiency = calculate_self_sufficiency(sc_total, imp_in_sc_period)

        # Savings
        hourly_savings = self._compute_savings(
            sc_hourly,
            cfg,
            stats,
            price_mode,
            price_entity,
            price_fallback,
        )

        # Feed-in revenue
        hourly_feed_in = self._compute_feed_in(
            exp_deltas,
            cfg,
            stats,
            tariff_mode,
            tariff_entity,
            tariff_fallback,
        )

        savings_eur = calculate_savings(hourly_savings)
        feed_in_eur = calculate_feed_in_revenue(hourly_feed_in)

        savings_all = savings_eur + historical_savings_eur
        feed_in_all = feed_in_eur + historical_feed_in_eur
        total_yield = savings_all + feed_in_all
        historical_offset_combined = historical_savings_eur + historical_feed_in_eur

        progress_pct = calculate_amortization_progress_pct(
            total_yield, installation_cost
        )

        daily_yields = aggregate_daily_yields(hourly_savings, hourly_feed_in)
        today = date.today()
        system_age_days = (today - commissioning_date).days
        period_yields = aggregate_period_yields(daily_yields, today)
        period_savings = aggregate_period_yields(aggregate_daily(hourly_savings), today)
        period_feed_in = aggregate_period_yields(aggregate_daily(hourly_feed_in), today)

        amort_date = calculate_amortization_date(
            daily_yields,
            installation_cost,
            total_yield,
            historical_offset_combined,
            commissioning_date,
            min_history_days,
            rolling_window_days,
            today,
        )

        avg_daily = calculate_average_daily_yield(daily_yields, rolling_window_days)

        days_to_amort: int | None = None
        if amort_date is not None:
            days_to_amort = max(0, (amort_date - today).days)

        stats_first = sc_hourly[0][0].date() if sc_hourly else None
        stats_last = sc_hourly[-1][0].date() if sc_hourly else None
        _LOGGER.debug(
            "PV Economics update: statistics %s..%s (%d hours), "
            "savings stats=%.2f + hist=%.2f = %.2f, "
            "feed_in stats=%.2f + hist=%.2f = %.2f, "
            "yield today=%.2f week=%.2f month=%.2f year=%.2f",
            stats_first,
            stats_last,
            len(sc_hourly),
            savings_eur,
            historical_savings_eur,
            savings_all,
            feed_in_eur,
            historical_feed_in_eur,
            feed_in_all,
            period_yields["today"],
            period_yields["this_week"],
            period_yields["this_month"],
            period_yields["this_year"],
        )

        return {
            VALUE_SELF_CONSUMPTION: round(sc_total, 3),
            VALUE_SELF_CONSUMPTION_RATE: (
                round(sc_rate * 100.0, 1) if sc_rate is not None else None
            ),
            VALUE_SELF_SUFFICIENCY: (
                round(sc_sufficiency * 100.0, 1) if sc_sufficiency is not None else None
            ),
            VALUE_TOTAL_SAVINGS: round(savings_all, 2),
            VALUE_FEED_IN_REVENUE: round(feed_in_all, 2),
            VALUE_TOTAL_YIELD: round(total_yield, 2),
            VALUE_NET_YIELD: round(total_yield - installation_cost, 2),
            VALUE_SYSTEM_AGE_DAYS: system_age_days,
            VALUE_AMORTIZATION_PROGRESS_PCT: (
                round(progress_pct * 100.0, 1) if progress_pct is not None else None
            ),
            VALUE_AMORTIZATION_DATE: amort_date,
            VALUE_DAYS_TO_AMORTIZATION: days_to_amort,
            VALUE_AVERAGE_DAILY_YIELD: (
                round(avg_daily, 2) if avg_daily is not None else None
            ),
            VALUE_IS_AMORTIZED: total_yield >= installation_cost,
            VALUE_YIELD_TODAY: round(period_yields["today"], 2),
            VALUE_YIELD_THIS_WEEK: round(period_yields["this_week"], 2),
            VALUE_YIELD_THIS_MONTH: round(period_yields["this_month"], 2),
            VALUE_YIELD_THIS_YEAR: round(period_yields["this_year"], 2),
            VALUE_SAVINGS_TODAY: round(period_savings["today"], 2),
            VALUE_SAVINGS_THIS_WEEK: round(period_savings["this_week"], 2),
            VALUE_SAVINGS_THIS_MONTH: round(period_savings["this_month"], 2),
            VALUE_SAVINGS_THIS_YEAR: round(period_savings["this_year"], 2),
            VALUE_FEED_IN_TODAY: round(period_feed_in["today"], 2),
            VALUE_FEED_IN_THIS_WEEK: round(period_feed_in["this_week"], 2),
            VALUE_FEED_IN_THIS_MONTH: round(period_feed_in["this_month"], 2),
            VALUE_FEED_IN_THIS_YEAR: round(period_feed_in["this_year"], 2),
            _PRICE_FALLBACK_KEY: price_fallback,
            _TARIFF_FALLBACK_KEY: tariff_fallback,
            _SAVINGS_FROM_STATS_KEY: round(savings_eur, 2),
            _FEED_IN_FROM_STATS_KEY: round(feed_in_eur, 2),
            _HIST_SAVINGS_KEY: round(historical_savings_eur, 2),
            _HIST_FEED_IN_KEY: round(historical_feed_in_eur, 2),
            _STATS_FIRST_DATE_KEY: stats_first,
            _STATS_LAST_DATE_KEY: stats_last,
            _STATS_HOURS_KEY: len(sc_hourly),
        }

    def _compute_savings(
        self,
        sc_hourly: list[tuple[datetime, float]],
        cfg: dict[str, Any],
        stats: dict[str, list[dict[str, Any]]],
        price_mode: str,
        price_entity: str | None,
        price_fallback: bool,
    ) -> list[tuple[datetime, float]]:
        """Return per-hour electricity savings."""
        if price_mode != TARIFF_MODE_ENTITY:
            return compute_hourly_savings(
                sc_hourly,
                fixed_price_ct=float(cfg[CONF_ELECTRICITY_PRICE_VALUE]),
            )

        if price_fallback or not price_entity:
            # Fallback: apply the current sensor state uniformly to every hour
            # so daily aggregation stays meaningful (the total equals
            # sc_total_kwh * current_price either way).
            state = self.hass.states.get(price_entity or "")
            if (
                price_entity
                and state
                and state.state not in ("unknown", "unavailable")
            ):
                try:
                    current_price_eur = float(state.state) / 100.0
                    return [(ts, kwh * current_price_eur) for ts, kwh in sc_hourly]
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
    ) -> list[tuple[datetime, float]]:
        """Return per-hour feed-in revenue."""
        if tariff_mode != TARIFF_MODE_ENTITY:
            return compute_hourly_feed_in(
                exp_deltas,
                fixed_tariff_ct=float(cfg[CONF_FEED_IN_TARIFF_VALUE]),
            )

        if tariff_fallback or not tariff_entity:
            # Fallback: apply the current sensor state uniformly to every hour
            # so daily aggregation stays meaningful.
            state = self.hass.states.get(tariff_entity or "")
            if (
                tariff_entity
                and state
                and state.state not in ("unknown", "unavailable")
            ):
                try:
                    current_tariff_eur = float(state.state) / 100.0
                    return [(ts, kwh * current_tariff_eur) for ts, kwh in exp_deltas]
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
