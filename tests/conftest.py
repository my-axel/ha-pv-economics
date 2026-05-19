"""Shared pytest fixtures for PV Economics tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.pv_economics.config_flow import PVEconomicsConfigFlow
from custom_components.pv_economics.const import (
    CONF_COMMISSIONING_DATE,
    CONF_INSTALLATION_COST,
    CONF_STATISTICS_START_DATE,
)


@pytest.fixture
def config_flow() -> PVEconomicsConfigFlow:
    flow = PVEconomicsConfigFlow()
    flow.async_set_unique_id = AsyncMock(return_value=None)
    flow._abort_if_unique_id_configured = MagicMock()
    return flow


@pytest.fixture
def config_flow_with_hass(config_flow: PVEconomicsConfigFlow) -> PVEconomicsConfigFlow:
    config_flow.hass = MagicMock()
    return config_flow


@pytest.fixture
def base_costs() -> dict:
    return {
        CONF_INSTALLATION_COST: 10000.0,
        CONF_COMMISSIONING_DATE: "2023-01-01",
        CONF_STATISTICS_START_DATE: "2023-06-01",
    }
