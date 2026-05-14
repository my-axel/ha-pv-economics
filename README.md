# PV Economics

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

Home Assistant integration that calculates the financial performance of a PV installation. It reads energy data from HA long-term statistics — no cloud, no external dependencies.

## What it tracks

| Sensor | Description |
|---|---|
| Self-consumption | Total kWh consumed directly from PV |
| Self-consumption rate | Self-consumption / total production |
| Self-sufficiency | Self-consumption / (self-consumption + grid import) |
| Total savings | Avoided electricity costs (pre-tracking total + HA-tracked) |
| Feed-in revenue | Grid export earnings (pre-tracking total + HA-tracked) |
| Total yield | Savings + feed-in revenue |
| Net yield | Total yield − installation cost (negative until break-even) |
| Amortization progress | Total yield as % of installation cost |
| Amortization date | Historical break-even date or projected future date |
| Days to amortization | Days remaining until break-even (0 when already amortized) |
| Average daily yield | Rolling-window average EUR/day used for projection |
| System age | Days since commissioning date |
| Is amortized | Binary sensor — true when total yield ≥ installation cost |

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

Setup is split into five steps:

**Step 1 — Installation costs**

| Field | Description |
|---|---|
| Installation cost | Total cost of the PV system (EUR) |
| Commissioning date | Date the system was first switched on |
| Tracking start date | Date from which HA statistics are read (default: today) |

**Step 2 — Pre-tracking totals** *(optional, both default to 0)*

| Field | Description |
|---|---|
| Electricity savings up to tracking start | Total savings earned before the tracking start date |
| Feed-in revenue up to tracking start | Total feed-in revenue earned before the tracking start date |

Enter your all-time totals as of the tracking start date. The integration adds all future earnings on top automatically. If you are setting up the integration on the day the system was installed, leave both at 0.

**Steps 3–5** — Energy sensors, feed-in tariff, electricity price (fixed ct/kWh or a dynamic sensor entity).

All settings can be changed after setup via the integration's **Configure** button.

## How savings and revenue are calculated

All financial sensors include both pre-tracking totals and HA-tracked amounts:

```
total_savings   = historical_savings_eur   + HA-tracked savings (from tracking start date)
feed_in_revenue = historical_feed_in_eur   + HA-tracked feed-in (from tracking start date)
total_yield     = total_savings + feed_in_revenue
```

Self-consumption rate and self-sufficiency are computed only for the period where both production and export statistics overlap. Pre-tracking kWh data cannot be recovered.

## Development

```bash
uv pip install homeassistant pytest pytest-asyncio
.venv/bin/python -m pytest
.venv/bin/ruff check custom_components/pv_economics/
```

---

*This integration was built entirely with AI assistance:*
- *[Claude Code](https://claude.ai/code) — Anthropic's agentic coding CLI*
- *[Codex](https://openai.com/codex) — OpenAI's AI coding tool*
