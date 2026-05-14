# Initial Specification: PV Economics

## Purpose

PV Economics is a focused Home Assistant custom integration that calculates the financial performance of a PV installation. It does not manage surplus power, control devices, or forecast production. Its scope is economics only.

## Architecture

- The integration is stateless with respect to energy accumulation. All kWh values are read from Home Assistant long-term statistics through `recorder.statistics` hourly buckets.
- Reset handling is delegated to Home Assistant's long-term statistics for `total_increasing` sensors. The integration must not maintain custom delta tracking.
- Dynamic price calculation is correlated by hour. When a price input is an entity, hourly self-consumption kWh is multiplied by the corresponding hourly mean price and summed. Dynamic prices must not use `total_kwh * current_price`.
- A single `DataUpdateCoordinator` runs on a configurable interval, defaulting to 5 minutes. It fetches statistics, computes derived values, and feeds all `CoordinatorEntity` sensors.
- No external dependencies beyond Home Assistant core are allowed. No cloud calls are made by this integration.

## Technical Baseline

- Python 3.12+
- Home Assistant 2024.10+
- HACS-compatible custom integration
- Fully async and fully type-hinted
- Use `ConfigEntry.runtime_data` for runtime coordinator storage
- Use `homeassistant.helpers.selector` for config and options flow inputs

## Repository Structure

```text
custom_components/
  pv_economics/
    __init__.py
    manifest.json
    const.py
    config_flow.py
    coordinator.py
    sensor.py
    binary_sensor.py
    statistics.py
    calculations.py
    translations/
      en.json
      de.json
tests/
  __init__.py
  conftest.py
  test_config_flow.py
  test_calculations.py
  test_coordinator.py
hacs.json
README.md
LICENSE
pyproject.toml
.github/workflows/
  validate.yml
  tests.yml
```

## Manifest And HACS Metadata

`manifest.json` essentials:

- `domain`: `pv_economics`
- `name`: `PV Economics`
- `version`: `0.1.0`
- `iot_class`: `local_polling`
- `config_flow`: `true`
- `integration_type`: `service`
- `dependencies`: `["recorder"]`
- `requirements`: `[]`

`hacs.json` essentials:

- `name`: `PV Economics`
- `render_readme`: `true`
- `homeassistant`: `"2024.10.0"`

## Configuration

The user flow configures economics, source entities, and tariff modes. The options flow allows all values to be edited after setup and also exposes `update_interval_minutes`.

Configuration fields:

- `installation_cost`: required float, in the Home Assistant configured currency
- `historical_offset`: optional float, default `0`
- `feed_in_tariff_mode`: `fixed` or `entity`
- `feed_in_tariff_value`: optional float, ct/kWh, required when feed-in tariff mode is `fixed`
- `feed_in_tariff_entity`: optional entity selector, required when feed-in tariff mode is `entity`
- `electricity_price_mode`: `fixed` or `entity`
- `electricity_price_value`: optional float, ct/kWh, required when electricity price mode is `fixed`
- `electricity_price_entity`: optional entity selector, required when electricity price mode is `entity`
- `pv_production_entity`: required energy entity
- `grid_export_entity`: required energy entity
- `grid_import_entity`: optional energy entity, required only for the self-sufficiency sensor
- `min_history_days`: optional int, default `60`
- `rolling_window_days`: optional int, default `365`
- `update_interval_minutes`: optional int, default `5`, options flow only

The initial implementation uses a multi-step flow so tariff fields are actually conditional.

## V1 Entities

All entities are grouped under a PV Economics device named from the integration entry title. Money units use `hass.config.currency`.

| Entity | Type | Unit | State class |
| --- | --- | --- | --- |
| `sensor.self_consumption` | sensor | kWh | `total_increasing` |
| `sensor.self_consumption_rate` | sensor | `%` | `measurement` |
| `sensor.self_sufficiency` | sensor | `%` | `measurement` |
| `sensor.total_savings` | sensor | currency | `total_increasing` |
| `sensor.feed_in_revenue` | sensor | currency | `total_increasing` |
| `sensor.total_yield` | sensor | currency | `total_increasing` |
| `sensor.amortization_progress` | sensor | currency | `measurement` |
| `sensor.amortization_progress_pct` | sensor | `%` | `measurement` |
| `sensor.amortization_date` | sensor | none | `device_class: date` |
| `binary_sensor.is_amortized` | binary sensor | none | none |

Only create `self_sufficiency` if `grid_import_entity` is configured.

## Later Calculation Logic

The future implementation will keep all calculation logic as pure functions in `calculations.py` with no Home Assistant imports.

- `self_consumption_kwh = production - export`, calculated per hour and then summed
- `self_consumption_rate = self_consumption / production`
- `self_sufficiency = self_consumption / (self_consumption + grid_import)`
- Entity-based electricity savings use `sum(self_consumption_kwh_hour * electricity_price_hour)`
- Fixed electricity savings use `self_consumption_total * price`
- Feed-in revenue follows the same fixed/entity split against export kWh
- `total_yield = savings + feed_in_revenue + historical_offset`
- `amortization_progress = total_yield`
- `amortization_progress_pct = total_yield / installation_cost`
- Amortization projection uses total-yield deltas over `rolling_window_days`, or all available days when below that window but at least `min_history_days`

## Edge Cases For Later Implementation

- If history is shorter than `min_history_days`, `amortization_date` is unknown.
- If daily average is less than or equal to zero, `amortization_date` is unknown.
- If `total_yield >= installation_cost`, `is_amortized` is true and `amortization_date` is the historical break-even date.
- If a price entity has no long-term statistics, log a warning, fall back to current state multiplied by total kWh, and expose this in entity attributes.
- Missing statistics buckets are skipped; no interpolation is performed.

## Initial Task Boundary

The initial task creates only the skeleton. It must not implement statistics fetching or calculation business logic. `config_flow.py` is the only file with real behavior at this stage.
