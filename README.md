# PV Economics

PV Economics is a HACS-compatible Home Assistant custom integration for calculating the financial performance of a PV installation.

This repository is currently an initial skeleton. Business logic for statistics fetching and calculations is intentionally not implemented yet.

## Planned Features

- Calculate PV self-consumption from long-term statistics.
- Calculate self-consumption rate and optional self-sufficiency.
- Calculate electricity savings from fixed or entity-based electricity prices.
- Calculate feed-in revenue from fixed or entity-based feed-in tariffs.
- Calculate total yield, amortization progress, and amortization date.
- Use Home Assistant recorder statistics instead of maintaining custom energy counters.
- Support HACS validation and Home Assistant test workflows.

## Scope

PV Economics focuses only on economics. It does not perform surplus management, device control, production forecasting, tax handling, battery correction, or maintenance-cost modeling.

## Installation

This integration is not ready for end users yet. Once released, install it through HACS as a custom repository and configure it from the Home Assistant UI.

## Development

```bash
pytest
ruff check .
mypy custom_components
```
