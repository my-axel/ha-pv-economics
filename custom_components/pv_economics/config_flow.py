"""Config flow for PV Economics."""

from __future__ import annotations

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
    DateSelector,
    DateSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
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
    TARIFF_MODE_FIXED,
    TARIFF_MODES,
)

_MISSING = object()


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
    """Schema for installation cost and financial baseline."""
    return vol.Schema(
        {
            _required_key(CONF_INSTALLATION_COST, defaults): _number_selector(
                min_value=0
            ),
            _required_key(CONF_COMMISSIONING_DATE, defaults): DateSelector(
                DateSelectorConfig()
            ),
            _optional_key(
                CONF_HISTORICAL_OFFSET,
                defaults,
                DEFAULT_HISTORICAL_OFFSET,
            ): _number_selector(),
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
                CONF_MIN_HISTORY_DAYS,
                defaults,
                DEFAULT_MIN_HISTORY_DAYS,
            ): _number_selector(min_value=1),
            _optional_key(
                CONF_ROLLING_WINDOW_DAYS,
                defaults,
                DEFAULT_ROLLING_WINDOW_DAYS,
            ): _number_selector(min_value=1),
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

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return PVEconomicsOptionsFlow(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Step 1: Installation costs and financial baseline."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_entities()

        return self.async_show_form(
            step_id="user",
            data_schema=_costs_schema(self._data),
        )

    async def async_step_entities(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Step 2: Energy sensors, pricing modes, and projection settings."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_feed_in_tariff()

        return self.async_show_form(
            step_id="entities",
            data_schema=_entities_schema(self._data),
        )

    async def async_step_feed_in_tariff(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Step 3: Feed-in tariff details."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_electricity_price()

        mode = self._data.get(CONF_FEED_IN_TARIFF_MODE, TARIFF_MODE_FIXED)
        return self.async_show_form(
            step_id="feed_in_tariff",
            data_schema=_feed_in_schema(self._data, mode),
        )

    async def async_step_electricity_price(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Step 4: Electricity price details."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="PV Economics", data=self._data)

        mode = self._data.get(CONF_ELECTRICITY_PRICE_MODE, TARIFF_MODE_FIXED)
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
        """Step 1: Edit installation costs and financial baseline."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_entities()

        return self.async_show_form(
            step_id="init",
            data_schema=_costs_schema(self._data),
        )

    async def async_step_entities(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Step 2: Edit energy sensors, pricing modes, and settings."""
        if user_input is not None:
            self._data.update(user_input)
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

    async def async_step_feed_in_tariff(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Step 3: Edit feed-in tariff details."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_electricity_price()

        mode = self._data.get(CONF_FEED_IN_TARIFF_MODE, TARIFF_MODE_FIXED)
        return self.async_show_form(
            step_id="feed_in_tariff",
            data_schema=_feed_in_schema(self._data, mode),
        )

    async def async_step_electricity_price(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Step 4: Edit electricity price details."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="", data=self._data)

        mode = self._data.get(CONF_ELECTRICITY_PRICE_MODE, TARIFF_MODE_FIXED)
        return self.async_show_form(
            step_id="electricity_price",
            data_schema=_electricity_price_schema(self._data, mode),
            description_placeholders={"statistics_note": _STATISTICS_NOTE},
        )
