# Alerting Roadmap

**Status:** ✅ v2.4 channels done (2026-08-21) · ✅ v2.3 all three rules done (target-price + all-time-low + meaningful-drop, 2026-08-21; ATL/meaningful-drop same-condition buckets 2026-08-22) · ✅ v2.14 alert logic + per-site tick cadence done (2026-08-21; matching dashboard badge now shipped too) · **Source:** grok research (channels), codex research (thresholds); v2.14 from the 2026-08-15 global-scope brainstorm

The v2.3/v2.4 slice shipped 2026-08-21 the **target-price** rule, the Telegram/
Discord dispatch protocol, the `alert_deliveries` delivery log, and (in the
same round) the **all-time-low** and **meaningful-drop** rules, all keyed on
`price_eur_equivalent` (v2.10). v2.14 added the two configurable
**tiered**/**percentile** historical-low alert modes (within the listing's own
same-`condition` bucket) plus the **per-site refresh cadence**: `pipeline.refresh`
now skips re-querying a site whose own `site_settings.min_refresh_interval_hours`
has not elapsed, independent of the product cadence. The matching dashboard badge
is also shipped (read-only display of the same tier-walk). See `ROADMAP.md` v2.3/v2.14.

## Channels: Telegram bot + Discord webhook

Both, per explicit decision — no single-channel constraint. Rationale from
research: for a solo tool, email is a deliverability/spam-folder tax not worth
paying, and desktop/push/mobile-app channels are overkill. Telegram
(`python-telegram-bot` or a raw `sendMessage` call, one chat with yourself) is
free, instant, and needs no server. A generic Discord webhook is a ~20-line
sibling with no bot setup — a plain `POST` to a webhook URL. Both write through
the same internal alert-dispatch interface so adding a third channel later
(e.g. ntfy.sh) is a small addition, not a redesign.

Alert message content (both channels): product, triggering site, old price →
new price, whether it's a new 30-day low, direct buy link.

## Alert types and default thresholds

| Alert | Default rule |
|---|---|
| New all-time low | Current confirmed, non-anomalous **item sticker** (`price_eur_equivalent` persisted with the observation) is at least `max(2%, EUR 5)` below that listing's prior same-condition sticker ATL. Never computed on landed-cost. |
| Meaningful drop | Current price is at least `10%` **and** `EUR 10` below that listing's 7-day rolling median of **same-condition** EUR stickers; requires ≥3 observations in that window. `unknown` never forms a bucket. |
| Target price | Current price `<= user_target_price`; notify once on crossing below, not on every refresh. |
| Tiered historical low (v2.14) | Current confirmed **item sticker** is at/below the minimum of that listing's confirmed, same-[condition](product_matching.md#condition-as-a-first-class-field-v211)-bucket **sticker** observations (`price_eur_equivalent` snapshotted on the row, using that row's `condition`) over a fixed ladder of lookback windows — **30-day / 90-day / 180-day / 365-day / all-time**. Fires at the *highest* tier reached (an all-time-low implies all the shorter tiers too; notify once, at the strongest claim, not five separate messages). Each tier requires data coverage proportional to its own window. Never uses landed-cost (shipping/VAT edits must not fire a tier). Generalizes the existing [30-day-low / ATL badge](dashboard_ux.md#borrowed-ux-ideas-v25-v26) pattern. Purely descriptive — "the lowest confirmed sticker seen in the last N days," never a forecast. |
| Percentile rarity (v2.14) | Current **item sticker** is at/below a **configurable percentile** (default 5th) of that listing's confirmed, same-condition-bucket sticker observations over a **configurable trailing window** (default 180 days), requiring a minimum sample size scaled to that window. A second, independent mode alongside the tiered rule, not a replacement — see [Two configurable modes](#two-configurable-historical-low-modes-v214) below. Also purely descriptive, also not landed-cost. |

Only `confirmed` (non-anomalous) listings can trigger an alert — `review`/
`rejected`/anomalous observations are ignored (see
[product_matching.md](product_matching.md)).

## Global defaults

- `alert_enabled = true` for explicitly tracked products, `false` for one-off
  ad-hoc searches — alerting is a watchlist feature, not something a casual
  `search` invocation opts you into.
- `alert_cooldown_hours = 72` per product + alert type — without a cooldown,
  a bouncing price around a threshold spams the channel into being muted.
- `minimum_tracking_age_days = 7` before the rolling-average ("meaningful drop")
  rule can fire — not enough history before that to know what "normal" looks
  like. All-time-low and target-price alerts can fire immediately since they
  don't depend on a rolling window.
- The 7-day rolling-median comparison is scoped to the *same listing's* own
  history — a newly-discovered cheaper retailer can trigger the all-time-low
  rule, but shouldn't be mischaracterized as "a 10% drop" (it's a different
  listing, not a price change on an existing one).
- If a target price is set, it overrides the meaningful-drop rule's EUR 10
  absolute floor — the user's explicit number wins.
- Never alert on a price *increase* — Keepa gates increase-watches behind a
  paid tier for a reason; it's not the job of this tool.

## Two configurable historical-low modes (v2.14)

Both modes exist because they answer different real questions, and which one
you want depends on urgency, not correctness:

- **Tiered** answers "is this the best price in a clearly-labeled window?" —
  interpretable, discrete, good when you're time-pressed and 90-day-best is
  genuinely good enough to act on.
- **Percentile** answers "how rare is this, continuously?" — tunable to be as
  strict as you want (e.g. bottom 2% of a full year), good when you can wait
  for a genuinely unusual price and don't want to be notified every time
  something merely beats the last 90 days.

**Configuration** (per `tracked_products` row, extending
[settings_and_config.md](settings_and_config.md#currency-and-fx-normalization)):
`historical_low_alert_mode` enum — `tiered` / `percentile` / `both`. When
`both`, the two fire independently (a price can trigger the percentile rule
without hitting a tier boundary, or vice versa) — they're not merged into one
combined score, since collapsing them would lose exactly the distinction that
makes having both worthwhile. Percentile-specific fields:
`rarity_percentile` (default `5`), `rarity_window_days` (default `180`),
`rarity_min_observations` (scaled to window; e.g. roughly one observation
per ~9 days of window as a floor, tunable).

## Refresh scheduling: per-site cadence via a tick script, not a daemon (v2.14)

Extends v2.2's scheduled refresh with **per-site cadence**, not just the
existing per-product `refresh_interval_hours` — some sites' prices barely
move day-to-day and don't need the same check frequency as a volatile one.

**Design:** add `site_settings.min_refresh_interval_hours` (a site-level
floor, alongside the existing rate-limit/politeness fields in that table).
The effective check interval for a given `(product, site)` pair is
`max(product.refresh_interval_hours, site.min_refresh_interval_hours)` — the
site floor can only slow a check down, never speed one up past what the
product owner asked for, and never below whatever the reliability-hardening
floor already requires (see [scrapers_and_retailers.md](scrapers_and_retailers.md)).

**Architecture: a tick script (cron/systemd-timer), not a persistent
daemon.** Runs on a modest fixed cadence (hourly is enough headroom above
any realistic per-site interval), checks `last_checked_at` per `(product,
site)` pair against its computed interval, and only actually scrapes pairs
that are due. This gets the same user-visible behavior as a daemon (prompt,
per-site-aware refresh) without new long-running-process infrastructure —
consistent with v2.2's original "simple loop/cron entry point, not a new
service" decision, and keeps the tick cadence itself well clear of the
"no sub-15-minute real-time tracking" scope boundary even though most ticks
will no-op for most pairs.

## Dependencies

- Requires [v2.1 tracked-product watchlist](settings_and_config.md) and
  [v2.2 scheduled refresh](settings_and_config.md) to exist first — alerting
  needs something to run on a schedule and compare against.
- Requires [product matching](product_matching.md) (v1.5) to exist first —
  alerting on unconfirmed/mismatched listings would alert on garbage.

## Explicitly not doing

- Alerting on every price tick or on price increases.
- Email as a channel (deferred indefinitely — SMTP + spam-folder debugging
  costs more solo-dev time than the feature is worth for one user).
- Browser push notifications or a dedicated mobile app.
