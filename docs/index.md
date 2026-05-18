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

## Quick start

1. Add this repository to HACS as a custom repository
2. Install **PV Economics** and restart Home Assistant
3. Go to **Settings → Devices & Services** and add the integration

See [Installation](installation.md) for manual setup and [Configuration](configuration.md) for a full walkthrough of the setup wizard.

## Example dashboard

A compact amortization overview. Requires [apexcharts-card](https://github.com/RomRider/apexcharts-card) (available via HACS).

```yaml
type: vertical-stack
cards:
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

  - type: custom:apexcharts-card
    header:
      show: true
      title: Monatliche Erträge
    chart_type: bar
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

Replace `pv_economics` in entity IDs if you renamed the integration entry.
