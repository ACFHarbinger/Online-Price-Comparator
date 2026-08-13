# Alerting Roadmap

**Status:** 📋 Planned (v2.3, v2.4) · **Source:** grok research (channels), codex research (thresholds)

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
