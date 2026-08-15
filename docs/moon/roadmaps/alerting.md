# Alerting Roadmap

**Status:** 📋 Planned (v2.3, v2.4, v2.14) · **Source:** grok research (channels), codex research (thresholds); v2.14 from the 2026-08-15 global-scope brainstorm

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
| New all-time low | Current confirmed, non-anomalous price is at least `max(2%, EUR 5)` below the prior all-time low for that listing. |
| Meaningful drop | Current price is at least `10%` **and** `EUR 10` below that listing's 7-day rolling median; requires ≥3 observations in that window. |
| Target price | Current price `<= user_target_price`; notify once on crossing below, not on every refresh. |
| Tiered historical low (v2.14, revised) | Current confirmed price is at/below the minimum of that listing's confirmed, same-[condition](product_matching.md#condition-as-a-first-class-field-v211)-bucket observations over a fixed ladder of lookback windows — **30-day / 90-day / 180-day / 365-day / all-time**. Fires at the *highest* tier reached (an all-time-low implies all the shorter tiers too; notify once, at the strongest claim, not five separate messages). Each tier requires data coverage proportional to its own window (can't claim a "1-year low" off 60 days of history) — reuses and generalizes the existing [30-day-low / ATL badge](dashboard_ux.md#borrowed-ux-ideas-v25-v26) pattern rather than introducing a separate percentile system. Purely descriptive — "the lowest confirmed price seen in the last N days," never a forecast. |

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
