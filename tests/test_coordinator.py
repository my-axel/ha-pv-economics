"""Coordinator integration tests."""
from __future__ import annotations

import re
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.pv_economics.const import (
    CONF_COMMISSIONING_DATE,
    CONF_ELECTRICITY_PRICE_ENTITY,
    CONF_ELECTRICITY_PRICE_MODE,
    CONF_ELECTRICITY_PRICE_VALUE,
    CONF_FEED_IN_TARIFF_MODE,
    CONF_FEED_IN_TARIFF_VALUE,
    CONF_GRID_EXPORT_ENTITY,
    CONF_HAS_BATTERY,
    CONF_INSTALLATION_COST,
    CONF_PV_PRODUCTION_ENTITY,
    CONF_STATISTICS_START_DATE,
    TARIFF_MODE_ENTITY,
    VALUE_FEED_IN_REVENUE,
    VALUE_SELF_CONSUMPTION,
    VALUE_TOTAL_SAVINGS,
)
from custom_components.pv_economics.coordinator import (
    _PRICE_FALLBACK_KEY,
    _STATS_HOURS_KEY,
    _TARIFF_FALLBACK_KEY,
    PVEconomicsCoordinator,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2024, 1, 2, 4, 0, 0, tzinfo=UTC)


def _ts(hour: int) -> datetime:
    """UTC datetime on the test date at the given hour."""
    return datetime(2024, 1, 2, hour, 0, 0, tzinfo=UTC)


def _bucket(
    start: datetime, total: float | None, mean: float | None = None
) -> dict:
    return {"start": start, "sum": total, "mean": mean}


def _make_entry(data: dict, options: dict | None = None) -> MagicMock:
    entry = MagicMock()
    entry.data = data
    entry.options = options or {}
    return entry


def _make_hass(entity_states: dict | None = None) -> MagicMock:
    hass = MagicMock()
    states = entity_states or {}
    hass.states.get.side_effect = lambda eid: states.get(eid)
    hass.config.currency = "EUR"
    return hass


def _make_coordinator(
    hass: MagicMock, data: dict, options: dict | None = None
) -> PVEconomicsCoordinator:
    entry = _make_entry(data, options)
    return PVEconomicsCoordinator(hass, entry)


# ---------------------------------------------------------------------------
# Shared config & static stats
# ---------------------------------------------------------------------------

_BASE_CFG: dict = {
    CONF_COMMISSIONING_DATE: "2024-01-01",
    CONF_STATISTICS_START_DATE: "2024-01-02",
    CONF_INSTALLATION_COST: 10000.0,
    CONF_PV_PRODUCTION_ENTITY: "sensor.pv",
    CONF_GRID_EXPORT_ENTITY: "sensor.export",
    CONF_ELECTRICITY_PRICE_MODE: "fixed",
    CONF_ELECTRICITY_PRICE_VALUE: 30.0,  # ct/kWh
    CONF_FEED_IN_TARIFF_MODE: "fixed",
    CONF_FEED_IN_TARIFF_VALUE: 8.0,  # ct/kWh
    CONF_HAS_BATTERY: False,
}

# 4 cumulative buckets -> 3 hourly deltas of 1.0 kWh each (h1, h2, h3)
_PROD_STATS = [
    _bucket(_ts(0), 0.0),
    _bucket(_ts(1), 1.0),
    _bucket(_ts(2), 2.0),
    _bucket(_ts(3), 3.0),
]
# 4 cumulative buckets -> 3 deltas of 0.5 kWh each
_EXP_STATS = [
    _bucket(_ts(0), 0.0),
    _bucket(_ts(1), 0.5),
    _bucket(_ts(2), 1.0),
    _bucket(_ts(3), 1.5),
]

# SC = prod - export = 0.5 kWh/h x 3 = 1.5 kWh total

_EXISTING_ENTITY = MagicMock(state="0")

_BOTH_ENTITIES = {
    "sensor.pv": _EXISTING_ENTITY,
    "sensor.export": _EXISTING_ENTITY,
}


def _stats_side_effect(hass, statistic_ids, start, end, period="hour"):
    if period == "hour":
        return {"sensor.pv": _PROD_STATS, "sensor.export": _EXP_STATS}
    return {}  # 5-min live call: no live data


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_coordinator_happy_path_fixed_price() -> None:
    """Full run with fixed price/tariff, no battery, 3 h of hourly stats."""
    hass = _make_hass(_BOTH_ENTITIES)
    coordinator = _make_coordinator(hass, _BASE_CFG)

    with (
        patch(
            "custom_components.pv_economics.coordinator.async_get_statistics",
            new_callable=AsyncMock,
            side_effect=_stats_side_effect,
        ),
        patch(
            "custom_components.pv_economics.coordinator.async_has_statistics",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "custom_components.pv_economics.coordinator"
            ".async_handle_fallback_repairs"
        ),
        patch("homeassistant.util.dt.utcnow", return_value=_NOW),
        patch("homeassistant.util.dt.now", return_value=_NOW),
        patch("homeassistant.util.dt.DEFAULT_TIME_ZONE", UTC),
        patch("homeassistant.util.dt.start_of_local_day", return_value=_ts(0)),
    ):
        result = await coordinator._async_update_data()

    # SC = 1.5 kWh (prod 3.0 - export 1.5)
    assert result[VALUE_SELF_CONSUMPTION] == pytest.approx(1.5)
    # Savings: 1.5 kWh x 30 ct = 0.45 EUR
    assert result[VALUE_TOTAL_SAVINGS] == pytest.approx(0.45, abs=0.01)
    # Feed-in: 1.5 kWh x 8 ct = 0.12 EUR
    assert result[VALUE_FEED_IN_REVENUE] == pytest.approx(0.12, abs=0.01)
    assert result[_PRICE_FALLBACK_KEY] is False
    assert result[_TARIFF_FALLBACK_KEY] is False
    assert result[_STATS_HOURS_KEY] == 3


async def test_coordinator_price_fallback_path(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Entity-based price without statistics triggers fallback + repair."""
    cfg = {
        **_BASE_CFG,
        CONF_ELECTRICITY_PRICE_MODE: TARIFF_MODE_ENTITY,
        CONF_ELECTRICITY_PRICE_ENTITY: "sensor.price",
    }
    price_state = MagicMock(
        state="28.5",
        attributes={"unit_of_measurement": "ct/kWh"},
    )
    hass = _make_hass(
        {
            "sensor.pv": _EXISTING_ENTITY,
            "sensor.export": _EXISTING_ENTITY,
            "sensor.price": price_state,
        }
    )
    coordinator = _make_coordinator(hass, cfg)

    with (
        patch(
            "custom_components.pv_economics.coordinator.async_get_statistics",
            new_callable=AsyncMock,
            side_effect=_stats_side_effect,
        ),
        patch(
            "custom_components.pv_economics.coordinator.async_has_statistics",
            new_callable=AsyncMock,
            return_value=False,  # no stats for price entity -> fallback
        ),
        patch(
            "custom_components.pv_economics.coordinator"
            ".async_handle_fallback_repairs",
        ) as mock_repairs,
        patch("homeassistant.util.dt.utcnow", return_value=_NOW),
        patch("homeassistant.util.dt.now", return_value=_NOW),
        patch("homeassistant.util.dt.DEFAULT_TIME_ZONE", UTC),
        patch("homeassistant.util.dt.start_of_local_day", return_value=_ts(0)),
    ):
        result = await coordinator._async_update_data()

    assert result[_PRICE_FALLBACK_KEY] is True
    assert result[_TARIFF_FALLBACK_KEY] is False
    # Fallback uses current state: 1.5 kWh x 28.5 ct = 0.4275 EUR
    assert result[VALUE_TOTAL_SAVINGS] == pytest.approx(0.4275, abs=0.005)
    # Repair handler must be called with price_fallback=True
    mock_repairs.assert_called_once()
    _, kwargs = mock_repairs.call_args
    assert kwargs.get("price_fallback") is True
    # Warning about missing statistics must be logged
    assert "sensor.price" in caplog.text


async def test_coordinator_update_failed_missing_entity() -> None:
    """Missing mandatory entity raises UpdateFailed."""
    # sensor.pv absent from states -> existence check fires
    hass = _make_hass({"sensor.export": _EXISTING_ENTITY})
    coordinator = _make_coordinator(hass, _BASE_CFG)

    with pytest.raises(UpdateFailed, match=re.escape("sensor.pv")):
        await coordinator._async_update_data()


async def test_coordinator_update_failed_on_stats_exception() -> None:
    """Unexpected exception from statistics layer is wrapped in UpdateFailed."""
    hass = _make_hass(_BOTH_ENTITIES)
    coordinator = _make_coordinator(hass, _BASE_CFG)

    with (
        patch(
            "custom_components.pv_economics.coordinator.async_get_statistics",
            new_callable=AsyncMock,
            side_effect=RuntimeError("recorder unavailable"),
        ),
        patch(
            "custom_components.pv_economics.coordinator.async_has_statistics",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch("homeassistant.util.dt.utcnow", return_value=_NOW),
        patch("homeassistant.util.dt.DEFAULT_TIME_ZONE", UTC),
        pytest.raises(UpdateFailed, match="recorder unavailable"),
    ):
        await coordinator._async_update_data()
