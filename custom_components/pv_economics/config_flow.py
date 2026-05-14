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

_MISSING = object()


def _number_selector(
    *,
    min_value: float | None = None,
    unit: str | None = None,
) -> NumberSelector:
    """Create a box-mode number selector."""
    config: dict[str, Any] = {"mode": NumberSelectorMode.BOX}
    if min_value is not None:
        config["min"] = min_value
    if unit is not None:
        config["unit_of_measurement"] = unit

    return NumberSelector(NumberSelectorConfig(config))


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
        )
    )


def _entity_selector() -> EntitySelector:
    """Create a generic entity selector."""
    return EntitySelector(EntitySelectorConfig(domain="sensor"))


def _required_key(
    key: str,
    defaults: dict[str, Any],
    fallback: Any = _MISSING,
) -> vol.Required:
    """Create a required schema key, omitting empty defaults."""
    default = defaults.get(key, fallback)
    if default is _MISSING or default is None:
        return vol.Required(key)
    return vol.Required(key, default=default)


def _optional_key(
    key: str,
    defaults: dict[str, Any],
    fallback: Any = _MISSING,
) -> vol.Optional:
    """Create an optional schema key, omitting empty defaults."""
    default = defaults.get(key, fallback)
    if default is _MISSING or default is None:
        return vol.Optional(key)
    return vol.Optional(key, default=default)


def _base_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Create schema for core integration settings."""
    return vol.Schema(
        {
            _required_key(CONF_INSTALLATION_COST, defaults): _number_selector(
                min_value=0
            ),
            _optional_key(
                CONF_HISTORICAL_OFFSET,
                defaults,
                DEFAULT_HISTORICAL_OFFSET,
            ): _number_selector(),
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
            _required_key(
                CONF_PV_PRODUCTION_ENTITY,
                defaults,
            ): _energy_entity_selector(),
            _required_key(
                CONF_GRID_EXPORT_ENTITY,
                defaults,
            ): _energy_entity_selector(),
            _optional_key(CONF_GRID_IMPORT_ENTITY, defaults): _energy_entity_selector(),
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
    """Create schema for feed-in tariff settings."""
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
    """Create schema for electricity price settings."""
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


def _options_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Create schema for options-only settings."""
    return vol.Schema(
        {
            _optional_key(
                CONF_UPDATE_INTERVAL_MINUTES,
                defaults,
                DEFAULT_UPDATE_INTERVAL_MINUTES,
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
