"""Wrappers around Home Assistant recorder statistics."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    list_statistic_ids,
    statistics_during_period,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant


async def async_get_statistics(
    hass: HomeAssistant,
    statistic_ids: list[str],
    start: datetime,
    end: datetime,
    period: str = "hour",
) -> dict[str, list[dict[str, Any]]]:
    """Fetch statistics for the requested statistic IDs.

    Returns a dict mapping statistic ID to a list of buckets.
    Each bucket is a plain dict with keys: start (datetime), sum (float|None),
    mean (float|None).
    """
    instance = get_instance(hass)
    raw: dict[str, list[dict[str, Any]]] = await instance.async_add_executor_job(
        statistics_during_period,
        hass,
        start,
        end,
        set(statistic_ids),
        period,
        {"energy": UnitOfEnergy.KILO_WATT_HOUR},
        {"sum", "mean"},
    )
    return {
        stat_id: [
            {
                "start": datetime.fromtimestamp(row["start"], tz=UTC),
                "sum": row.get("sum"),
                "mean": row.get("mean"),
            }
            for row in rows
        ]
        for stat_id, rows in raw.items()
    }


async def async_get_hourly_statistics(
    hass: HomeAssistant,
    statistic_ids: list[str],
    start: datetime,
    end: datetime,
) -> dict[str, list[dict[str, Any]]]:
    """Fetch hourly statistics. Alias for async_get_statistics with period='hour'."""
    return await async_get_statistics(hass, statistic_ids, start, end, period="hour")


async def async_has_statistics(
    hass: HomeAssistant,
    statistic_id: str,
) -> bool:
    """Return whether a statistic ID has long-term statistics."""
    instance = get_instance(hass)
    ids: list[dict[str, Any]] = await instance.async_add_executor_job(
        list_statistic_ids,
        hass,
        {statistic_id},
        None,
    )
    return len(ids) > 0
