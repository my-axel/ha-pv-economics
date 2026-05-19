# Future Ideas

A loose collection of things that might be interesting to add someday. None of this is planned or scheduled — just ideas worth writing down. If something here matters to you, feel free to open an issue.

The scope will stay **Economics**: no forecasts, no device control, no external cloud services.

---

## Possible additions

**Year-over-year comparison**
A sensor showing yield this year vs. the same period last year (%). Gets interesting from the second year of operation onward.

**Self-consumption value (€/kWh)**
`total_savings ÷ self_consumption_kWh` — makes it tangible why consuming your own solar power is worth more than exporting it.

**Current price / tariff as sensors**
When using entity mode for electricity price or feed-in tariff, expose the current ct/kWh value as a dedicated sensor. Useful for dynamic-tariff setups (Tibber, Awattar, etc.) and makes the live value available on dashboards.

**Best / worst month on `total_yield`**
Ready-made "best month: July 2024 — €187.42" attributes so users don't have to build custom templates for dashboard highlights.

**Battery round-trip efficiency**
Rolling ratio of discharge to charge energy. A metric battery owners care about but rarely have a clean, continuous measurement for.

**Annual ROI (%)**
`yearly_yield ÷ installation_cost × 100`. Sometimes easier to communicate than an amortization date.

**Yearly performance vs. expected**
Same idea as the existing monthly performance sensor, but for the full year.

**`reconfigure` flow**
Home Assistant shows a dedicated "Reconfigure" entry in the UI for structural changes like swapping entity IDs, separate from the Options flow used for tuning settings.

**Action: `update_historical_totals`**
A quick way to adjust pre-tracking savings and feed-in totals without going through the full setup wizard — handy when an old electricity bill turns up.

**Auto-detect `commissioning_date`**
If a user doesn't know their commissioning date, default to the earliest date with data in the PV production sensor's long-term statistics.

**Repair notifications for source entities**
If the configured production or export sensor disappears or loses its long-term statistics, surface that as a visible Home Assistant repair issue rather than silent zeros.

**Attributes on `is_amortized`**
The binary sensor has no attributes today. Adding `time_left`, `amortization_date`, and `progress_pct` to it would make it useful as a standalone dashboard element.

**Multi-instance support**
For users with two separate installations, a second config entry.

**Two-rate tariff (peak / off-peak) in fixed mode**
Day/night rates for users with a classic two-rate meter who don't need real-time pricing.

**Multiple investment tranches with dates**
For systems that were extended later (battery added, more panels) — a list of investments with dates rather than a single total amount.

---

## Deliberately out of scope

- **PV forecasts, degradation tracking, load control** — outside the economics focus
- **CSV / Excel export** — Home Assistant's built-in statistics and recorder already cover this
- **Gamification** (trees planted, offset badges) — not the target audience
- **Loan / interest modelling** — would turn a lightweight integration into a financial planning tool
- **`pv_economics.recalculate` action** — `homeassistant.update_entity` already does this
