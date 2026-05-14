"""PV Economics integration setup."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_COMMISSIONING_DATE,
    CONF_HISTORICAL_FEED_IN,
    CONF_HISTORICAL_SAVINGS,
    CONF_STATISTICS_START_DATE,
    PLATFORMS,
)
from .coordinator import PVEconomicsCoordinator

_LOGGER = logging.getLogger(__name__)

type PVEconomicsConfigEntry = ConfigEntry[PVEconomicsCoordinator]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PVEconomicsConfigEntry,
) -> bool:
    """Set up PV Economics from a config entry."""
    coordinator = PVEconomicsCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(
    hass: HomeAssistant,
    entry: PVEconomicsConfigEntry,
) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant,
    entry: PVEconomicsConfigEntry,
) -> bool:
    """Unload a PV Economics config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Migrate older config entries to the current schema."""
    if entry.version == 1:
        # v1 had a single historical_offset and fetched stats from the
        # commissioning date. Preserve the old totals: put the offset into
        # savings, leave feed-in at 0, anchor the stats start date to the
        # commissioning date so HA-tracked totals remain unchanged.
        new_data = {**entry.data}
        old_offset = float(new_data.pop("historical_offset", 0.0) or 0.0)
        new_data.setdefault("historical_savings_eur", old_offset)
        new_data.setdefault("historical_feed_in_eur", 0.0)
        new_data.setdefault(
            CONF_STATISTICS_START_DATE, new_data[CONF_COMMISSIONING_DATE]
        )
        hass.config_entries.async_update_entry(entry, data=new_data, version=2)
        _LOGGER.info(
            "Migrated PV Economics entry %s from version 1 to 2", entry.entry_id
        )
    if entry.version == 2:
        # v2 used currency-specific key names. Rename to neutral names.
        new_data = {**entry.data}
        new_data[CONF_HISTORICAL_SAVINGS] = new_data.pop(
            "historical_savings_eur", 0.0
        )
        new_data[CONF_HISTORICAL_FEED_IN] = new_data.pop(
            "historical_feed_in_eur", 0.0
        )
        hass.config_entries.async_update_entry(entry, data=new_data, version=3)
        _LOGGER.info(
            "Migrated PV Economics entry %s from version 2 to 3", entry.entry_id
        )
    return True
