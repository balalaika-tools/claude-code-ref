# Example pull request descriptions

These are synthesized examples (not from any real repo) of well-written PR descriptions. They exist to calibrate tone, depth, and how to *choose* sections — not to hand you a fill-in-the-blanks template. Do not lift their section names, phrasing, or structure wholesale onto a PR they don't fit. Neither example uses every section; each uses exactly the sections its own change needed, and yours should too, judged fresh each time from the actual diff in front of you.

## Example 1 — a substantial fix, all sections earn their place

This PR touched notification delivery with a genuinely complex root cause, a rejected alternative, and a live verification step. It uses nearly every optional section because the change actually has that much surface area: a `Summary`, a `Why this was needed` with concrete failure modes, a detailed `What changed`, a `Live verification` table comparing two approaches, `Automated tests`, `Operational considerations`, and a `Review checklist`.

```markdown
## Summary

This PR makes push-notification delivery resilient to devices that go offline mid-send, expired tokens, and providers that silently truncate oversized payloads.

The final design does one bounded delivery attempt per device per batch:

1. Look up the device's current token and platform (iOS/Android/web) at send time, not at enqueue time.
2. Split the payload into a small "alert" body and a larger "data" body, so truncation only ever drops the data body, never the user-visible alert text.
3. Validate the provider's per-device response before marking a delivery successful: reject non-2xx responses, `InvalidToken`/`Unregistered` errors, and payloads the provider reports as truncated.
4. Retry once, with backoff, only for transient provider errors — not for invalid tokens.

There is deliberately no minimum-payload-size rule. Short alerts remain valid and are covered by automated tests.

## Why this was needed

Three reported delivery failures exposed different root causes:

- Users who reinstalled the app kept receiving silent failures because the old token was cached at enqueue time, before the new token was registered.
- Android devices on some carriers received the alert with an empty body because the provider truncates payloads over 4KB and previously we packed everything into one field.
- A stale device (token revoked by the OS) returned a 200 from the provider with an `Unregistered` reason code in the response body, which the old code did not inspect.

The previous delivery path:
- resolved the device token once when the notification was enqueued, not when it was sent;
- packed the entire payload, including a base64 thumbnail, into a single field with no size budget;
- treated any 2xx HTTP response as a successful delivery without reading the response body;
- retried every failure indefinitely with no backoff, including permanently invalid tokens.

This allowed a technically successful provider call to silently drop content or spin on undeliverable tokens forever.

## What changed

### Token resolution moved to send time

- Look up the device token immediately before dispatch instead of at enqueue time.
- Drop the notification (and log it) if no token is registered for the device.

### Payload budgeting

- Split into `alert` (title/body, capped at 1KB) and `data` (everything else, capped at 3KB).
- Truncate only the `data` payload when over budget; never truncate `alert`.

### Response-aware validation

- Parse each provider response for per-device reason codes, not just the batch HTTP status.
- Treat `InvalidToken`/`Unregistered`/`Truncated` as terminal failures — no retry, token is unregistered from the device table.
- Retry `Timeout`/`InternalError` once with a 2s backoff.

## Live verification

Ran a staging batch of 50 synthetic devices covering fresh tokens, stale tokens, and oversized payloads.

| Scenario | Before | After |
| --- | --- | --- |
| Reinstalled device (stale token) | Silent failure, no alert | Delivered, alert visible |
| Oversized payload (thumbnail + long body) | Empty alert body | Alert intact, data payload truncated |
| Revoked token | Retried indefinitely | Failed once, token unregistered |

## Automated tests

Focused coverage includes: send-time token resolution, alert/data payload budgeting and truncation boundary, response reason-code parsing for all three platforms, retry-vs-terminal-failure classification, and token unregistration on `Unregistered`.

```text
Focused delivery tests: 22 passed
Full test suite:        184 passed
Lint/format:            passed
```

## Operational considerations

- Send-time token lookup adds one extra read per notification; this is negligible against provider round-trip latency.
- Terminal failures now unregister the device token immediately, so a user who reinstalls will need to re-register once — expected behavior, not a regression.

## Review checklist

- [x] Token is resolved at send time, not enqueue time.
- [x] Alert body is never truncated; only the data payload is.
- [x] Non-2xx and reason-coded failures are not marked successful.
- [x] Invalid/unregistered tokens are not retried indefinitely.
- [x] All unit/integration tests and lint checks pass.
- [x] Live verification completed against all three reported failure scenarios.
```

## Example 2 — a mechanical refactor, small and callout-led

This PR is a large diff but a simple change: pure file moves and renames, no behavior change. It doesn't need a `Why`, a verification table, or a checklist — the one thing a reviewer must not miss is that the diff size is misleading, so it leads with a GitHub `> [!IMPORTANT]` callout instead of burying that fact in prose. Everything else is a compact `Summary`, a `New structure` listing, and a one-line `Verification`.

```markdown
> [!IMPORTANT]
> **No application behavior or pipeline changes are intended in this PR.** This is a code-organization refactor only. The large diff is primarily file moves, module extractions, renames, and the corresponding import/test path updates.

## Summary

- reorganize flat `handlers`, `models`, and `jobs` modules into responsibility-based packages
- split the oversized checkout and inventory handlers into focused services
- isolate the payment-provider client, webhook verification, and one module per event type under `billing/events`
- rename the legacy `cleanup.py` job to `stale_cart_cleanup.py` so it isn't confused with the new `stale_session_cleanup.py`
- update imports, tests, and deployment health-check module paths to match the new layout

## New structure

- `app/handlers/checkout`, `app/handlers/inventory`, `app/handlers/auth`
- `app/billing/events`, `app/billing/providers`, `app/billing/webhooks`
- `app/jobs/cleanup`, `app/jobs/reporting`

Entrypoints remain at `app.web.main` and `app.worker.main`. Job names and API behavior are unchanged.

## Verification

- `212 passed` with the full test suite
- Lint and format checks passed
- all configured pre-commit hooks passed
```

## What makes both of these work

- **The section list is a menu, not a checklist.** Neither PR uses all of `Summary` / `Why` / `What changed` / `Live verification` / `Automated tests` / `Operational considerations` / `Review checklist`. Pick the subset that actually carries information for *this* change; an empty or boilerplate section is worse than no section.
- **`Summary` is the one section that's basically always worth having** — it's the only thing some reviewers will read.
- **Lead with the thing a reviewer could misunderstand.** Example 2's callout exists because a huge file-move diff looks scary at a glance; naming that up front changes how the diff gets read. Reach for `> [!IMPORTANT]` (or `> [!WARNING]`/`> [!NOTE]`) when there's one fact the reviewer must not miss — a deliberate non-goal, a breaking change, a migration step — not as decoration.
- **Concrete detail over adjectives.** "Alert body capped at 1KB, data payload truncated above 3KB" beats "greatly improved delivery." Tables, file paths, and counts are what let a reviewer trust the description instead of re-deriving it from the diff.
- **State what's explicitly *not* included** when it's relevant (Example 1's "no minimum-payload-size rule" callout) — reviewers otherwise wonder if it was forgotten.
