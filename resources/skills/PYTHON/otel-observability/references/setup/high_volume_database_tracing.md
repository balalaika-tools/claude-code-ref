# High-Volume Database and ORM Tracing

Read this file when database or ORM spans scale with rows, candidates, sessions, flushes, or
transactions; when database scopes dominate a representative trace; or before replacing database
auto-instrumentation with manual telemetry.

## Decide from exported evidence

Database auto-instrumentation is useful when an operator needs query-level latency, operation names,
connection checkout behavior, or dependency error details. It is not mandatory merely because a
service uses a database. An ORM can turn one bounded business action into hundreds or thousands of
connection and statement spans. Those spans may be true and still be the wrong retained boundary.

Use a representative exported workload:

1. Count spans by instrumentation scope and operation, and relate the count to business cardinality
   such as rows, candidates, sessions, or messages.
2. Check whether database spans obscure the root, phases, external calls, and failures an operator
   actually follows. There is no universal percentage threshold; record the measured shape and the
   operational question.
3. Keep database auto-instrumentation when individual query or checkout latency is a current SLO,
   incident, capacity, or correctness concern. Otherwise, leaving it off is a valid design choice.
4. Check failure coverage before disabling it. A trace that becomes quiet but makes a database error
   anonymous is not an improvement.

Do not describe disabling DB tracing as a database performance optimization. It reduces telemetry
volume, not database round trips. Continue fixing measured N+1 work, transaction churn, and excess
checkouts at their data-access boundaries.

## Preserve the application contract

When database tracing is disabled, preserve the useful application shape instead of reproducing the
physical call graph manually:

- one root per request, job, message, or workflow transition;
- a small number of stable business-phase spans with duration, outcome, bounded counts, and
  `error.type` on failure;
- independent metrics for latency, throughput, backlog, errors, and pool health when those are
  operational requirements;
- one correlated structured exception log at the boundary that owns the failure, carrying the
  bounded phase or step, `trace_id`, `span_id`, low-cardinality error type, and safe traceback;
- no span per repository method, transaction, ORM flush, row, or entity, and no success log per SQL
  statement.

Keep useful automatic boundaries independently. Disabling noisy database instrumentation is not a
reason to remove HTTP server/client, queue, cache, or model instrumentation whose volume and incident
value are appropriate.

Do not leave chatty DB spans enabled and filter them in the Collector when the goal is to reduce
producer/export overhead or make the source trace understandable. Filtering does not undo
instrumentation, processing, or export work and can create incomplete traces. Use filtering only for
a separately verified retention policy.

## Optional diagnostic mode

If future query investigation is likely, prefer a validated, disabled-by-default diagnostic setting
or a temporary deployment configuration over permanent high-volume tracing. The instrumentor still
has one activation owner, activates before the first query, and normally requires a process restart.
Document how to enable it, how operators can see that it is active, and when it must be disabled.

Installing an instrumentation package while leaving it inert is safe only in code-based setup. A
zero-code launcher activates installed entry points unless they are explicitly disabled, so verify
the actual activation model before treating an installed database instrumentor as dormant.

## Verification

- Capture a representative workload and record total spans plus counts by instrumentation scope.
- With database tracing off, confirm trace size does not scale with rows or candidates because of
  repository, transaction, connection, or SQL spans.
- Confirm the intended root and business-phase spans retain duration, bounded outcomes, counts, and
  correct parentage; confirm other approved dependency spans remain unchanged.
- Force an escaping and, where supported, an isolated database failure. The owning business span is
  `ERROR`, and exactly one correlated structured log carries a bounded phase or step, error type, and
  safe traceback.
- Confirm no SQL text, bind values, credentials, database URLs, or raw exception state moved into
  manual spans, metrics, or logs.
- If diagnostic mode exists, enable it before process start and confirm one database instrumentation
  owner returns without changing business outcomes. Disable it and repeat the quiet-shape check.
