"""Constants for the PV Economics integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "pv_economics"

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

CONF_INSTALLATION_COST = "installation_cost"
CONF_COMMISSIONING_DATE = "commissioning_date"
CONF_HISTORICAL_OFFSET = "historical_offset"
CONF_FEED_IN_TARIFF_MODE = "feed_in_tariff_mode"
CONF_FEED_IN_TARIFF_VALUE = "feed_in_tariff_value"
CONF_FEED_IN_TARIFF_ENTITY = "feed_in_tariff_entity"
CONF_ELECTRICITY_PRICE_MODE = "electricity_price_mode"
CONF_ELECTRICITY_PRICE_VALUE = "electricity_price_value"
CONF_ELECTRICITY_PRICE_ENTITY = "electricity_price_entity"
CONF_PV_PRODUCTION_ENTITY = "pv_production_entity"
CONF_GRID_EXPORT_ENTITY = "grid_export_entity"
CONF_GRID_IMPORT_ENTITY = "grid_import_entity"
CONF_MIN_HISTORY_DAYS = "min_history_days"
CONF_ROLLING_WINDOW_DAYS = "rolling_window_days"
CONF_UPDATE_INTERVAL_MINUTES = "update_interval_minutes"

TARIFF_MODE_FIXED = "fixed"
TARIFF_MODE_ENTITY = "entity"
TARIFF_MODES = [TARIFF_MODE_FIXED, TARIFF_MODE_ENTITY]

DEFAULT_HISTORICAL_OFFSET = 0.0
DEFAULT_MIN_HISTORY_DAYS = 60
DEFAULT_ROLLING_WINDOW_DAYS = 365
DEFAULT_UPDATE_INTERVAL_MINUTES = 5

VALUE_SELF_CONSUMPTION = "self_consumption"
VALUE_SELF_CONSUMPTION_RATE = "self_consumption_rate"
VALUE_SELF_SUFFICIENCY = "self_sufficiency"
VALUE_TOTAL_SAVINGS = "total_savings"
VALUE_FEED_IN_REVENUE = "feed_in_revenue"
VALUE_TOTAL_YIELD = "total_yield"
VALUE_AMORTIZATION_PROGRESS = "amortization_progress"
VALUE_AMORTIZATION_PROGRESS_PCT = "amortization_progress_pct"
VALUE_NET_YIELD = "net_yield"
VALUE_AMORTIZATION_DATE = "amortization_date"
VALUE_IS_AMORTIZED = "is_amortized"
