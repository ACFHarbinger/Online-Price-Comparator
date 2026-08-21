# Price Forecasting Roadmap

**Status:** 📋 Planned (v2.18) · **Source:** direct user request, 2026-08-21 —
un-parks the "Price forecasting" row that `ROADMAP.md`'s Parked table had
twice explicitly rejected as a blended feature (see [Relationship to the
tiered-low badge](#relationship-to-the-tiered-low-badge-and-prior-rejection)
below for why this is a reversal, not a contradiction).

## Why this is separate from every other price-history feature

Every other feature that reads `price_history` in this repo — the trend
chart (v1.4), the anomaly detector (v1.6), the tiered/percentile
historical-low badge (v2.14) — is **descriptive**: it states a fact about
observations that already happened. A forecast is **predictive**: it's a
model's guess about observations that haven't happened yet, with irreducible
uncertainty a descriptive stat doesn't have. Presenting the two with the same
visual confidence would make the tool actively dishonest — exactly the
failure mode this repo's own scope boundaries exist to avoid (see
[ROADMAP.md](../ROADMAP.md#scope-boundaries)).

## v0 design: descriptive trend, not a model (ships first)

Before any actual forecasting model, ship the honest version of "which way is
this going": a **trend/gradient indicator** computed directly from recent
`price_history` — e.g. a short rolling linear-regression slope (7d/30d
windows) over confirmed, non-anomalous, same-condition observations,
labeled as "recent trend: -€3.20/week" or "+1.1%/week", never as a future
price. This is descriptive statistics (same family as the anomaly detector's
IQR), not prediction, and belongs alongside the [statistical price
attributes](dashboard_ux.md#statistical-price-attributes-volatility-trend-2026-08-21)
work in `dashboard_ux.md` — it's listed here only because it's the natural
stepping stone toward v1's actual forecasting model below, not because it's
itself a forecast.

## v1 design: a real forecasting model

- **Model**: start simple — a seasonal-naive or lightweight exponential-
  smoothing model (e.g. Holt's linear trend) over each tracked product's
  confirmed, same-condition, EUR-equivalent `price_history`. Only escalate to
  ARIMA/Prophet-class models if the simple baseline is demonstrably worse on
  held-out history — this repo's matching/anomaly features both shipped the
  simplest statistically-defensible method first ([product_matching.md](product_matching.md)'s
  IQR fence over a learned model), and forecasting should follow the same
  bias.
- **Minimum history gate**: refuse to forecast (show "not enough history
  yet," not a flat line or a silent skip) below a minimum observation count
  and time span — a forecast trained on 3 data points is worse than no
  forecast. Exact thresholds TBD during implementation; document them in the
  UI, not just in code.
- **Output is a range, never a point**: a forecast surfaces a confidence
  band (e.g. 80% interval) for the requested future window, not a single
  number — a single predicted price invites exactly the false-precision
  trust this feature must avoid.
- **Per-condition, per-currency-basis**: same rule as anomaly detection —
  train and predict within one exact `condition` bucket, on the persisted
  `price_eur_equivalent` item sticker (v2.10), never on landed-cost or mixed
  native currencies.
- **Re-trained on refresh, not live**: forecasts update on the same cadence
  as the per-site refresh tick (v2.14's tick script), not recomputed per
  dashboard page load — this is a personal tool, not a trading system.

## UI placement: separate surface, explicit uncertainty

- Lives in its **own panel/tab**, never overlaid on the historical trend
  line or the tiered-low badge — a viewer must not be able to mistake a
  projected band for an observed price. Dashed/hatched styling and an
  explicit "Projected — not a guarantee" label on every render, per
  `dashboard_ux.md`'s aesthetic direction (financial-terminal dark-slate,
  reuse `theme.py` tokens, don't introduce a competing visual language).
- Always shows the confidence band, the model's minimum-history gate status,
  and when it was last retrained — a forecast without its own honesty
  metadata is worse than no forecast.
- Never feeds the tiered/percentile historical-low badge (v2.14), the
  anomaly detector (v1.6), or "best price" ranking — those stay strictly
  observation-based. A forecast is read-only decision *context*, not an
  input to any other feature's math.

## Relationship to the tiered-low badge and prior rejection

`ROADMAP.md`'s Parked table rejected forecasting twice as "prediction
theater" — both times in the context of it potentially being *blended into*
the descriptive tiered-low alert/badge (v2.14), which would have let a
prediction masquerade as a statistical fact. That specific failure mode is
still rejected here: this roadmap's entire UI-placement section above exists
to prevent it. What changed 2026-08-21 is that forecasting is no longer
*only* a parked, unscoped "revisit someday" idea — the user explicitly
requested it as a real, separately-scoped feature (priority 5 of 5 in the
2026-08-21 prioritization, see [ROADMAP.md](../ROADMAP.md#current-priorities-2026-08-21)),
which is exactly the escalation path the original parked note already
anticipated ("noted... as worth investigating **as a separate research
track**").

## Sequencing

Needs real price history to be meaningful at all — this is naturally a
later-milestone feature (v2.18), gated on the historical-low badge/tiered
work (v2.14) shipping first so there's an existing trend-chart surface to
add a separate forecast panel next to, and on v2.10 (FX/landed-cost
semantics) for the same reason anomaly detection needs it: mixed-currency
or landed-cost training data produces a meaningless model.
