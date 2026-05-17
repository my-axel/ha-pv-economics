# Configuration

The setup wizard walks through 5 screens (7 with battery storage). All settings can be changed later via the **Configure** button on the integration card.

## Screen 1 — Installation cost

| Field | Description |
|---|---|
| Installation cost | Total system cost in your local currency |
| Commissioning date | Date the system was first switched on |
| Tracking start date | Date from which HA statistics are read (defaults to today) |

**When commissioning date and tracking start date differ:** if HA only has data from a later date than when the system went live, set the commissioning date to the actual installation day and the tracking start date to when your HA data begins. Use Screen 2 to enter what you earned in between.

## Screen 2 — Pre-tracking totals *(optional)*

Savings and feed-in revenue earned before the tracking start date. Both default to 0 — leave them at 0 if you're setting up on the day of installation.

## Screen 3 — Sensors and settings

| Field | Description |
|---|---|
| PV production | Sensor for total energy produced (kWh, `total_increasing`) |
| Grid export | Sensor for energy fed into the grid (kWh, `total_increasing`) |
| Grid import | Sensor for energy drawn from the grid — optional; needed for self-sufficiency |
| Feed-in tariff mode | Fixed ct/kWh value or a dynamic HA sensor |
| Electricity price mode | Fixed ct/kWh value or a dynamic HA sensor |
| Rolling window | Days used for the yield average and projection (default: 365) |
| Has battery | Enable if you have battery storage |

## Screens 4–5 — Battery *(only shown when battery is enabled)*

**Screen 4** — Choose sensor type:

- **Bidirectional power sensor** — a single W or kW sensor that is positive when charging and negative when discharging (or vice versa — you select which direction).
- **Two energy sensors** — separate `total_increasing` kWh sensors for charge and discharge.

**Screen 5** — Select the actual sensor entity (or entities).

Without a battery, these two screens are skipped.

## Screen 5 (or 6) — Feed-in tariff

Enter the fixed tariff in ct/kWh, or select the HA sensor chosen in Screen 3.

!!! note
    Dynamic (entity-based) prices require long-term statistics to be enabled on that sensor. Without statistics the integration falls back to its current state.

## Screen 6 (or 7) — Electricity price

Same as above, for your electricity purchase price.

---

## Options (Configure button)

All fields from setup are editable. The **Configure** flow additionally exposes:

| Field | Description |
|---|---|
| Update interval | How often the coordinator refreshes data (default: 5 min) |
