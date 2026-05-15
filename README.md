# PV Economics

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

Home Assistant integration that calculates the financial performance of a PV installation. Reads energy data from HA long-term statistics — no cloud, no external dependencies.

## Sensors

| Sensor | Description |
|---|---|
| Self-consumption | Total kWh consumed directly from PV |
| Self-consumption rate | Self-consumption / total production |
| Self-sufficiency | Self-consumption / (self-consumption + grid import) |
| Total savings | Avoided electricity costs since commissioning |
| Feed-in revenue | Grid export earnings since commissioning |
| Total yield | Savings + feed-in revenue |
| Net yield | Total yield − installation cost |
| Amortization progress | Total yield as % of installation cost |
| Amortization date | Historical break-even date, or projected future date |
| Days to amortization | Days remaining until break-even |
| Average daily yield | Rolling average EUR/day (basis for projection) |
| System age | Days since commissioning date |
| Yield / Savings / Feed-in today | Period totals for the current day |
| Yield / Savings / Feed-in this week | Period totals for the current ISO week |
| Yield / Savings / Feed-in this month | Period totals for the current month |
| Yield / Savings / Feed-in this year | Period totals for the current year |
| Is amortized | Binary sensor — true when total yield ≥ installation cost |

**Attributes on projection sensors** (`amortization_date`, `days_to_amortization`, `average_daily_yield`): `data_days` shows how many days of statistics the calculation is based on. `amortization_date` also exposes `time_left` (e.g. `"12y 5m 3d"`).

**`total_yield` also exposes `monthly_yields`**: a list of `{"month": "YYYY-MM", "yield": <EUR>}` entries for the last 13 months (including the current incomplete month), ready to use as a data source for graph cards.

Out of scope: surplus management, device control, production forecasting, battery correction.

## Requirements

- Home Assistant 2024.10+
- Energy sensors with long-term statistics (`total_increasing`)

## Installation

1. Add this repository to HACS as a custom repository
2. Install **PV Economics** and restart Home Assistant
3. Add the integration via **Settings → Devices & Services**

## Configuration

Setup is split into five steps:

**Step 1 — Installation costs**

| Field | Description |
|---|---|
| Installation cost | Total cost of the PV system |
| Commissioning date | Date the system was first switched on |
| Tracking start date | Date from which HA statistics are read |

**Step 2 — Pre-tracking totals** *(optional, both default to 0)*

Savings and feed-in revenue earned before the tracking start date. The integration adds all future earnings on top. Leave at 0 if setting up on installation day.

**Steps 3–5** — Energy sensors, feed-in tariff, electricity price (fixed ct/kWh or a dynamic entity).

All settings can be changed after setup via the integration's **Configure** button.

## How it works

```
total_savings   = pre-tracking savings   + HA-tracked savings
feed_in_revenue = pre-tracking feed-in   + HA-tracked feed-in
total_yield     = total_savings + feed_in_revenue
```

Period and projection sensors include a live supplement from 5-minute statistics, so values stay current within the last few minutes rather than waiting for the next full hour to be compiled.

## Example Dashboard

The following Lovelace YAML gives a compact amortization overview. It requires [apexcharts-card](https://github.com/RomRider/apexcharts-card) (available via HACS). Replace `pv_economics` entity IDs with your actual entity IDs if you renamed the integration entry.

```yaml
type: vertical-stack
cards:
  # ── Progress gauge ────────────────────────────────────────────────────────
  - type: gauge
    entity: sensor.pv_economics_amortization_progress
    name: Amortisation
    min: 0
    max: 100
    needle: true
    severity:
      green: 75
      yellow: 40
      red: 0

  # ── Key metrics ───────────────────────────────────────────────────────────
  - type: entities
    entities:
      - entity: sensor.pv_economics_total_yield
        name: Gesamtertrag
      - entity: sensor.pv_economics_net_yield
        name: Nettoertrag
      - entity: sensor.pv_economics_amortization_date
        name: Amortisationsdatum
      - entity: sensor.pv_economics_days_to_amortization
        name: Noch
      - entity: sensor.pv_economics_average_daily_yield
        name: Ø Tagesertrag

  # ── Monthly yield bar chart ───────────────────────────────────────────────
  - type: custom:apexcharts-card
    header:
      show: true
      title: Monatliche Erträge
    chart_type: line
    apex_config:
      xaxis:
        type: datetime
        labels:
          format: MMM yy
    series:
      - entity: sensor.pv_economics_total_yield
        name: Ertrag
        color: var(--energy-solar-color, "#FF9800")
        data_generator: |
          return entity.attributes.monthly_yields.map(m => {
            const [y, mo] = m.month.split('-').map(Number);
            return [new Date(y, mo - 1, 1).getTime(), m.yield];
          });
```

## Development

```bash
uv pip install homeassistant pytest pytest-asyncio
.venv/bin/python -m pytest
.venv/bin/ruff check custom_components/pv_economics/
```

---

*Built with [Claude Code](https://claude.ai/code) and [Codex](https://openai.com/codex).*
