"""Repair issues for PV Economics."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)

from .const import DOMAIN


def async_handle_fallback_repairs(
    hass: HomeAssistant,
    price_entity: str | None,
    tariff_entity: str | None,
    price_fallback: bool,
    tariff_fallback: bool,
) -> None:
    """Create or clear repair issues for statistics-fallback price sources."""
    if price_fallback and price_entity:
        async_create_issue(
            hass,
            DOMAIN,
            "price_entity_no_statistics",
            is_fixable=False,
            severity=IssueSeverity.WARNING,
            translation_key="price_entity_no_statistics",
            translation_placeholders={"entity_id": price_entity},
        )
    else:
        async_delete_issue(hass, DOMAIN, "price_entity_no_statistics")

    if tariff_fallback and tariff_entity:
        async_create_issue(
            hass,
            DOMAIN,
            "tariff_entity_no_statistics",
            is_fixable=False,
            severity=IssueSeverity.WARNING,
            translation_key="tariff_entity_no_statistics",
            translation_placeholders={"entity_id": tariff_entity},
        )
    else:
        async_delete_issue(hass, DOMAIN, "tariff_entity_no_statistics")
