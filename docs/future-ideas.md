# Future Ideas

This page collects possible additions to PV Economics after 1.0. Nothing here is committed or scheduled — it's a transparent look at what might come next.

**Scope stays Economics.** No forecasts, no device control, no external cloud dependencies. Every idea here fits the existing coordinator / sensor model.

---

## High value, low effort

These ideas build directly on data the coordinator already computes and would each add a useful sensor or attribute with minimal complexity.

**Year-over-year comparison**
A sensor showing yield this year vs. the same period last year (%). Becomes meaningful from the second year of operation and directly answers the most common user question: "Is my system performing well?"

**Self-consumption value (€/kWh)**
`total_savings ÷ self_consumption_kWh`. Makes it immediately clear why self-consumption is more valuable than grid export — the "aha moment" for new users.

**Current price / tariff as sensors**
When using entity mode for electricity price or feed-in tariff, expose the current ct/kWh value as a sensor. Makes dynamic-tariff setups (Tibber, Awattar, etc.) easier to display on dashboards and simplifies debugging without having to dig into logs.

**Best / worst month attributes on `total_yield`**
Derived from the existing `monthly_yields` attribute. Adds ready-made values like "best month: July 2024 — €187.42" so users don't need custom templates for dashboard highlights.

**Battery round-trip efficiency**
Rolling-window ratio of `sum(discharge) / sum(charge)`. Only shown when battery storage is configured. A metric most battery owners care about but rarely have a clean, ongoing measurement for.

**Annual ROI (%)**
`yearly_yield ÷ installation_cost × 100`. A standard financial metric that's easier to communicate ("7.3% annual return") than an abstract amortization date.

**Yearly performance vs. expected**
Same algorithm as the existing monthly performance sensor, aggregated to the full year. Small addition since the seasonality calculation is already in place.

---

## UX and robustness

**`reconfigure` flow**
Home Assistant's modern UI shows a dedicated "Reconfigure" entry alongside "Configure". Reconfigure is the right place for structural changes like swapping entity IDs, while Options handles tuning like update intervals. The logic is mostly shared with the existing options flow.

**Action: `update_historical_totals`**
A targeted action to adjust the pre-tracking savings and feed-in totals without navigating the full five-step options flow. Useful when an old electricity bill turns up with a more accurate figure.

**Auto-default `commissioning_date` from statistics**
If a user doesn't know their commissioning date during setup, default to the earliest date with data in the PV production entity's long-term statistics. Reduces setup friction for existing installations.

**Repair issues for source entities**
Currently `repairs.py` raises a visible repair issue when price/tariff statistics are missing. The same pattern applied to `pv_production_entity` and `grid_export_entity`: if they lose their long-term statistics or are deleted, the user sees a repair notification instead of silent zeros.

**Attributes on `is_amortized`**
The binary sensor currently has no attributes. Mirroring `time_left`, `amortization_date`, and `progress_pct` onto it would make it self-contained as a single dashboard entity.

---

## Larger additions (only if there's real demand)

These are useful but touch the data model more deeply. Worth doing only if users actually ask for them.

**Multi-instance support**
Today the integration blocks a second config entry. For users with two installations (e.g. home + holiday house) this would be valuable. Requires changing the unique-ID strategy and writing a migration for existing entries.

**Two-rate tariff (peak / off-peak) in fixed mode**
Day/night rates or simple EV charging tariffs. Targeted at users with a classic two-rate electricity meter who don't need (or want) dynamic entity-based pricing. Users with real-time pricing already use entity mode.

**CO₂ savings sensor (opt-in)**
`self_consumption_kWh × gCO₂_per_kWh`, with a configurable default factor (e.g. DE grid mix ~380 g/kWh). Small to implement; the effort is keeping it genuinely opt-in so it doesn't blur the economics focus.

**Multiple investment tranches with dates**
Battery added later, module expansion — today only a single total investment amount is supported. A list of `(amount, date)` tranches would make amortization tracking more honest for upgraded systems. Touches `calculate_amortization_date` and needs documentation.

---

## Deliberately out of scope

- **PV forecasts, degradation tracking, load control** — outside the economics focus
- **CSV / Excel export** — Home Assistant's built-in statistics cards and recorder backups already cover this
- **Gamification** (trees planted, CO₂ offset badges) — not the target audience
- **Loan / interest modelling in net yield** — would turn a lightweight integration into a financial planning app
- **`pv_economics.recalculate` action** — `homeassistant.update_entity` already does this
