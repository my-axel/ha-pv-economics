"""Config flow for PV Economics."""

from __future__ import annotations

from datetime import date
from typing import Any

import voluptuous as vol
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.helpers.selector import (
    BooleanSelector,
    DateSelector,
    DateSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    BATTERY_POSITIVE_CHARGE,
    BATTERY_POSITIVE_DISCHARGE,
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
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_HISTORICAL_FEED_IN,
    DEFAULT_HISTORICAL_SAVINGS,
    DEFAULT_ROLLING_WINDOW_DAYS,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    TARIFF_MODE_ENTITY,
    TARIFF_MODE_FIXED,
    TARIFF_MODES,
)

_MISSING = object()


def _validate_costs(data: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if float(data.get(CONF_INSTALLATION_COST, 0)) <= 0:
        errors[CONF_INSTALLATION_COST] = "installation_cost_zero"
    start = data.get(CONF_STATISTICS_START_DATE)
    commissioning = data.get(CONF_COMMISSIONING_DATE)
    if start and commissioning and (
        date.fromisoformat(start) < date.fromisoformat(commissioning)
    ):
        errors[CONF_STATISTICS_START_DATE] = "statistics_before_commissioning"
    return errors


def _validate_entities(data: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if data.get(CONF_PV_PRODUCTION_ENTITY) == data.get(CONF_GRID_EXPORT_ENTITY):
        errors[CONF_GRID_EXPORT_ENTITY] = "duplicate_entity"
    return errors


def _validate_battery_sensors(
    data: dict[str, Any], saved: dict[str, Any]
) -> dict[str, str]:
    production = saved.get(CONF_PV_PRODUCTION_ENTITY)
    export = saved.get(CONF_GRID_EXPORT_ENTITY)
    errors: dict[str, str] = {}
    if saved.get(CONF_BATTERY_SENSOR_TYPE) == BATTERY_TYPE_BIDIRECTIONAL:
        if data.get(CONF_BATTERY_POWER_ENTITY) in (production, export):
            errors[CONF_BATTERY_POWER_ENTITY] = "duplicate_entity"
    else:
        for key in (CONF_BATTERY_CHARGE_ENTITY, CONF_BATTERY_DISCHARGE_ENTITY):
            if data.get(key) in (production, export):
                errors[key] = "duplicate_entity"
        if (
            not errors
            and data.get(CONF_BATTERY_CHARGE_ENTITY) is not None
            and data.get(CONF_BATTERY_CHARGE_ENTITY)
            == data.get(CONF_BATTERY_DISCHARGE_ENTITY)
        ):
            errors[CONF_BATTERY_DISCHARGE_ENTITY] = "duplicate_entity"
    return errors


def _validate_tariff_entity(entity_id: str, hass: Any) -> str | None:
    """Return an error key if the entity is not usable as a price source, else None."""
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unknown", "unavailable"):
        return "entity_not_available"
    try:
        float(state.state)
    except ValueError:
        return "entity_not_numeric"
    return None


def _number_selector(
    *,
    min_value: float | None = None,
    unit: str | None = None,
) -> NumberSelector:
    config: dict[str, Any] = {"mode": NumberSelectorMode.BOX}
    if min_value is not None:
        config["min"] = min_value
    if unit is not None:
        config["unit_of_measurement"] = unit
    return NumberSelector(NumberSelectorConfig(config))


def _tariff_mode_selector() -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=TARIFF_MODES,
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def _energy_entity_selector() -> EntitySelector:
    return EntitySelector(
        EntitySelectorConfig(
            domain="sensor",
            device_class=SensorDeviceClass.ENERGY,
        )
    )


def _entity_selector() -> EntitySelector:
    return EntitySelector(EntitySelectorConfig(domain="sensor"))


def _battery_type_selector() -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=[
                SelectOptionDict(
                    value=BATTERY_TYPE_BIDIRECTIONAL,
                    label="Bidirectional power sensor (W/kW)",
                ),
                SelectOptionDict(
                    value=BATTERY_TYPE_TWO_SENSORS,
                    label="Two separate energy sensors (kWh)",
                ),
            ],
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def _battery_positive_selector() -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=[
                SelectOptionDict(
                    value=BATTERY_POSITIVE_CHARGE, label="Positive = charging"
                ),
                SelectOptionDict(
                    value=BATTERY_POSITIVE_DISCHARGE, label="Positive = discharging"
                ),
            ],
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def _required_key(
    key: str,
    defaults: dict[str, Any],
    fallback: Any = _MISSING,
) -> vol.Required:
    default = defaults.get(key, fallback)
    if default is _MISSING or default is None:
        return vol.Required(key)
    return vol.Required(key, default=default)


def _optional_key(
    key: str,
    defaults: dict[str, Any],
    fallback: Any = _MISSING,
) -> vol.Optional:
    default = defaults.get(key, fallback)
    if default is _MISSING or default is None:
        return vol.Optional(key)
    return vol.Optional(key, default=default)


def _costs_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Schema for installation cost, commissioning date, and tracking start date."""
    return vol.Schema(
        {
            _required_key(CONF_INSTALLATION_COST, defaults): _number_selector(
                min_value=0
            ),
            _required_key(CONF_COMMISSIONING_DATE, defaults): DateSelector(
                DateSelectorConfig()
            ),
            _required_key(CONF_STATISTICS_START_DATE, defaults): DateSelector(
                DateSelectorConfig()
            ),
        }
    )


def _history_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Schema for pre-tracking financial totals (optional, default 0)."""
    return vol.Schema(
        {
            _optional_key(
                CONF_HISTORICAL_SAVINGS,
                defaults,
                DEFAULT_HISTORICAL_SAVINGS,
            ): _number_selector(min_value=0),
            _optional_key(
                CONF_HISTORICAL_FEED_IN,
                defaults,
                DEFAULT_HISTORICAL_FEED_IN,
            ): _number_selector(min_value=0),
        }
    )


def _entities_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Schema for energy sensors, pricing modes, and projection settings."""
    return vol.Schema(
        {
            _required_key(
                CONF_PV_PRODUCTION_ENTITY, defaults
            ): _energy_entity_selector(),
            _required_key(
                CONF_GRID_EXPORT_ENTITY, defaults
            ): _energy_entity_selector(),
            _optional_key(
                CONF_GRID_IMPORT_ENTITY, defaults
            ): _energy_entity_selector(),
            _required_key(
                CONF_FEED_IN_TARIFF_MODE,
                defaults,
                TARIFF_MODE_FIXED,
            ): _tariff_mode_selector(),
            _required_key(
                CONF_ELECTRICITY_PRICE_MODE,
                defaults,
                TARIFF_MODE_FIXED,
            ): _tariff_mode_selector(),
            _optional_key(
                CONF_ROLLING_WINDOW_DAYS,
                defaults,
                DEFAULT_ROLLING_WINDOW_DAYS,
            ): _number_selector(min_value=1),
            _optional_key(
                CONF_HAS_BATTERY,
                defaults,
                False,
            ): BooleanSelector(),
        }
    )


def _feed_in_schema(defaults: dict[str, Any], mode: str) -> vol.Schema:
    """Schema for feed-in tariff details."""
    if mode == TARIFF_MODE_ENTITY:
        return vol.Schema(
            {
                _required_key(CONF_FEED_IN_TARIFF_ENTITY, defaults): _entity_selector()
            }
        )
    return vol.Schema(
        {
            _required_key(
                CONF_FEED_IN_TARIFF_VALUE,
                defaults,
            ): _number_selector(min_value=0, unit="ct/kWh")
        }
    )


def _electricity_price_schema(defaults: dict[str, Any], mode: str) -> vol.Schema:
    """Schema for electricity price details."""
    if mode == TARIFF_MODE_ENTITY:
        return vol.Schema(
            {
                _required_key(
                    CONF_ELECTRICITY_PRICE_ENTITY,
                    defaults,
                ): _entity_selector()
            }
        )
    return vol.Schema(
        {
            _required_key(
                CONF_ELECTRICITY_PRICE_VALUE,
                defaults,
            ): _number_selector(min_value=0, unit="ct/kWh")
        }
    )


_STATISTICS_NOTE = (
    "Entity-based prices require long-term statistics to be enabled on the sensor. "
    "Without statistics, the integration falls back to the current sensor state."
)


class PVEconomicsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PV Economics."""

    VERSION = 3

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return PVEconomicsOptionsFlow(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Step 1: Installation cost, commissioning date, and tracking start date."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if CONF_STATISTICS_START_DATE not in self._data:
            self._data[CONF_STATISTICS_START_DATE] = date.today().isoformat()

        if user_input is not None:
            errors = _validate_costs(user_input)
            if not errors:
                self._data.update(user_input)
                return await self.async_step_history()
            return self.async_show_form(
                step_id="user",
                data_schema=_costs_schema(self._data | user_input),
                errors=errors,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_costs_schema(self._data),
        )

    async def async_step_history(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Step 2: Pre-tracking financial totals (optional)."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_entities()

        return self.async_show_form(
            step_id="history",
            data_schema=_history_schema(self._data),
        )

    async def async_step_entities(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Step 3: Energy sensors, pricing modes, and projection settings."""
        if user_input is not None:
            errors = _validate_entities(user_input)
            if errors:
                return self.async_show_form(
                    step_id="entities",
                    data_schema=_entities_schema(self._data | user_input),
                    errors=errors,
                )
            self._data.update(user_input)
            if user_input.get(CONF_HAS_BATTERY):
                return await self.async_step_battery_type()
            for key in (
                CONF_BATTERY_SENSOR_TYPE,
                CONF_BATTERY_POWER_ENTITY,
                CONF_BATTERY_POWER_POSITIVE,
                CONF_BATTERY_CHARGE_ENTITY,
                CONF_BATTERY_DISCHARGE_ENTITY,
            ):
                self._data.pop(key, None)
            return await self.async_step_feed_in_tariff()

        return self.async_show_form(
            step_id="entities",
            data_schema=_entities_schema(self._data),
        )

    async def async_step_battery_type(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Step 3b: Battery sensor type selection."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_battery_sensors()

        return self.async_show_form(
            step_id="battery_type",
            data_schema=vol.Schema(
                {
                    _required_key(
                        CONF_BATTERY_SENSOR_TYPE,
                        self._data,
                        BATTERY_TYPE_TWO_SENSORS,
                    ): _battery_type_selector(),
                }
            ),
        )

    async def async_step_battery_sensors(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Step 3c: Battery sensor entity selection."""
        sensor_type = self._data.get(CONF_BATTERY_SENSOR_TYPE, BATTERY_TYPE_TWO_SENSORS)
        if user_input is not None:
            errors = _validate_battery_sensors(user_input, self._data)
            if errors:
                return self.async_show_form(
                    step_id="battery_sensors",
                    data_schema=self._battery_sensors_schema(
                        sensor_type, self._data | user_input
                    ),
                    errors=errors,
                )
            self._data.update(user_input)
            # Clear stale keys for whichever sensor type was NOT chosen
            if self._data.get(CONF_BATTERY_SENSOR_TYPE) == BATTERY_TYPE_BIDIRECTIONAL:
                self._data.pop(CONF_BATTERY_CHARGE_ENTITY, None)
                self._data.pop(CONF_BATTERY_DISCHARGE_ENTITY, None)
            else:
                self._data.pop(CONF_BATTERY_POWER_ENTITY, None)
                self._data.pop(CONF_BATTERY_POWER_POSITIVE, None)
            return await self.async_step_feed_in_tariff()

        return self.async_show_form(
            step_id="battery_sensors",
            data_schema=self._battery_sensors_schema(sensor_type, self._data),
        )

    @staticmethod
    def _battery_sensors_schema(
        sensor_type: str, defaults: dict[str, Any]
    ) -> vol.Schema:
        if sensor_type == BATTERY_TYPE_BIDIRECTIONAL:
            return vol.Schema(
                {
                    _required_key(
                        CONF_BATTERY_POWER_ENTITY, defaults
                    ): _entity_selector(),
                    _required_key(
                        CONF_BATTERY_POWER_POSITIVE, defaults, BATTERY_POSITIVE_CHARGE
                    ): _battery_positive_selector(),
                }
            )
        return vol.Schema(
            {
                _required_key(
                    CONF_BATTERY_CHARGE_ENTITY, defaults
                ): _energy_entity_selector(),
                _required_key(
                    CONF_BATTERY_DISCHARGE_ENTITY, defaults
                ): _energy_entity_selector(),
            }
        )

    async def async_step_feed_in_tariff(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Step 4: Feed-in tariff details."""
        mode = self._data.get(CONF_FEED_IN_TARIFF_MODE, TARIFF_MODE_FIXED)
        if user_input is not None:
            if mode == TARIFF_MODE_ENTITY:
                err = _validate_tariff_entity(
                    user_input[CONF_FEED_IN_TARIFF_ENTITY], self.hass
                )
                if err:
                    return self.async_show_form(
                        step_id="feed_in_tariff",
                        data_schema=_feed_in_schema(self._data | user_input, mode),
                        errors={CONF_FEED_IN_TARIFF_ENTITY: err},
                    )
            self._data.update(user_input)
            return await self.async_step_electricity_price()

        return self.async_show_form(
            step_id="feed_in_tariff",
            data_schema=_feed_in_schema(self._data, mode),
        )

    async def async_step_electricity_price(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Step 5: Electricity price details."""
        mode = self._data.get(CONF_ELECTRICITY_PRICE_MODE, TARIFF_MODE_FIXED)
        if user_input is not None:
            if mode == TARIFF_MODE_ENTITY:
                err = _validate_tariff_entity(
                    user_input[CONF_ELECTRICITY_PRICE_ENTITY], self.hass
                )
                if err:
                    return self.async_show_form(
                        step_id="electricity_price",
                        data_schema=_electricity_price_schema(
                            self._data | user_input, mode
                        ),
                        errors={CONF_ELECTRICITY_PRICE_ENTITY: err},
                        description_placeholders={"statistics_note": _STATISTICS_NOTE},
                    )
            self._data.update(user_input)
            return self.async_create_entry(title="PV Economics", data=self._data)

        return self.async_show_form(
            step_id="electricity_price",
            data_schema=_electricity_price_schema(self._data, mode),
            description_placeholders={"statistics_note": _STATISTICS_NOTE},
        )


class PVEconomicsOptionsFlow(OptionsFlow):
    """Handle PV Economics options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry
        self._data: dict[str, Any] = {
            **config_entry.data,
            **config_entry.options,
        }

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Step 1: Edit installation cost, commissioning date, tracking start date."""
        if user_input is not None:
            errors = _validate_costs(user_input)
            if not errors:
                self._data.update(user_input)
                return await self.async_step_history()
            return self.async_show_form(
                step_id="init",
                data_schema=_costs_schema(self._data | user_input),
                errors=errors,
            )

        return self.async_show_form(
            step_id="init",
            data_schema=_costs_schema(self._data),
        )

    async def async_step_history(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Step 2: Edit pre-tracking financial totals."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_entities()

        return self.async_show_form(
            step_id="history",
            data_schema=_history_schema(self._data),
        )

    async def async_step_entities(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Step 3: Edit energy sensors, pricing modes, and settings."""
        if user_input is not None:
            errors = _validate_entities(user_input)
            if errors:
                schema = _entities_schema(self._data | user_input).extend(
                    {
                        _optional_key(
                            CONF_UPDATE_INTERVAL_MINUTES,
                            self._data | user_input,
                            DEFAULT_UPDATE_INTERVAL_MINUTES,
                        ): _number_selector(min_value=1, unit="min")
                    }
                )
                return self.async_show_form(
                    step_id="entities",
                    data_schema=schema,
                    errors=errors,
                )
            self._data.update(user_input)
            if user_input.get(CONF_HAS_BATTERY):
                return await self.async_step_battery_type()
            for key in (
                CONF_BATTERY_SENSOR_TYPE,
                CONF_BATTERY_POWER_ENTITY,
                CONF_BATTERY_POWER_POSITIVE,
                CONF_BATTERY_CHARGE_ENTITY,
                CONF_BATTERY_DISCHARGE_ENTITY,
            ):
                self._data.pop(key, None)
            return await self.async_step_feed_in_tariff()

        schema = _entities_schema(self._data).extend(
            {
                _optional_key(
                    CONF_UPDATE_INTERVAL_MINUTES,
                    self._data,
                    DEFAULT_UPDATE_INTERVAL_MINUTES,
                ): _number_selector(min_value=1, unit="min")
            }
        )
        return self.async_show_form(
            step_id="entities",
            data_schema=schema,
        )

    async def async_step_battery_type(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Step 3b: Battery sensor type selection."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_battery_sensors()

        return self.async_show_form(
            step_id="battery_type",
            data_schema=vol.Schema(
                {
                    _required_key(
                        CONF_BATTERY_SENSOR_TYPE,
                        self._data,
                        BATTERY_TYPE_TWO_SENSORS,
                    ): _battery_type_selector(),
                }
            ),
        )

    async def async_step_battery_sensors(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Step 3c: Battery sensor entity selection."""
        sensor_type = self._data.get(CONF_BATTERY_SENSOR_TYPE, BATTERY_TYPE_TWO_SENSORS)
        if user_input is not None:
            errors = _validate_battery_sensors(user_input, self._data)
            if errors:
                return self.async_show_form(
                    step_id="battery_sensors",
                    data_schema=PVEconomicsConfigFlow._battery_sensors_schema(
                        sensor_type, self._data | user_input
                    ),
                    errors=errors,
                )
            self._data.update(user_input)
            # Clear stale keys for whichever sensor type was NOT chosen
            if self._data.get(CONF_BATTERY_SENSOR_TYPE) == BATTERY_TYPE_BIDIRECTIONAL:
                self._data.pop(CONF_BATTERY_CHARGE_ENTITY, None)
                self._data.pop(CONF_BATTERY_DISCHARGE_ENTITY, None)
            else:
                self._data.pop(CONF_BATTERY_POWER_ENTITY, None)
                self._data.pop(CONF_BATTERY_POWER_POSITIVE, None)
            return await self.async_step_feed_in_tariff()

        return self.async_show_form(
            step_id="battery_sensors",
            data_schema=PVEconomicsConfigFlow._battery_sensors_schema(
                sensor_type, self._data
            ),
        )

    async def async_step_feed_in_tariff(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Step 4: Edit feed-in tariff details."""
        mode = self._data.get(CONF_FEED_IN_TARIFF_MODE, TARIFF_MODE_FIXED)
        if user_input is not None:
            if mode == TARIFF_MODE_ENTITY:
                err = _validate_tariff_entity(
                    user_input[CONF_FEED_IN_TARIFF_ENTITY], self.hass
                )
                if err:
                    return self.async_show_form(
                        step_id="feed_in_tariff",
                        data_schema=_feed_in_schema(self._data | user_input, mode),
                        errors={CONF_FEED_IN_TARIFF_ENTITY: err},
                    )
            self._data.update(user_input)
            return await self.async_step_electricity_price()

        return self.async_show_form(
            step_id="feed_in_tariff",
            data_schema=_feed_in_schema(self._data, mode),
        )

    async def async_step_electricity_price(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Step 5: Edit electricity price details."""
        mode = self._data.get(CONF_ELECTRICITY_PRICE_MODE, TARIFF_MODE_FIXED)
        if user_input is not None:
            if mode == TARIFF_MODE_ENTITY:
                err = _validate_tariff_entity(
                    user_input[CONF_ELECTRICITY_PRICE_ENTITY], self.hass
                )
                if err:
                    return self.async_show_form(
                        step_id="electricity_price",
                        data_schema=_electricity_price_schema(
                            self._data | user_input, mode
                        ),
                        errors={CONF_ELECTRICITY_PRICE_ENTITY: err},
                        description_placeholders={"statistics_note": _STATISTICS_NOTE},
                    )
            self._data.update(user_input)
            return self.async_create_entry(title="", data=self._data)

        return self.async_show_form(
            step_id="electricity_price",
            data_schema=_electricity_price_schema(self._data, mode),
            description_placeholders={"statistics_note": _STATISTICS_NOTE},
        )
