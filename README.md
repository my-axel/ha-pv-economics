# PV Economics

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

Home Assistant integration for tracking the financial return of a solar installation. Reads energy data directly from HA long-term statistics — no cloud, no external dependencies.

## What it does

- Calculates savings (avoided electricity cost) and feed-in revenue since commissioning
- Projects the amortization date based on a configurable rolling yield average
- Period sensors for today, this week, this month, and this year
- Seasonal sensors: monthly performance vs. expectation and projected annual yield
- Optional battery storage support with round-trip loss correction
- Monthly yield attribute ready for use with graph cards

## Requirements

- Home Assistant 2024.10+
- PV production and grid export sensors with long-term statistics (`state_class: total_increasing`)

## Installation

**Via HACS (recommended)**

1. Add this repository to HACS as a custom repository
2. Install **PV Economics** and restart Home Assistant
3. Go to **Settings → Devices & Services** and add the integration

**Manual**

Copy `custom_components/pv_economics/` into your HA `custom_components` directory, restart, then add via **Settings → Devices & Services**.

## Sensors

| Sensor | Description |
|---|---|
| Self-consumption | kWh consumed directly from PV |
| Self-consumption rate | Self-consumption ÷ total production |
| Self-sufficiency | Self-consumption ÷ (self-consumption + grid import) |
| Total savings | Avoided electricity costs since commissioning |
| Feed-in revenue | Grid export earnings since commissioning |
| Total yield | Savings + feed-in revenue |
| Net yield | Total yield − installation cost |
| Amortization progress | Total yield as % of installation cost |
| Amortization date | Break-even date — historical or projected |
| Days to amortization | Days remaining until break-even |
| Average daily yield | Rolling average (default: 365-day window) |
| System age | Days since commissioning date |
| Yield / Savings / Feed-in — today / this week / this month / this year | Period totals |
| Monthly performance vs. expected | This month's yield vs. seasonal expectation (requires 12 months of history) |
| Projected yield this year | Year-to-date plus seasonal forecast for remaining months |
| Is amortized | Binary sensor, true when total yield ≥ installation cost |

## Documentation

Full documentation including configuration walkthrough and dashboard examples: [ha-pv-economics.readthedocs.io](https://ha-pv-economics.readthedocs.io)

---

*Built with [Claude Code](https://claude.ai/code) and [Codex](https://openai.com/codex).*
