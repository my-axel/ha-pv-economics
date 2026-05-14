"""Sensor platform for PV Economics."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
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
    VALUE_NET_YIELD,
    VALUE_SELF_CONSUMPTION,
    VALUE_SELF_CONSUMPTION_RATE,
    VALUE_SELF_SUFFICIENCY,
    VALUE_SYSTEM_AGE_DAYS,
    VALUE_TOTAL_SAVINGS,
    VALUE_TOTAL_YIELD,
)
from .coordinator import (
    _PRICE_FALLBACK_KEY,
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
        state_class=SensorStateClass.MEASUREMENT,
        unit_fn=_currency_unit,
        fallback_attr_key=_PRICE_FALLBACK_KEY,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_FEED_IN_REVENUE,
        translation_key=VALUE_FEED_IN_REVENUE,
        value_key=VALUE_FEED_IN_REVENUE,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        unit_fn=_currency_unit,
        fallback_attr_key=_TARIFF_FALLBACK_KEY,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_TOTAL_YIELD,
        translation_key=VALUE_TOTAL_YIELD,
        value_key=VALUE_TOTAL_YIELD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        unit_fn=_currency_unit,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_NET_YIELD,
        translation_key=VALUE_NET_YIELD,
        value_key=VALUE_NET_YIELD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
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
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.DAYS,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_AVERAGE_DAILY_YIELD,
        translation_key=VALUE_AVERAGE_DAILY_YIELD,
        value_key=VALUE_AVERAGE_DAILY_YIELD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        unit_fn=_currency_unit,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_SYSTEM_AGE_DAYS,
        translation_key=VALUE_SYSTEM_AGE_DAYS,
        value_key=VALUE_SYSTEM_AGE_DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.DAYS,
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
        """Expose fallback flag when an entity price had no long-term statistics."""
        key = self.entity_description.fallback_attr_key
        if key is None or not self.coordinator.data:
            return None
        fallback = self.coordinator.data.get(key, False)
        if fallback:
            return {"statistics_fallback": True}
        return None
