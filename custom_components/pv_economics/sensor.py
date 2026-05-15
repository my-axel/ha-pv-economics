"""Sensor platform for PV Economics."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import PVEconomicsConfigEntry
from .const import (
    CONF_GRID_IMPORT_ENTITY,
    DOMAIN,
    VALUE_AMORTIZATION_DATE,
    VALUE_AMORTIZATION_PROGRESS_PCT,
    VALUE_AVERAGE_DAILY_YIELD,
    VALUE_DAYS_TO_AMORTIZATION,
    VALUE_FEED_IN_REVENUE,
    VALUE_FEED_IN_THIS_MONTH,
    VALUE_FEED_IN_THIS_WEEK,
    VALUE_FEED_IN_THIS_YEAR,
    VALUE_FEED_IN_TODAY,
    VALUE_NET_YIELD,
    VALUE_SAVINGS_THIS_MONTH,
    VALUE_SAVINGS_THIS_WEEK,
    VALUE_SAVINGS_THIS_YEAR,
    VALUE_SAVINGS_TODAY,
    VALUE_SELF_CONSUMPTION,
    VALUE_SELF_CONSUMPTION_RATE,
    VALUE_SELF_SUFFICIENCY,
    VALUE_SYSTEM_AGE_DAYS,
    VALUE_TOTAL_SAVINGS,
    VALUE_TOTAL_YIELD,
    VALUE_YIELD_THIS_MONTH,
    VALUE_YIELD_THIS_WEEK,
    VALUE_YIELD_THIS_YEAR,
    VALUE_YIELD_TODAY,
)
from .coordinator import (
    _FEED_IN_FROM_STATS_KEY,
    _HIST_FEED_IN_KEY,
    _HIST_SAVINGS_KEY,
    _PRICE_FALLBACK_KEY,
    _SAVINGS_FROM_STATS_KEY,
    _STATS_FIRST_DATE_KEY,
    _STATS_HOURS_KEY,
    _STATS_LAST_DATE_KEY,
    _TARIFF_FALLBACK_KEY,
    PVEconomicsCoordinator,
)


def _currency_unit(hass: HomeAssistant) -> str:
    """Return Home Assistant's configured currency."""
    return hass.config.currency


@dataclass(frozen=True, kw_only=True)
class PVEconomicsSensorEntityDescription(SensorEntityDescription):
    """Description for a PV Economics sensor."""

    value_key: str
    unit_fn: Callable[[HomeAssistant], str | None] | None = None
    fallback_attr_key: str | None = None
    # Maps coordinator data key → attribute name exposed via extra_state_attributes
    diagnostic_attr_keys: dict[str, str] = field(default_factory=dict)


SENSOR_DESCRIPTIONS: tuple[PVEconomicsSensorEntityDescription, ...] = (
    PVEconomicsSensorEntityDescription(
        key=VALUE_SELF_CONSUMPTION,
        translation_key=VALUE_SELF_CONSUMPTION,
        value_key=VALUE_SELF_CONSUMPTION,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_SELF_CONSUMPTION_RATE,
        translation_key=VALUE_SELF_CONSUMPTION_RATE,
        value_key=VALUE_SELF_CONSUMPTION_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_SELF_SUFFICIENCY,
        translation_key=VALUE_SELF_SUFFICIENCY,
        value_key=VALUE_SELF_SUFFICIENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_TOTAL_SAVINGS,
        translation_key=VALUE_TOTAL_SAVINGS,
        value_key=VALUE_TOTAL_SAVINGS,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        unit_fn=_currency_unit,
        fallback_attr_key=_PRICE_FALLBACK_KEY,
        diagnostic_attr_keys={
            _SAVINGS_FROM_STATS_KEY: "from_statistics",
            _HIST_SAVINGS_KEY: "historical_offset",
        },
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_FEED_IN_REVENUE,
        translation_key=VALUE_FEED_IN_REVENUE,
        value_key=VALUE_FEED_IN_REVENUE,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        unit_fn=_currency_unit,
        fallback_attr_key=_TARIFF_FALLBACK_KEY,
        diagnostic_attr_keys={
            _FEED_IN_FROM_STATS_KEY: "from_statistics",
            _HIST_FEED_IN_KEY: "historical_offset",
        },
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_TOTAL_YIELD,
        translation_key=VALUE_TOTAL_YIELD,
        value_key=VALUE_TOTAL_YIELD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        unit_fn=_currency_unit,
        diagnostic_attr_keys={
            _STATS_FIRST_DATE_KEY: "statistics_from",
            _STATS_LAST_DATE_KEY: "statistics_until",
            _STATS_HOURS_KEY: "data_hours",
        },
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_NET_YIELD,
        translation_key=VALUE_NET_YIELD,
        value_key=VALUE_NET_YIELD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        unit_fn=_currency_unit,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_AMORTIZATION_PROGRESS_PCT,
        translation_key=VALUE_AMORTIZATION_PROGRESS_PCT,
        value_key=VALUE_AMORTIZATION_PROGRESS_PCT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_AMORTIZATION_DATE,
        translation_key=VALUE_AMORTIZATION_DATE,
        value_key=VALUE_AMORTIZATION_DATE,
        device_class=SensorDeviceClass.DATE,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_DAYS_TO_AMORTIZATION,
        translation_key=VALUE_DAYS_TO_AMORTIZATION,
        value_key=VALUE_DAYS_TO_AMORTIZATION,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.DAYS,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_AVERAGE_DAILY_YIELD,
        translation_key=VALUE_AVERAGE_DAILY_YIELD,
        value_key=VALUE_AVERAGE_DAILY_YIELD,
        device_class=SensorDeviceClass.MONETARY,
        unit_fn=_currency_unit,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_SYSTEM_AGE_DAYS,
        translation_key=VALUE_SYSTEM_AGE_DAYS,
        value_key=VALUE_SYSTEM_AGE_DAYS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.DAYS,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_YIELD_TODAY,
        translation_key=VALUE_YIELD_TODAY,
        value_key=VALUE_YIELD_TODAY,
        device_class=SensorDeviceClass.MONETARY,
        unit_fn=_currency_unit,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_YIELD_THIS_WEEK,
        translation_key=VALUE_YIELD_THIS_WEEK,
        value_key=VALUE_YIELD_THIS_WEEK,
        device_class=SensorDeviceClass.MONETARY,
        unit_fn=_currency_unit,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_YIELD_THIS_MONTH,
        translation_key=VALUE_YIELD_THIS_MONTH,
        value_key=VALUE_YIELD_THIS_MONTH,
        device_class=SensorDeviceClass.MONETARY,
        unit_fn=_currency_unit,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_YIELD_THIS_YEAR,
        translation_key=VALUE_YIELD_THIS_YEAR,
        value_key=VALUE_YIELD_THIS_YEAR,
        device_class=SensorDeviceClass.MONETARY,
        unit_fn=_currency_unit,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_SAVINGS_TODAY,
        translation_key=VALUE_SAVINGS_TODAY,
        value_key=VALUE_SAVINGS_TODAY,
        device_class=SensorDeviceClass.MONETARY,
        unit_fn=_currency_unit,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_SAVINGS_THIS_WEEK,
        translation_key=VALUE_SAVINGS_THIS_WEEK,
        value_key=VALUE_SAVINGS_THIS_WEEK,
        device_class=SensorDeviceClass.MONETARY,
        unit_fn=_currency_unit,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_SAVINGS_THIS_MONTH,
        translation_key=VALUE_SAVINGS_THIS_MONTH,
        value_key=VALUE_SAVINGS_THIS_MONTH,
        device_class=SensorDeviceClass.MONETARY,
        unit_fn=_currency_unit,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_SAVINGS_THIS_YEAR,
        translation_key=VALUE_SAVINGS_THIS_YEAR,
        value_key=VALUE_SAVINGS_THIS_YEAR,
        device_class=SensorDeviceClass.MONETARY,
        unit_fn=_currency_unit,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_FEED_IN_TODAY,
        translation_key=VALUE_FEED_IN_TODAY,
        value_key=VALUE_FEED_IN_TODAY,
        device_class=SensorDeviceClass.MONETARY,
        unit_fn=_currency_unit,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_FEED_IN_THIS_WEEK,
        translation_key=VALUE_FEED_IN_THIS_WEEK,
        value_key=VALUE_FEED_IN_THIS_WEEK,
        device_class=SensorDeviceClass.MONETARY,
        unit_fn=_currency_unit,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_FEED_IN_THIS_MONTH,
        translation_key=VALUE_FEED_IN_THIS_MONTH,
        value_key=VALUE_FEED_IN_THIS_MONTH,
        device_class=SensorDeviceClass.MONETARY,
        unit_fn=_currency_unit,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_FEED_IN_THIS_YEAR,
        translation_key=VALUE_FEED_IN_THIS_YEAR,
        value_key=VALUE_FEED_IN_THIS_YEAR,
        device_class=SensorDeviceClass.MONETARY,
        unit_fn=_currency_unit,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PVEconomicsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PV Economics sensors."""
    coordinator = entry.runtime_data
    descriptions = list(SENSOR_DESCRIPTIONS)

    if CONF_GRID_IMPORT_ENTITY not in {**entry.data, **entry.options}:
        descriptions = [
            d for d in descriptions if d.key != VALUE_SELF_SUFFICIENCY
        ]

    async_add_entities(
        PVEconomicsSensor(coordinator, entry, description)
        for description in descriptions
    )


class PVEconomicsSensor(CoordinatorEntity[PVEconomicsCoordinator], SensorEntity):
    """PV Economics sensor."""

    entity_description: PVEconomicsSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PVEconomicsCoordinator,
        entry: PVEconomicsConfigEntry,
        description: PVEconomicsSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="PV Economics",
        )
        if description.unit_fn is not None:
            self._attr_native_unit_of_measurement = description.unit_fn(
                coordinator.hass
            )

    @property
    def native_value(self) -> float | date | None:
        """Return the sensor value from coordinator data."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self.entity_description.value_key)  # type: ignore[return-value]

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose diagnostic and fallback attributes."""
        if not self.coordinator.data:
            return None
        attrs: dict[str, Any] = {}
        for data_key, attr_name in self.entity_description.diagnostic_attr_keys.items():
            val = self.coordinator.data.get(data_key)
            if val is not None:
                attrs[attr_name] = val
        fallback_key = self.entity_description.fallback_attr_key
        if fallback_key and self.coordinator.data.get(fallback_key):
            attrs["statistics_fallback"] = True
        return attrs or None
