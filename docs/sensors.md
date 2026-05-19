# Sensors

## Reference

| Sensor | Unit | Description |
|---|---|---|
| Self-consumption | kWh | Energy consumed directly from PV (not from grid) |
| Self-consumption rate | % | Self-consumption ÷ total production |
| Self-sufficiency | % | Self-consumption ÷ (self-consumption + grid import) |
| Total savings | € | Avoided electricity costs since commissioning |
| Feed-in revenue | € | Grid export earnings since commissioning |
| Total yield | € | Savings + feed-in revenue |
| Net yield | € | Total yield − installation cost |
| Amortization progress | % | Total yield as a percentage of installation cost |
| Amortization date | date | Break-even date — historical if already reached, projected otherwise |
| Days to amortization | days | Days remaining until break-even |
| Average daily yield | €/day | Rolling average over the configured window (default: 365 days) |
| System age | days | Days since commissioning date |
| Yield / Savings / Feed-in — today | € | Totals for the current calendar day |
| Yield / Savings / Feed-in — this week | € | Totals for the current ISO week (Mon–Sun) |
| Yield / Savings / Feed-in — this month | € | Totals for the current calendar month |
| Yield / Savings / Feed-in — this year | € | Totals for the current calendar year |
| Monthly performance vs. expected | % | This month's yield vs. seasonal expectation, prorated to days elapsed. Requires 12 complete calendar months of history. |
| Projected yield this year | € | Year-to-date yield plus a seasonal forecast for remaining months. Falls back to a flat daily-average projection when fewer than 12 complete calendar months of history are available. |
| Is amortized | — | Binary sensor, true when total yield ≥ installation cost |

## Sensor attributes

**`total_savings` and `feed_in_revenue`** expose:

| Attribute | Description |
|---|---|
| `from_statistics` | Amount tracked by HA statistics (excludes pre-tracking offset) |
| `historical_offset` | Pre-tracking total entered during setup |
| `statistics_fallback` | `true` when the price/tariff entity has no long-term statistics and the current state is used as a fallback |

**Projection sensors** (`amortization_date`, `days_to_amortization`, `average_daily_yield`) expose a `data_days` attribute — the number of days of statistics the calculation is based on. `amortization_date` additionally exposes `time_left` as a human-readable string (e.g. `"12y 5m 3d"`).

**`total_yield`** exposes:

| Attribute | Description |
|---|---|
| `monthly_yields` | List of `{"month": "YYYY-MM", "yield": <float>}` entries for the last 13 months including the current incomplete month. Use as a data source for bar/line chart cards. |
| `statistics_from` | Date of the first hourly statistics bucket used in calculations |
| `statistics_until` | Date of the last hourly statistics bucket used in calculations |
| `data_hours` | Number of complete hourly buckets used |

## How calculations work

```
total_savings   = pre-tracking savings + HA-tracked savings
feed_in_revenue = pre-tracking feed-in + HA-tracked feed-in
total_yield     = total_savings + feed_in_revenue
```

**With a battery:** battery charge energy is subtracted from self-consumption to avoid double-counting, then discharge energy is added back:

```
savings = (self_consumption − battery_charge) × price
        + battery_discharge × price
```

Round-trip losses are handled implicitly — discharge is always less than charge energy, so the math naturally accounts for losses without an explicit efficiency factor.

**Live data:** period and projection sensors supplement hourly HA statistics with 5-minute live data, so values stay current within the last few minutes rather than waiting for the next hourly bucket.
