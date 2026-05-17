# Configuration

Setup is split into multiple steps in the UI. All settings can be changed afterwards via the integration's **Configure** button.

## Step 1 — Installation costs

| Field | Description |
|---|---|
| Installation cost | Total cost of the PV system |
| Commissioning date | Date the system was first switched on |
| Tracking start date | Date from which HA statistics are read |

## Step 2 — Pre-tracking totals *(optional)*

Savings and feed-in revenue earned before the tracking start date. The integration adds all future earnings on top. Leave at 0 if setting up on installation day.

## Step 3 — Energy sensors

| Field | Description |
|---|---|
| PV production sensor | Total energy produced (kWh, `total_increasing`) |
| Grid export sensor | Energy exported to the grid (kWh, `total_increasing`) |
| Grid import sensor | Energy imported from the grid (kWh, `total_increasing`) |
| Has battery storage | Enable if a battery is installed |

## Steps 4–5 — Battery *(only shown when battery is enabled)*

Choose between two sensor configurations:

- **Bidirectional power sensor** — a single W or kW sensor that goes positive when charging and negative when discharging (or vice versa). Select which direction is positive.
- **Two separate energy sensors** — separate `total_increasing` kWh sensors for charge and discharge energy.

Without a battery these steps are skipped entirely.

## Steps 5–7 — Tariffs

- Feed-in tariff (ct/kWh)
- Electricity price — fixed ct/kWh or a dynamic HA entity
