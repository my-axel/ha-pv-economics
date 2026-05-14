# PV Economics

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

Home Assistant integration that calculates the financial performance of a PV installation. It reads energy data from HA long-term statistics — no cloud, no external dependencies.

## What it tracks

- **Self-consumption** and self-consumption rate
- **Self-sufficiency** (optional, requires grid import sensor)
- **Electricity savings** — fixed price or dynamic hourly price entity
- **Feed-in revenue** — fixed tariff or dynamic hourly tariff entity
- **Total yield** and amortization progress
- **Amortization date** — projected break-even based on recent performance

Out of scope: surplus management, device control, production forecasting, battery correction.

## Requirements

- Home Assistant 2024.10+
- Energy sensors with long-term statistics (`total_increasing`)

## Installation

1. Add this repository to HACS as a custom repository
2. Install **PV Economics**
3. Restart Home Assistant
4. Add the integration via **Settings → Devices & Services**

## Configuration

| Field | Description |
|---|---|
| Installation cost | Total cost of the PV system |
| Commissioning date | Date the system was first switched on |
| Historical offset | Earnings before this integration was set up |
| PV production entity | Energy sensor for total production |
| Grid export entity | Energy sensor for grid export |
| Grid import entity | *(Optional)* Required for self-sufficiency |
| Electricity price | Fixed ct/kWh or a sensor entity |
| Feed-in tariff | Fixed ct/kWh or a sensor entity |

All settings can be changed after setup via the integration's **Configure** button.

## Development

```bash
uv pip install homeassistant pytest pytest-asyncio
.venv/bin/python -m pytest
.venv/bin/ruff check custom_components/pv_economics/
```
