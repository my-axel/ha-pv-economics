"""Tests for PV Economics config flow."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.pv_economics.config_flow import (
    PVEconomicsConfigFlow,
    PVEconomicsOptionsFlow,
    _validate_battery_sensors,
    _validate_costs,
    _validate_entities,
    _validate_tariff_entity,
)
from custom_components.pv_economics.const import (
    BATTERY_POSITIVE_CHARGE,
    BATTERY_TYPE_BIDIRECTIONAL,
    BATTERY_TYPE_TWO_SENSORS,
    CONF_BATTERY_CHARGE_ENTITY,
    CONF_BATTERY_DISCHARGE_ENTITY,
    CONF_BATTERY_POWER_ENTITY,
    CONF_BATTERY_POWER_POSITIVE,
    CONF_BATTERY_SENSOR_TYPE,
    CONF_COMMISSIONING_DATE,
    CONF_ELECTRICITY_PRICE_ENTITY,
    CONF_ELECTRICITY_PRICE_MODE,
    CONF_ELECTRICITY_PRICE_VALUE,
    CONF_FEED_IN_TARIFF_ENTITY,
    CONF_FEED_IN_TARIFF_MODE,
    CONF_FEED_IN_TARIFF_VALUE,
    CONF_GRID_EXPORT_ENTITY,
    CONF_GRID_IMPORT_ENTITY,
    CONF_HAS_BATTERY,
    CONF_HISTORICAL_FEED_IN,
    CONF_HISTORICAL_SAVINGS,
    CONF_INSTALLATION_COST,
    CONF_PV_PRODUCTION_ENTITY,
    CONF_ROLLING_WINDOW_DAYS,
    CONF_STATISTICS_START_DATE,
    TARIFF_MODE_ENTITY,
    TARIFF_MODE_FIXED,
)

# ---------------------------------------------------------------------------
# Shared input helpers
# ---------------------------------------------------------------------------

_COSTS = {
    CONF_INSTALLATION_COST: 10000.0,
    CONF_COMMISSIONING_DATE: "2023-01-01",
    CONF_STATISTICS_START_DATE: "2023-06-01",
}
_HISTORY = {
    CONF_HISTORICAL_SAVINGS: 0.0,
    CONF_HISTORICAL_FEED_IN: 0.0,
}
_ENTITIES_FIXED = {
    CONF_PV_PRODUCTION_ENTITY: "sensor.pv_production",
    CONF_GRID_EXPORT_ENTITY: "sensor.grid_export",
    CONF_FEED_IN_TARIFF_MODE: TARIFF_MODE_FIXED,
    CONF_ELECTRICITY_PRICE_MODE: TARIFF_MODE_FIXED,
    CONF_ROLLING_WINDOW_DAYS: 365,
    CONF_HAS_BATTERY: False,
}
_FEED_IN_FIXED = {CONF_FEED_IN_TARIFF_VALUE: 8.0}
_ELECTRICITY_FIXED = {CONF_ELECTRICITY_PRICE_VALUE: 30.0}


# ---------------------------------------------------------------------------
# Happy-path: fixed tariffs, no battery, no grid import
# ---------------------------------------------------------------------------


async def test_happy_path_fixed_no_battery(config_flow: PVEconomicsConfigFlow) -> None:
    result = await config_flow.async_step_user(_COSTS)
    assert result["type"] == "form"
    assert result["step_id"] == "history"

    result = await config_flow.async_step_history(_HISTORY)
    assert result["step_id"] == "entities"

    result = await config_flow.async_step_entities(_ENTITIES_FIXED)
    assert result["step_id"] == "feed_in_tariff"

    result = await config_flow.async_step_feed_in_tariff(_FEED_IN_FIXED)
    assert result["step_id"] == "electricity_price"

    result = await config_flow.async_step_electricity_price(_ELECTRICITY_FIXED)
    assert result["type"] == "create_entry"
    assert result["data"][CONF_INSTALLATION_COST] == 10000.0
    assert result["data"][CONF_FEED_IN_TARIFF_VALUE] == 8.0
    assert result["data"][CONF_ELECTRICITY_PRICE_VALUE] == 30.0
    assert CONF_BATTERY_SENSOR_TYPE not in result["data"]


async def test_happy_path_with_grid_import(config_flow: PVEconomicsConfigFlow) -> None:
    entities = {**_ENTITIES_FIXED, CONF_GRID_IMPORT_ENTITY: "sensor.grid_import"}
    await config_flow.async_step_user(_COSTS)
    await config_flow.async_step_history(_HISTORY)
    result = await config_flow.async_step_entities(entities)
    assert result["step_id"] == "feed_in_tariff"
    await config_flow.async_step_feed_in_tariff(_FEED_IN_FIXED)
    result = await config_flow.async_step_electricity_price(_ELECTRICITY_FIXED)
    assert result["type"] == "create_entry"
    assert result["data"][CONF_GRID_IMPORT_ENTITY] == "sensor.grid_import"


# ---------------------------------------------------------------------------
# Entity mode: feed-in tariff and electricity price
# ---------------------------------------------------------------------------


async def test_entity_mode_feed_in(
    config_flow_with_hass: PVEconomicsConfigFlow,
) -> None:
    flow = config_flow_with_hass
    flow.hass.states.get.return_value = MagicMock(state="8.5")

    entities = {
        **_ENTITIES_FIXED,
        CONF_FEED_IN_TARIFF_MODE: TARIFF_MODE_ENTITY,
        CONF_ELECTRICITY_PRICE_MODE: TARIFF_MODE_FIXED,
    }
    await flow.async_step_user(_COSTS)
    await flow.async_step_history(_HISTORY)
    await flow.async_step_entities(entities)

    result = await flow.async_step_feed_in_tariff(
        {CONF_FEED_IN_TARIFF_ENTITY: "sensor.feed_in_tariff"}
    )
    assert result["step_id"] == "electricity_price"

    result = await flow.async_step_electricity_price(_ELECTRICITY_FIXED)
    assert result["type"] == "create_entry"
    assert result["data"][CONF_FEED_IN_TARIFF_ENTITY] == "sensor.feed_in_tariff"


async def test_entity_mode_electricity_price(
    config_flow_with_hass: PVEconomicsConfigFlow,
) -> None:
    flow = config_flow_with_hass
    flow.hass.states.get.return_value = MagicMock(state="29.5")

    entities = {
        **_ENTITIES_FIXED,
        CONF_FEED_IN_TARIFF_MODE: TARIFF_MODE_FIXED,
        CONF_ELECTRICITY_PRICE_MODE: TARIFF_MODE_ENTITY,
    }
    await flow.async_step_user(_COSTS)
    await flow.async_step_history(_HISTORY)
    await flow.async_step_entities(entities)
    await flow.async_step_feed_in_tariff(_FEED_IN_FIXED)

    result = await flow.async_step_electricity_price(
        {CONF_ELECTRICITY_PRICE_ENTITY: "sensor.electricity_price"}
    )
    assert result["type"] == "create_entry"
    assert result["data"][CONF_ELECTRICITY_PRICE_ENTITY] == "sensor.electricity_price"


# ---------------------------------------------------------------------------
# Battery path: bidirectional
# ---------------------------------------------------------------------------


async def test_battery_bidirectional(config_flow: PVEconomicsConfigFlow) -> None:
    entities = {
        **_ENTITIES_FIXED,
        CONF_HAS_BATTERY: True,
    }
    await config_flow.async_step_user(_COSTS)
    await config_flow.async_step_history(_HISTORY)

    result = await config_flow.async_step_entities(entities)
    assert result["step_id"] == "battery_type"

    result = await config_flow.async_step_battery_type(
        {CONF_BATTERY_SENSOR_TYPE: BATTERY_TYPE_BIDIRECTIONAL}
    )
    assert result["step_id"] == "battery_sensors"

    result = await config_flow.async_step_battery_sensors(
        {
            CONF_BATTERY_POWER_ENTITY: "sensor.battery_power",
            CONF_BATTERY_POWER_POSITIVE: BATTERY_POSITIVE_CHARGE,
        }
    )
    assert result["step_id"] == "feed_in_tariff"

    await config_flow.async_step_feed_in_tariff(_FEED_IN_FIXED)
    result = await config_flow.async_step_electricity_price(_ELECTRICITY_FIXED)
    assert result["type"] == "create_entry"
    assert result["data"][CONF_BATTERY_POWER_ENTITY] == "sensor.battery_power"
    assert CONF_BATTERY_CHARGE_ENTITY not in result["data"]
    assert CONF_BATTERY_DISCHARGE_ENTITY not in result["data"]


# ---------------------------------------------------------------------------
# Battery path: two-sensor + stale key cleanup
# ---------------------------------------------------------------------------


async def test_battery_two_sensors(config_flow: PVEconomicsConfigFlow) -> None:
    entities = {**_ENTITIES_FIXED, CONF_HAS_BATTERY: True}
    await config_flow.async_step_user(_COSTS)
    await config_flow.async_step_history(_HISTORY)
    await config_flow.async_step_entities(entities)
    await config_flow.async_step_battery_type(
        {CONF_BATTERY_SENSOR_TYPE: BATTERY_TYPE_TWO_SENSORS}
    )

    result = await config_flow.async_step_battery_sensors(
        {
            CONF_BATTERY_CHARGE_ENTITY: "sensor.battery_charge",
            CONF_BATTERY_DISCHARGE_ENTITY: "sensor.battery_discharge",
        }
    )
    assert result["step_id"] == "feed_in_tariff"
    await config_flow.async_step_feed_in_tariff(_FEED_IN_FIXED)
    result = await config_flow.async_step_electricity_price(_ELECTRICITY_FIXED)
    assert result["type"] == "create_entry"
    assert result["data"][CONF_BATTERY_CHARGE_ENTITY] == "sensor.battery_charge"
    assert CONF_BATTERY_POWER_ENTITY not in result["data"]
    assert CONF_BATTERY_POWER_POSITIVE not in result["data"]


async def test_battery_switch_type_cleans_stale_keys(
    config_flow: PVEconomicsConfigFlow,
) -> None:
    entities = {**_ENTITIES_FIXED, CONF_HAS_BATTERY: True}
    await config_flow.async_step_user(_COSTS)
    await config_flow.async_step_history(_HISTORY)
    await config_flow.async_step_entities(entities)
    # First select two-sensor, then switch to bidirectional
    await config_flow.async_step_battery_type(
        {CONF_BATTERY_SENSOR_TYPE: BATTERY_TYPE_TWO_SENSORS}
    )
    # Inject stale two-sensor keys into _data to simulate prior entry
    config_flow._data[CONF_BATTERY_CHARGE_ENTITY] = "sensor.old_charge"
    config_flow._data[CONF_BATTERY_DISCHARGE_ENTITY] = "sensor.old_discharge"
    config_flow._data[CONF_BATTERY_SENSOR_TYPE] = BATTERY_TYPE_BIDIRECTIONAL

    result = await config_flow.async_step_battery_sensors(
        {
            CONF_BATTERY_POWER_ENTITY: "sensor.battery_power",
            CONF_BATTERY_POWER_POSITIVE: BATTERY_POSITIVE_CHARGE,
        }
    )
    assert result["step_id"] == "feed_in_tariff"
    await config_flow.async_step_feed_in_tariff(_FEED_IN_FIXED)
    result = await config_flow.async_step_electricity_price(_ELECTRICITY_FIXED)
    assert CONF_BATTERY_CHARGE_ENTITY not in result["data"]
    assert CONF_BATTERY_DISCHARGE_ENTITY not in result["data"]
    assert result["data"][CONF_BATTERY_POWER_ENTITY] == "sensor.battery_power"


# ---------------------------------------------------------------------------
# OptionsFlow round-trip
# ---------------------------------------------------------------------------


def _make_entry(data: dict) -> MagicMock:
    entry = MagicMock()
    entry.data = data
    entry.options = {}
    return entry


async def test_options_flow_round_trip() -> None:
    saved = {
        **_COSTS,
        **_HISTORY,
        **_ENTITIES_FIXED,
        **_FEED_IN_FIXED,
        **_ELECTRICITY_FIXED,
    }
    flow = PVEconomicsOptionsFlow(_make_entry(saved))

    result = await flow.async_step_init(
        {**_COSTS, CONF_INSTALLATION_COST: 12000.0}
    )
    assert result["step_id"] == "history"

    result = await flow.async_step_history(_HISTORY)
    assert result["step_id"] == "entities"

    result = await flow.async_step_entities(_ENTITIES_FIXED)
    assert result["step_id"] == "feed_in_tariff"

    result = await flow.async_step_feed_in_tariff(_FEED_IN_FIXED)
    assert result["step_id"] == "electricity_price"

    result = await flow.async_step_electricity_price(_ELECTRICITY_FIXED)
    assert result["type"] == "create_entry"
    assert result["data"][CONF_INSTALLATION_COST] == 12000.0


async def test_options_flow_disable_battery_removes_keys() -> None:
    saved = {
        **_COSTS,
        **_HISTORY,
        **{**_ENTITIES_FIXED, CONF_HAS_BATTERY: True},
        CONF_BATTERY_SENSOR_TYPE: BATTERY_TYPE_TWO_SENSORS,
        CONF_BATTERY_CHARGE_ENTITY: "sensor.batt_charge",
        CONF_BATTERY_DISCHARGE_ENTITY: "sensor.batt_discharge",
        **_FEED_IN_FIXED,
        **_ELECTRICITY_FIXED,
    }
    flow = PVEconomicsOptionsFlow(_make_entry(saved))

    await flow.async_step_init(_COSTS)
    await flow.async_step_history(_HISTORY)
    # Disable battery
    result = await flow.async_step_entities(
        {**_ENTITIES_FIXED, CONF_HAS_BATTERY: False}
    )
    assert result["step_id"] == "feed_in_tariff"
    await flow.async_step_feed_in_tariff(_FEED_IN_FIXED)
    result = await flow.async_step_electricity_price(_ELECTRICITY_FIXED)
    assert result["type"] == "create_entry"
    assert CONF_BATTERY_SENSOR_TYPE not in result["data"]
    assert CONF_BATTERY_CHARGE_ENTITY not in result["data"]


# ---------------------------------------------------------------------------
# Migration: v1→v3, v2→v3
# ---------------------------------------------------------------------------


async def test_migrate_v1_to_v3() -> None:
    from custom_components.pv_economics import async_migrate_entry

    hass = MagicMock()
    entry = MagicMock()
    entry.version = 1
    entry.entry_id = "test_entry"
    entry.data = {
        "installation_cost": 8000.0,
        "commissioning_date": "2022-01-01",
        "historical_offset": 150.0,
        "pv_production_entity": "sensor.pv",
        "grid_export_entity": "sensor.export",
        "feed_in_tariff_mode": "fixed",
        "feed_in_tariff_value": 8.0,
        "electricity_price_mode": "fixed",
        "electricity_price_value": 30.0,
        "rolling_window_days": 365,
        "has_battery": False,
    }

    result = await async_migrate_entry(hass, entry)
    assert result is True
    hass.config_entries.async_update_entry.assert_called()


async def test_migrate_v2_to_v3() -> None:
    from custom_components.pv_economics import async_migrate_entry

    hass = MagicMock()
    entry = MagicMock()
    entry.version = 2
    entry.entry_id = "test_entry"
    entry.data = {
        "installation_cost": 8000.0,
        "commissioning_date": "2022-01-01",
        "statistics_start_date": "2022-01-01",
        "historical_savings_eur": 200.0,
        "historical_feed_in_eur": 50.0,
        "pv_production_entity": "sensor.pv",
        "grid_export_entity": "sensor.export",
        "feed_in_tariff_mode": "fixed",
        "feed_in_tariff_value": 8.0,
        "electricity_price_mode": "fixed",
        "electricity_price_value": 30.0,
        "rolling_window_days": 365,
        "has_battery": False,
    }

    result = await async_migrate_entry(hass, entry)
    assert result is True
    hass.config_entries.async_update_entry.assert_called()


# ---------------------------------------------------------------------------
# Validation: installation_cost = 0
# ---------------------------------------------------------------------------


def test_validate_costs_zero_installation_cost() -> None:
    errors = _validate_costs(
        {
            CONF_INSTALLATION_COST: 0.0,
            CONF_COMMISSIONING_DATE: "2023-01-01",
            CONF_STATISTICS_START_DATE: "2023-06-01",
        }
    )
    assert errors == {CONF_INSTALLATION_COST: "installation_cost_zero"}


def test_validate_costs_positive_installation_cost() -> None:
    errors = _validate_costs(
        {
            CONF_INSTALLATION_COST: 0.01,
            CONF_COMMISSIONING_DATE: "2023-01-01",
            CONF_STATISTICS_START_DATE: "2023-06-01",
        }
    )
    assert CONF_INSTALLATION_COST not in errors


async def test_config_flow_rejects_zero_cost(
    config_flow: PVEconomicsConfigFlow,
) -> None:
    result = await config_flow.async_step_user(
        {**_COSTS, CONF_INSTALLATION_COST: 0.0}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"][CONF_INSTALLATION_COST] == "installation_cost_zero"


# ---------------------------------------------------------------------------
# Validation: statistics_before_commissioning
# ---------------------------------------------------------------------------


def test_validate_costs_statistics_before_commissioning() -> None:
    errors = _validate_costs(
        {
            CONF_INSTALLATION_COST: 5000.0,
            CONF_COMMISSIONING_DATE: "2023-06-01",
            CONF_STATISTICS_START_DATE: "2023-01-01",
        }
    )
    assert errors == {CONF_STATISTICS_START_DATE: "statistics_before_commissioning"}


def test_validate_costs_statistics_same_as_commissioning() -> None:
    errors = _validate_costs(
        {
            CONF_INSTALLATION_COST: 5000.0,
            CONF_COMMISSIONING_DATE: "2023-01-01",
            CONF_STATISTICS_START_DATE: "2023-01-01",
        }
    )
    assert CONF_STATISTICS_START_DATE not in errors


async def test_config_flow_rejects_statistics_before_commissioning(
    config_flow: PVEconomicsConfigFlow,
) -> None:
    bad_costs = {
        CONF_INSTALLATION_COST: 5000.0,
        CONF_COMMISSIONING_DATE: "2023-06-01",
        CONF_STATISTICS_START_DATE: "2023-01-01",
    }
    result = await config_flow.async_step_user(bad_costs)
    err_key = "statistics_before_commissioning"
    assert result["errors"][CONF_STATISTICS_START_DATE] == err_key


# ---------------------------------------------------------------------------
# Validation: duplicate entities
# ---------------------------------------------------------------------------


def test_validate_entities_same_production_and_export() -> None:
    errors = _validate_entities(
        {
            CONF_PV_PRODUCTION_ENTITY: "sensor.pv",
            CONF_GRID_EXPORT_ENTITY: "sensor.pv",
        }
    )
    assert errors == {CONF_GRID_EXPORT_ENTITY: "duplicate_entity"}


def test_validate_entities_distinct() -> None:
    errors = _validate_entities(
        {
            CONF_PV_PRODUCTION_ENTITY: "sensor.pv",
            CONF_GRID_EXPORT_ENTITY: "sensor.export",
        }
    )
    assert not errors


def test_validate_battery_sensors_bidirectional_duplicate() -> None:
    saved = {
        CONF_PV_PRODUCTION_ENTITY: "sensor.pv",
        CONF_GRID_EXPORT_ENTITY: "sensor.export",
        CONF_BATTERY_SENSOR_TYPE: BATTERY_TYPE_BIDIRECTIONAL,
    }
    errors = _validate_battery_sensors(
        {
            CONF_BATTERY_POWER_ENTITY: "sensor.pv",
            CONF_BATTERY_POWER_POSITIVE: BATTERY_POSITIVE_CHARGE,
        },
        saved,
    )
    assert errors == {CONF_BATTERY_POWER_ENTITY: "duplicate_entity"}


def test_validate_battery_sensors_two_sensors_same_entity() -> None:
    saved = {
        CONF_PV_PRODUCTION_ENTITY: "sensor.pv",
        CONF_GRID_EXPORT_ENTITY: "sensor.export",
        CONF_BATTERY_SENSOR_TYPE: BATTERY_TYPE_TWO_SENSORS,
    }
    errors = _validate_battery_sensors(
        {
            CONF_BATTERY_CHARGE_ENTITY: "sensor.batt",
            CONF_BATTERY_DISCHARGE_ENTITY: "sensor.batt",
        },
        saved,
    )
    assert errors == {CONF_BATTERY_DISCHARGE_ENTITY: "duplicate_entity"}


async def test_config_flow_rejects_duplicate_entities(
    config_flow: PVEconomicsConfigFlow,
) -> None:
    await config_flow.async_step_user(_COSTS)
    await config_flow.async_step_history(_HISTORY)
    result = await config_flow.async_step_entities(
        {
            **_ENTITIES_FIXED,
            CONF_PV_PRODUCTION_ENTITY: "sensor.same",
            CONF_GRID_EXPORT_ENTITY: "sensor.same",
        }
    )
    assert result["errors"][CONF_GRID_EXPORT_ENTITY] == "duplicate_entity"


# ---------------------------------------------------------------------------
# Validation: entity-mode state check
# ---------------------------------------------------------------------------


def test_validate_tariff_entity_unavailable() -> None:
    hass = MagicMock()
    hass.states.get.return_value = MagicMock(state="unavailable")
    assert _validate_tariff_entity("sensor.price", hass) == "entity_not_available"


def test_validate_tariff_entity_unknown() -> None:
    hass = MagicMock()
    hass.states.get.return_value = MagicMock(state="unknown")
    assert _validate_tariff_entity("sensor.price", hass) == "entity_not_available"


def test_validate_tariff_entity_missing() -> None:
    hass = MagicMock()
    hass.states.get.return_value = None
    assert _validate_tariff_entity("sensor.price", hass) == "entity_not_available"


def test_validate_tariff_entity_non_numeric() -> None:
    hass = MagicMock()
    hass.states.get.return_value = MagicMock(state="not_a_number")
    assert _validate_tariff_entity("sensor.price", hass) == "entity_not_numeric"


def test_validate_tariff_entity_valid() -> None:
    hass = MagicMock()
    hass.states.get.return_value = MagicMock(state="29.5")
    assert _validate_tariff_entity("sensor.price", hass) is None


async def test_config_flow_rejects_unavailable_entity_mode(
    config_flow_with_hass: PVEconomicsConfigFlow,
) -> None:
    flow = config_flow_with_hass
    flow.hass.states.get.return_value = MagicMock(state="unavailable")

    entities = {
        **_ENTITIES_FIXED,
        CONF_FEED_IN_TARIFF_MODE: TARIFF_MODE_ENTITY,
        CONF_ELECTRICITY_PRICE_MODE: TARIFF_MODE_FIXED,
    }
    await flow.async_step_user(_COSTS)
    await flow.async_step_history(_HISTORY)
    await flow.async_step_entities(entities)

    result = await flow.async_step_feed_in_tariff(
        {CONF_FEED_IN_TARIFF_ENTITY: "sensor.feed_in_tariff"}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "feed_in_tariff"
    assert result["errors"][CONF_FEED_IN_TARIFF_ENTITY] == "entity_not_available"
