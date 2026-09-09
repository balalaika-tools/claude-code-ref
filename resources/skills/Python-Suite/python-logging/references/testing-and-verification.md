# Testing and Verification

Test application-owned processors and event decisions, not the logging library itself. Follow the repository's existing test framework; do not add a new framework solely for logging.

## Focused tests

When a suite exists, cover the changed behavior:

- the same event schema is produced for normal and error paths;
- timestamps, level/severity, event, and service identity are present and correctly typed;
- request/job context appears inside its boundary and is cleared afterward;
- two concurrent boundaries do not leak context into each other;
- valid active trace IDs are added when tracing exists and omitted when absent/invalid;
- reserved fields cannot be overwritten by untrusted context;
- nested canary secrets are redacted before serialization;
- `LOG_FULL_EXCEPTION_TRACE=true` preserves the full chained traceback once;
- `LOG_FULL_EXCEPTION_TRACE=false` removes traceback, raw exception message, and canary PII while preserving classification and correlation;
- an oversized traceback is truncated with an explicit marker and the record survives;
- one escaping exception produces exactly one terminal error record;
- recovered retries/fallbacks produce the intended warning and no terminal error;
- GenAI content canaries never appear in captured logs.

Capture the final serialized record or use the library's in-memory sink. Assertions should inspect parsed fields and value types, not fragile key ordering or the renderer's whitespace.

## Runtime verification

Run representative success, failure, retry, and shutdown paths. Capture emitted output and confirm:

- every line is valid standalone JSON in deployed mode;
- event names are stable and variable values are separate fields;
- level/severity and service identity are correct;
- the intended correlation IDs appear and no stale context leaks;
- exactly one terminal failure record contains the configured exception projection;
- canary credentials, headers, PII, payloads, and GenAI content are absent;
- multiline exception text remains inside one JSON record;
- noisy routine events obey the documented filter/sample rule while failures remain;
- final worker/CLI/serverless shutdown records are flushed.

When delivery configuration is in scope, verify at the real destination: the event is searchable by event name, severity, service, and correlation field; field types survive ingestion; timestamp parsing is correct; size limits do not drop the exception record; and retention/access controls match the data policy. Local stdout proves serialization, not backend delivery.

## Symptom guide

| Symptom | Likely owner to inspect |
| --- | --- |
| Plain text or double-encoded JSON | competing formatter/handler or logging through an already rendered string |
| Duplicate records | propagation plus child handler, two startup configurations, framework and application owning the same event, or two delivery paths |
| Missing context | binding outside the boundary, wrong async/thread context mechanism, or early clearing |
| Context from another request/job | context not cleared in `finally` or unsafe global mutable state |
| Missing traceback | exception info lost before the central exception processor or masking enabled |
| Secret still visible | redaction after serialization, shallow traversal, or leak through exception/URL/object representation |
| Final records missing | buffered/asynchronous handler not flushed within shutdown lifecycle |
| Backend cannot query a field | type/schema changed during ingestion, field nested unexpectedly, or backend indexing policy |

## Report honestly

State exactly which tests and runtime paths ran, which sink was inspected, and what could not be verified. Do not describe delivery as complete when only local serialization was tested.
