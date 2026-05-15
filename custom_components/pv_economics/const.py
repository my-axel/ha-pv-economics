"""Constants for the PV Economics integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "pv_economics"

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

CONF_INSTALLATION_COST = "installation_cost"
CONF_COMMISSIONING_DATE = "commissioning_date"
CONF_STATISTICS_START_DATE = "statistics_start_date"
CONF_HISTORICAL_SAVINGS = "historical_savings"
CONF_HISTORICAL_FEED_IN = "historical_feed_in"
CONF_FEED_IN_TARIFF_MODE = "feed_in_tariff_mode"
CONF_FEED_IN_TARIFF_VALUE = "feed_in_tariff_value"
CONF_FEED_IN_TARIFF_ENTITY = "feed_in_tariff_entity"
CONF_ELECTRICITY_PRICE_MODE = "electricity_price_mode"
CONF_ELECTRICITY_PRICE_VALUE = "electricity_price_value"
CONF_ELECTRICITY_PRICE_ENTITY = "electricity_price_entity"
CONF_PV_PRODUCTION_ENTITY = "pv_production_entity"
CONF_GRID_EXPORT_ENTITY = "grid_export_entity"
CONF_GRID_IMPORT_ENTITY = "grid_import_entity"
CONF_ROLLING_WINDOW_DAYS = "rolling_window_days"
CONF_UPDATE_INTERVAL_MINUTES = "update_interval_minutes"

CONF_HAS_BATTERY = "has_battery"
CONF_BATTERY_SENSOR_TYPE = "battery_sensor_type"
CONF_BATTERY_POWER_ENTITY = "battery_power_entity"
CONF_BATTERY_POWER_POSITIVE = "battery_power_positive"
CONF_BATTERY_CHARGE_ENTITY = "battery_charge_entity"
CONF_BATTERY_DISCHARGE_ENTITY = "battery_discharge_entity"

BATTERY_TYPE_BIDIRECTIONAL = "bidirectional_power"
BATTERY_TYPE_TWO_SENSORS = "two_energy"
BATTERY_POSITIVE_CHARGE = "charge"
BATTERY_POSITIVE_DISCHARGE = "discharge"

TARIFF_MODE_FIXED = "fixed"
TARIFF_MODE_ENTITY = "entity"
TARIFF_MODES = [TARIFF_MODE_FIXED, TARIFF_MODE_ENTITY]

DEFAULT_HISTORICAL_SAVINGS = 0.0
DEFAULT_HISTORICAL_FEED_IN = 0.0
DEFAULT_ROLLING_WINDOW_DAYS = 365
DEFAULT_UPDATE_INTERVAL_MINUTES = 5

VALUE_SELF_CONSUMPTION = "self_consumption"
VALUE_SELF_CONSUMPTION_RATE = "self_consumption_rate"
VALUE_SELF_SUFFICIENCY = "self_sufficiency"
VALUE_TOTAL_SAVINGS = "total_savings"
VALUE_FEED_IN_REVENUE = "feed_in_revenue"
VALUE_TOTAL_YIELD = "total_yield"
VALUE_NET_YIELD = "net_yield"
VALUE_AMORTIZATION_PROGRESS_PCT = "amortization_progress_pct"
VALUE_AMORTIZATION_DATE = "amortization_date"
VALUE_DAYS_TO_AMORTIZATION = "days_to_amortization"
VALUE_AVERAGE_DAILY_YIELD = "average_daily_yield"
VALUE_SYSTEM_AGE_DAYS = "system_age_days"
VALUE_IS_AMORTIZED = "is_amortized"
VALUE_YIELD_TODAY = "yield_today"
VALUE_YIELD_THIS_WEEK = "yield_this_week"
VALUE_YIELD_THIS_MONTH = "yield_this_month"
VALUE_YIELD_THIS_YEAR = "yield_this_year"
VALUE_SAVINGS_TODAY = "savings_today"
VALUE_SAVINGS_THIS_WEEK = "savings_this_week"
VALUE_SAVINGS_THIS_MONTH = "savings_this_month"
VALUE_SAVINGS_THIS_YEAR = "savings_this_year"
VALUE_FEED_IN_TODAY = "feed_in_today"
VALUE_FEED_IN_THIS_WEEK = "feed_in_this_week"
VALUE_FEED_IN_THIS_MONTH = "feed_in_this_month"
VALUE_FEED_IN_THIS_YEAR = "feed_in_this_year"
