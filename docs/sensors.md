# Sensors

## Overview

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

## Notable attributes

**Projection sensors** (`amortization_date`, `days_to_amortization`, `average_daily_yield`) expose a `data_days` attribute showing how many days of statistics the calculation is based on. `amortization_date` also exposes `time_left` (e.g. `"12y 5m 3d"`).

**`total_yield`** exposes `monthly_yields`: a list of `{"month": "YYYY-MM", "yield": <EUR>}` entries for the last 13 months (including the current incomplete month), ready to use as a data source for graph cards.

## How calculations work

```
total_savings   = pre-tracking savings   + HA-tracked savings
feed_in_revenue = pre-tracking feed-in   + HA-tracked feed-in
total_yield     = total_savings + feed_in_revenue
```

**With a battery:** self-consumption savings are corrected to avoid double-counting. Energy that goes into the battery is subtracted from self-consumption, and the battery's discharge contribution is added back separately:

```
savings = (self_consumption − battery_charge) × price
        + battery_discharge × price
```

Round-trip losses are handled implicitly — discharge energy is always less than charge energy, so the math works out without any explicit efficiency factor.

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
