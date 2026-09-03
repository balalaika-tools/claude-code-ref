# Application and Business Logging

Every application gets a small, intentional event catalogue. `structlog.md`
owns JSON rendering, trace correlation, exception fields, and delivery;
this file decides **what is worth logging**. Read the business code before
choosing events. Framework access logs and generic "entered function" messages
do not satisfy this requirement.

## Default event baseline

Start with the rows matching the application's real boundaries. These are the
default suggestions, not permission to emit a high-volume mirror of the trace.

| Application shape | Default events |
| --- | --- |
| Every process | `application_started`, `application_stopping`; configuration validation failures before telemetry starts go to stderr without secrets |
| HTTP/API | `request_failed`; use framework access logs for routine request completion unless a business outcome must be independently searchable |
| Worker/consumer | `job_started`, `job_completed`, `job_failed`; `queue_message_failed` when message disposition is the fact that matters |
| Scheduled job/CLI | `job_started`, `job_completed`, `job_failed` |
| Durable workflow/state machine | `workflow_transition_started`, `workflow_transition_completed`, `workflow_transition_failed` |
| Any retry/fallback boundary | one `warning` for a recovered failure, including attempt and the bounded recovery outcome |
| Material business change | one past-tense domain event, such as `order_approved`, `payment_declined`, or `exception_resolved` |

For a very hot boundary, sample or omit routine start/completion logs when the
trace and metrics already answer the same question. Never sample terminal
failure logs. Keep a successful business event when it is an audit-relevant
state change, an external side effect, or something operators search without
opening a trace.

## Which business events deserve a record

Log an event when at least one is true:

- a domain state changed or an irreversible/external side effect occurred;
- a bounded business decision changed the path: approved, rejected, routed,
  blocked, deferred, fallback selected;
- work was retried, abandoned, dead-lettered, partially completed, or recovered;
- an operator will search for this occurrence by a business identifier;
- the occurrence needs its own timestamp or severity rather than only a span
  duration and attributes.

Do not log getters, loops, successful helper calls, or each step already visible
as a span. For every proposed event, write the operational question it answers.
If no one can state that question, leave the event out.

## Event schema

Every record emitted inside a span inherits `service.name`, `trace_id`, and
`span_id` from the shared processor. Add only fields that explain or locate the
event:

```text
event identity       stable past-tense event name
business context     bounded operation, workflow/state, decision/reason, outcome
execution context    attempt, duration_s, item/result count, dependency/queue
search context       order_id, workflow_run_id, tenant_id when policy permits
failure context      error.type, stable error/code, exception.stacktrace on owner
```

Use the same bounded vocabulary across spans, metrics, and logs. High-cardinality
IDs can be useful on logs and spans, but never on metrics. Do not place payloads,
credentials, prompts, documents, or personal data in ordinary event fields
without explicit permission.

## Failure ownership

The boundary that decides the operation's final outcome emits exactly one
`error` record with `exc_info=True`. Its shared renderer applies
`LOG_FULL_EXCEPTION_TRACE` and, by default, writes the complete chained
traceback to the dedicated `exception.stacktrace` section. Inner layers set span status/`error.type` and
re-raise; they do not duplicate the log.

A failed attempt that is handled and then recovered may emit one `warning` at
the recovery boundary because it never reaches the outer owner. Include
`app.outcome=retried|fallback|degraded`, the attempt, and the stable error type.
Do not mark the overall span `ERROR` when the operation ultimately succeeds.

## Review checklist

- The event catalogue covers process lifecycle, each real execution boundary,
  terminal failures, recovered retries/fallbacks, and material domain changes.
- Event names are stable and searchable; runtime values are fields.
- Each event answers a named operational or business question.
- Routine logs do not duplicate the trace, and terminal error logs are never
  sampled away.
- Every exception has one owning log with trace correlation and the configured
  `exception.stacktrace` policy.
- A canary test proves secrets and disallowed PII do not reach the log backend.
