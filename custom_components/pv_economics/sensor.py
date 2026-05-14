"""Sensor platform for PV Economics."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import PVEconomicsConfigEntry
from .const import (
    CONF_GRID_IMPORT_ENTITY,
    DOMAIN,
    VALUE_AMORTIZATION_DATE,
    VALUE_AMORTIZATION_PROGRESS,
    VALUE_AMORTIZATION_PROGRESS_PCT,
    VALUE_FEED_IN_REVENUE,
    VALUE_SELF_CONSUMPTION,
    VALUE_SELF_CONSUMPTION_RATE,
    VALUE_SELF_SUFFICIENCY,
    VALUE_TOTAL_SAVINGS,
    VALUE_TOTAL_YIELD,
)
from .coordinator import PVEconomicsCoordinator


@dataclass(frozen=True, kw_only=True)
class PVEconomicsSensorEntityDescription(SensorEntityDescription):
    """Description for a PV Economics sensor."""

    value_key: str
    unit_fn: Callable[[HomeAssistant], str | None] | None = None


def _currency_unit(hass: HomeAssistant) -> str:
    """Return Home Assistant's configured currency."""
    return hass.config.currency


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
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit_fn=_currency_unit,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_FEED_IN_REVENUE,
        translation_key=VALUE_FEED_IN_REVENUE,
        value_key=VALUE_FEED_IN_REVENUE,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit_fn=_currency_unit,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_TOTAL_YIELD,
        translation_key=VALUE_TOTAL_YIELD,
        value_key=VALUE_TOTAL_YIELD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit_fn=_currency_unit,
    ),
    PVEconomicsSensorEntityDescription(
        key=VALUE_AMORTIZATION_PROGRESS,
        translation_key=VALUE_AMORTIZATION_PROGRESS,
        value_key=VALUE_AMORTIZATION_PROGRESS,
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
            description
            for description in descriptions
            if description.key != VALUE_SELF_SUFFICIENCY
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
        """Return the sensor value."""
        # TODO: Return values from coordinator data once calculations exist.
        return None
