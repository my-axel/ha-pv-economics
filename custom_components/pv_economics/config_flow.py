"""Config flow for PV Economics."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.helpers.selector import (
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


def _number_selector(
    *,
    min_value: float | None = None,
    unit: str | None = None,
) -> NumberSelector:
    """Create a box-mode number selector."""
    return NumberSelector(
        NumberSelectorConfig(
            min=min_value,
            mode=NumberSelectorMode.BOX,
            unit_of_measurement=unit,
        )
    )


def _tariff_mode_selector() -> SelectSelector:
    """Create the tariff mode selector."""
    return SelectSelector(
        SelectSelectorConfig(
            options=TARIFF_MODES,
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def _energy_entity_selector() -> EntitySelector:
    """Create an energy entity selector for total-increasing sensors."""
    return EntitySelector(
        EntitySelectorConfig(
            domain="sensor",
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
        )
    )


def _entity_selector() -> EntitySelector:
    """Create a generic entity selector."""
    return EntitySelector(EntitySelectorConfig(domain="sensor"))


def _base_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Create schema for core integration settings."""
    return vol.Schema(
        {
            vol.Required(
                CONF_INSTALLATION_COST,
                default=defaults.get(CONF_INSTALLATION_COST),
            ): _number_selector(min_value=0),
            vol.Optional(
                CONF_HISTORICAL_OFFSET,
                default=defaults.get(
                    CONF_HISTORICAL_OFFSET,
                    DEFAULT_HISTORICAL_OFFSET,
                ),
            ): _number_selector(),
            vol.Required(
                CONF_FEED_IN_TARIFF_MODE,
                default=defaults.get(CONF_FEED_IN_TARIFF_MODE, TARIFF_MODE_FIXED),
            ): _tariff_mode_selector(),
            vol.Required(
                CONF_ELECTRICITY_PRICE_MODE,
                default=defaults.get(CONF_ELECTRICITY_PRICE_MODE, TARIFF_MODE_FIXED),
            ): _tariff_mode_selector(),
            vol.Required(
                CONF_PV_PRODUCTION_ENTITY,
                default=defaults.get(CONF_PV_PRODUCTION_ENTITY),
            ): _energy_entity_selector(),
            vol.Required(
                CONF_GRID_EXPORT_ENTITY,
                default=defaults.get(CONF_GRID_EXPORT_ENTITY),
            ): _energy_entity_selector(),
            vol.Optional(
                CONF_GRID_IMPORT_ENTITY,
                default=defaults.get(CONF_GRID_IMPORT_ENTITY),
            ): _energy_entity_selector(),
            vol.Optional(
                CONF_MIN_HISTORY_DAYS,
                default=defaults.get(CONF_MIN_HISTORY_DAYS, DEFAULT_MIN_HISTORY_DAYS),
            ): _number_selector(min_value=1),
            vol.Optional(
                CONF_ROLLING_WINDOW_DAYS,
                default=defaults.get(
                    CONF_ROLLING_WINDOW_DAYS,
                    DEFAULT_ROLLING_WINDOW_DAYS,
                ),
            ): _number_selector(min_value=1),
        }
    )


def _feed_in_schema(defaults: dict[str, Any], mode: str) -> vol.Schema:
    """Create schema for feed-in tariff settings."""
    if mode == TARIFF_MODE_ENTITY:
        return vol.Schema(
            {
                vol.Required(
                    CONF_FEED_IN_TARIFF_ENTITY,
                    default=defaults.get(CONF_FEED_IN_TARIFF_ENTITY),
                ): _entity_selector()
            }
        )

    return vol.Schema(
        {
            vol.Required(
                CONF_FEED_IN_TARIFF_VALUE,
                default=defaults.get(CONF_FEED_IN_TARIFF_VALUE),
            ): _number_selector(min_value=0, unit="ct/kWh")
        }
    )


def _electricity_price_schema(defaults: dict[str, Any], mode: str) -> vol.Schema:
    """Create schema for electricity price settings."""
    if mode == TARIFF_MODE_ENTITY:
        return vol.Schema(
            {
                vol.Required(
                    CONF_ELECTRICITY_PRICE_ENTITY,
                    default=defaults.get(CONF_ELECTRICITY_PRICE_ENTITY),
                ): _entity_selector()
            }
        )

    return vol.Schema(
        {
            vol.Required(
                CONF_ELECTRICITY_PRICE_VALUE,
                default=defaults.get(CONF_ELECTRICITY_PRICE_VALUE),
            ): _number_selector(min_value=0, unit="ct/kWh")
        }
    )


def _options_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Create schema for options-only settings."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_UPDATE_INTERVAL_MINUTES,
                default=defaults.get(
                    CONF_UPDATE_INTERVAL_MINUTES,
                    DEFAULT_UPDATE_INTERVAL_MINUTES,
                ),
            ): _number_selector(min_value=1, unit="min")
        }
    )


class PVEconomicsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PV Economics."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Create the options flow."""
        return PVEconomicsOptionsFlow(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_feed_in_tariff()

        return self.async_show_form(
            step_id="user",
            data_schema=_base_schema(self._data),
        )

    async def async_step_feed_in_tariff(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle feed-in tariff details."""
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
        """Handle electricity price details."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="PV Economics", data=self._data)

        mode = self._data.get(CONF_ELECTRICITY_PRICE_MODE, TARIFF_MODE_FIXED)
        return self.async_show_form(
            step_id="electricity_price",
            data_schema=_electricity_price_schema(self._data, mode),
            description_placeholders={
                "statistics_note": "Entity prices should expose long-term statistics.",
            },
        )


class PVEconomicsOptionsFlow(OptionsFlow):
    """Handle PV Economics options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self._data: dict[str, Any] = {
            **config_entry.data,
            **config_entry.options,
        }

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle editable base options."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_feed_in_tariff()

        return self.async_show_form(
            step_id="init",
            data_schema=_base_schema(self._data).extend(
                _options_schema(self._data).schema
            ),
        )

    async def async_step_feed_in_tariff(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle editable feed-in tariff details."""
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
        """Handle editable electricity price details."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="", data=self._data)

        mode = self._data.get(CONF_ELECTRICITY_PRICE_MODE, TARIFF_MODE_FIXED)
        return self.async_show_form(
            step_id="electricity_price",
            data_schema=_electricity_price_schema(self._data, mode),
            description_placeholders={
                "statistics_note": "Entity prices should expose long-term statistics.",
            },
        )
