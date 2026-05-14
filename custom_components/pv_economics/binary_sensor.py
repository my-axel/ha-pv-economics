"""Binary sensor platform for PV Economics."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import PVEconomicsConfigEntry
from .const import DOMAIN, VALUE_IS_AMORTIZED
from .coordinator import PVEconomicsCoordinator

IS_AMORTIZED_DESCRIPTION = BinarySensorEntityDescription(
    key=VALUE_IS_AMORTIZED,
    translation_key=VALUE_IS_AMORTIZED,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PVEconomicsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PV Economics binary sensors."""
    async_add_entities(
        [PVEconomicsBinarySensor(entry.runtime_data, entry, IS_AMORTIZED_DESCRIPTION)]
    )


class PVEconomicsBinarySensor(
    CoordinatorEntity[PVEconomicsCoordinator],
    BinarySensorEntity,
):
    """PV Economics binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PVEconomicsCoordinator,
        entry: PVEconomicsConfigEntry,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="PV Economics",
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether the PV installation is amortized."""
        # TODO: Return value from coordinator data once calculations exist.
        return None
