"""Wrappers around Home Assistant recorder statistics.

This module will contain async helpers for reading hourly long-term statistics
from recorder.statistics while keeping recorder-specific details out of the
coordinator and pure calculations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant


async def async_get_hourly_statistics(
    hass: HomeAssistant,
    statistic_ids: list[str],
    start: datetime,
    end: datetime,
) -> dict[str, list[dict[str, Any]]]:
    """Fetch hourly long-term statistics for the requested statistic IDs."""
    raise NotImplementedError


async def async_has_statistics(
    hass: HomeAssistant,
    statistic_id: str,
) -> bool:
    """Return whether a statistic ID has long-term statistics."""
    raise NotImplementedError
