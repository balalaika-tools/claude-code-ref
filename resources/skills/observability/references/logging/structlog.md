# Structured Logging with structlog

Logs are the third signal: metrics detect, traces explain causality, logs carry the local detail. They earn their place only if you can get from a log line to its trace and back.

Logging lives in `core/logging.py`, `observability/logging.py`, or whatever shared logging module the service already has. Extend the existing one — do not add a second logging configuration.

## Trace correlation

Every log emitted inside a span must carry `trace_id` and `span_id`. Without them the log is an isolated sentence with no context.

structlog does not have to route through the stdlib formatter. If stdout or a file agent is the transport, add the trace context in the processor chain:

```python
# observability/logging.py
import sys

import structlog
from opentelemetry import trace
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.trace import format_span_id, format_trace_id

from core.config import get_settings


def add_otel_trace_context(_, __, event_dict):
    context = trace.get_current_span().get_span_context()
    if context.is_valid:
        event_dict["trace_id"] = format_trace_id(context.trace_id)
        event_dict["span_id"] = format_span_id(context.span_id)
    return event_dict


def add_exception_fields(_, __, event_dict):
    """Materialize standard exception fields before format_exc_info consumes it."""
    exc_info = event_dict.get("exc_info")
    if not exc_info:
        return event_dict
    if exc_info is True:
        exc_info = sys.exc_info()
    elif isinstance(exc_info, BaseException):
        exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
    if isinstance(exc_info, tuple) and len(exc_info) == 3 and exc_info[1]:
        exc_type, exc, _ = exc_info
        event_dict.setdefault(
            "exception.type", f"{exc_type.__module__}.{exc_type.__qualname__}"
        )
        event_dict.setdefault("exception.message", str(exc))
    return event_dict


def configure_logging(logger_provider: LoggerProvider | None = None) -> None:
    settings = get_settings()

    processors = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        add_exception_fields,
        structlog.processors.format_exc_info,
    ]
    if logger_provider is not None:
        # OtelEventProcessor is defined below in this same module. It drops
        # named events after export so stdout collection cannot duplicate them.
        processors.append(OtelEventProcessor(logger_provider, "chat-api.events"))
    processors.extend(
        [
            # Must run before the renderer, or the fields never reach the output.
            add_otel_trace_context,
            structlog.processors.JSONRenderer(),
        ]
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            structlog.stdlib.NAME_TO_LEVEL[settings.log_level.lower()]
        ),
        cache_logger_on_first_use=True,
    )


log = structlog.get_logger().bind(**{"service.name": get_settings().otel_service_name})
```

Call `configure_logging(providers.logger_provider)` after
`providers = configure_observability()`. The provider is `None` unless named
OTel events are enabled, so ordinary JSON stdout logging needs no second setup
path.

The output should look like:

```json
{
  "event": "retrieval_completed",
  "level": "info",
  "timestamp": "2026-08-10T09:12:44.113Z",
  "service.name": "chat-api",
  "trace_id": "9f4a1c2b3d4e5f60718293a4b5c6d7e8",
  "span_id": "1a2b3c4d5e6f7081",
  "returned_documents": 5
}
```

`trace_id` is 32 lowercase hex characters, `span_id` is 16. If they are missing entirely, the call happened outside an active span. If they are present but all zeros, the span context is invalid — usually because a background task lost context (see `../tracing/worker_runtime.md`).

Do **not** add `trace_sampled` to application logs when the Collector owns tail sampling. The W3C trace-flags sampled bit records the upstream SDK's head-recording/propagation decision; it does not report the later retention decision made by a tail-sampling Collector. With the explicit `AlwaysOn` application sampler required by `../setup/sdk_bootstrap.md`, that bit is always true even for a trace the Collector ultimately drops, so exposing it as a log field is misleading. Measure effective retention at the Collector/backend as described in `../tracing/production_policy.md`.

For stdlib `logging`, `LoggingInstrumentor().instrument(inject_trace_context=True)` injects `otelTraceID`, `otelSpanID`, `otelTraceSampled`, and `otelServiceName` — not the snake-case keys above. Map the trace ID, span ID, and service name to the desired JSON names in the service's existing formatter. When tail sampling owns retention, deliberately omit `otelTraceSampled` for the reason above. `set_logging_format=True` also calls `logging.basicConfig()` and is the wrong owner when formatting already exists.
On `0.65b0`, that instrumentor also installs an OpenTelemetry export handler by default. If stdout/file collection owns delivery, set `OTEL_PYTHON_LOG_AUTO_INSTRUMENTATION=false`; otherwise the same stdlib record can leave by both paths. Do not activate it for structlog records already handled by the processor above.

## Linked traces and durable workflows

Logs carry **execution correlation**; traces carry **causal topology**. A log
record has one current `trace_id`/`span_id` pair. Parent relationships and
`SpanLink`s belong on spans and are not copied into every log record.

This distinction matters for a DB-backed worker or state machine that starts a
new trace with a link to the transition that scheduled it:

```text
producer trace A
  -> persisted carrier in work row

worker trace B, SpanLink -> A
  -> worker logs use trace_id B and the current worker span_id
```

Never put trace A's ID into the worker log's top-level `trace_id`. That falsely
claims the log was emitted inside trace A and breaks log-to-span navigation.
The automatic trace-context processor must always use the active worker span.

For a workflow that crosses several linked traces, add a stable business
correlation key to the root/transition spans and the small set of logs someone
will query independently:

```json
{
  "event": "workflow_transition_started",
  "service.name": "order-worker",
  "trace_id": "<current-worker-trace-id>",
  "span_id": "<current-worker-span-id>",
  "workflow_run_id": "wf-123",
  "workflow_state": "capture_payment",
  "attempt": 2
}
```

The documented cross-signal mapping is:

```text
span attribute  app.workflow.run.id
log field       workflow_run_id
metric label    never — this value is high-cardinality
```

If the trace backend cannot navigate links, a boundary log such as
`workflow_transition_started` may additionally carry `causal_trace_id`. Keep
it separate from `trace_id` and add it only for a demonstrated query need; do
not copy it to every log. The preferred cross-trace search key remains
`workflow_run_id`.

## Event names

The `event` field names what happened, in past tense or as a state change, and stays stable. Varying values are fields.

```
request_received          job_started            queue_message_received
request_completed         job_completed          queue_message_processed
request_failed            job_failed             queue_message_failed
workflow_transition_started      workflow_transition_completed
workflow_transition_failed
```

Not: `processing`, `done`, `something_failed`, `error`, `here`. An event name you cannot write a query against is not an event name.

The GenAI events — model, tool, agent, retrieval, guardrail — are in `genai.md`.

## Fields

Three are effectively mandatory on operational logs:

```
trace_id      span_id      service.name
```

Then the bounded request context that makes the record findable and groupable:

```
http.route          model               attempt
app.job.type        gen_ai.tool.name    app.outcome
error.type          queue               duration_s
```

And the domain identifiers that let you find *this* record later — this is where high-cardinality values belong, because logs index them and metrics cannot:

```
exception_id      order_id          supplier_id      document_count
workflow_run_id   workflow_state    operation        tenant_id
```

Never log:

```
raw prompts and completions      access tokens, API keys
full request/response bodies     cookies, authorization headers
retrieved document text          personal data without explicit permission
```

An LLM service is where this rule gets broken, and it has its own file: `genai.md` covers what a GenAI service must keep out of its logs, which events are worth emitting, and where the exception record goes when a model call is retried inside an agent.

## Don't mirror the trace into the logs

Logs and traces overlap; duplicating one into the other doubles cost and halves signal.

| Fact                                                                   | Belongs in                               |
| ---------------------------------------------------------------------- | ---------------------------------------- |
| Describes the whole operation (model, duration, token counts, outcome) | span attribute                           |
| A point-in-time occurrence needing its own timestamp and severity      | log record                               |
| Needs to be queryable without opening a trace                          | log record                               |
| Detail of a failure — message, stack trace                            | log record, once, at the owning boundary |

Emitting a log at every step of a traced pipeline recreates the trace in a worse format. Log the operational records someone would actually query on their own.

First-party span events are outside this skill's error contract. The pinned
Trace API still supports them, but the exception-on-span semantic convention is
deprecated and new exception events go to correlated log records
(`../conventions/errors.md`).

## Exception logging

Log once at the owning boundary and route `exc_info` through the shared renderer: full traceback in local/dev/staging, safe authored message and bounded indicators in production. Redact credentials/tokens everywhere; call sites never branch on environment.

```python
try:
    return call_model(model, messages)
except TimeoutError as exc:
    span.set_status(Status(StatusCode.ERROR))
    span.set_attribute("error.type", type(exc).__name__)
    log.error(
        "model_request_failed",
        # Only needed if named OTel events are enabled; see below.
        otel_event_name="app.model.request.failed",
        exc_info=True,  # The central processor applies the safe/full policy.
        **{
            "error.type": type(exc).__name__,
            "gen_ai.request.model": model,
            "gen_ai.provider.name": provider,
            "attempt": attempt,
        },
    )
    raise
```

Logging at every level produces one incident with six stack traces and no way to tell which one is the cause.

### Backend size limits on the traceback attribute

A log backend can cap the size of structured metadata per record — Grafana Loki, for example, rejects a whole line once its structured metadata exceeds `max_structured_metadata_size`. The rendered traceback is unbounded; a deep stack or an `ExceptionGroup` can exceed that cap easily. When it does, the backend does not truncate the field — it drops the **entire record**, so the one owning exception log for the failure disappears along with `trace_id`, `error.type`, and everything else on it.

This is a different failure than the Collector-side deletion `../collector/production.md` warns about: that removes only the stack trace and the record still arrives. Confirm the log backend's per-record limit before shipping full-traceback logging anywhere it applies. Two mitigations, in order of preference:

- Keep the traceback as a bounded attribute and truncate it to a fixed size safely under the backend's cap — never drop the field silently.
- If the backend's log body has no comparable limit, carry the rendered traceback there instead of in `attributes`: pop `event_dict["exception"]` (written by `format_exc_info`) before building the attributes dict, and fold it into `body`. Bounded, searchable fields (`error.type`, `workflow_run_id`, …) stay attributes either way — only the unbounded text moves.

Verify with a synthetic exception whose rendered traceback exceeds the backend's cap and confirm exactly one record still arrives.

## Named OpenTelemetry events (optional)

A correlated JSON log is not automatically an OpenTelemetry **Event**. In the OTel data model an Event is a `LogRecord` whose top-level `event_name` is non-empty — an `event.name` *attribute* is not the same thing and backends may not treat it as one.

Add this only if the project exports the OTel logs signal. If logs go to stdout and a log agent, the correlation above is sufficient.

<!-- complete-python-template -->
```python
from time import time_ns
from typing import Any

import structlog
from opentelemetry._logs import SeverityNumber, get_logger
from opentelemetry.context import get_current
from opentelemetry.sdk._logs import LoggerProvider


class OtelEventProcessor:
    """Turn structlog calls carrying otel_event_name into named OTel events."""

    _severity = {
        "debug": SeverityNumber.DEBUG,
        "info": SeverityNumber.INFO,
        "warning": SeverityNumber.WARN,
        "error": SeverityNumber.ERROR,
        "critical": SeverityNumber.FATAL,
    }

    def __init__(self, provider: LoggerProvider, name: str) -> None:
        self._logger = get_logger(name, logger_provider=provider)

    def __call__(self, _logger, method_name: str, event_dict: dict[str, Any]):
        event_name = event_dict.pop("otel_event_name", None)
        if event_name is None:
            return event_dict

        level = str(event_dict.get("level", method_name)).lower()
        event_name = str(event_name)
        attributes = {
            k: v
            for k, v in event_dict.items()
            if k not in {"event", "level", "timestamp", "exception"}
        }
        if "exception" in event_dict:
            attributes["exception.stacktrace"] = event_dict["exception"]

        # This standard event recommends WARN even when the provider failure
        # ultimately causes an application-owned ERROR event at an outer
        # boundary. The ownership rule prevents emitting both for one escape.
        if event_name == "gen_ai.client.operation.exception":
            severity_number = SeverityNumber.WARN
            severity_text = "WARN"
        else:
            severity_number = self._severity.get(level, SeverityNumber.INFO)
            severity_text = level.upper()

        self._logger.emit(
            timestamp=time_ns(),
            event_name=event_name,
            body=event_dict.get("event"),
            severity_number=severity_number,
            severity_text=severity_text,
            attributes=attributes,
            # This is what attaches trace_id and span_id.
            context=get_current(),
        )

        # The record already entered the OTel pipeline. Dropping it here
        # prevents a log agent from ingesting a second copy from stdout.
        raise structlog.DropEvent
```

The shared provider owner in `../setup/sdk_bootstrap.md` creates and registers
the optional `LoggerProvider`; this module only consumes it. Register the event
processor before the renderer by passing that provider into the configuration
function shown above:

```python
providers = configure_observability()
configure_logging(providers.logger_provider)
```

Do not shut the logger provider down here. `shutdown_observability()` owns it
and stops logging, tracing, and metrics through one idempotent lifecycle.

The `DropEvent` matters: without it, a service whose stdout is also collected sends every named event twice, through two different paths, with two different schemas.

`add_exception_fields` must run before `format_exc_info`: the latter consumes
`exc_info` and leaves only rendered stack text. The earlier processor preserves
the fully qualified `exception.type` and `exception.message` required by the
standard GenAI exception event. Its OTel severity is always `WARN`; an outer
application-owned failure event may still be `ERROR`, subject to the one-record
ownership rule.

Event names must be stable. Model names, request IDs, and user IDs are attributes.

Named events go to a log backend or the Collector's logs pipeline — not to Langfuse, whose OTLP endpoint ingests traces only (`genai.md`).

## Trace sampling does not sample logs

Collector pipelines are signal-specific, and tail sampling operates on traces. If a trace is rejected, its logs still flow:

```
log backend    records with trace_id=abc123
trace backend  no trace abc123
```

These orphan logs are normal. Aligning the two requires a stateful component that buffers logs by trace ID until the sampling decision exists — real custom infrastructure, with memory pressure, log latency, and a temporary store of potentially sensitive data. Only build it against a strict retention requirement.

The practical default is independent, importance-aware retention:

```
traces  keep all failed and slow traces; sample normal traffic
logs    keep WARN/ERROR; sample or drop noisy INFO/DEBUG
```

"Sample or drop" needs a mechanism, and there are three — pick one deliberately:

| Where | How | Cost |
| --- | --- | --- |
| Application | `make_filtering_bound_logger` at the configured level, and a per-event sampler for a known-noisy call site | Cheapest; the record never exists, so it cannot be recovered |
| Collector logs pipeline | a `filter` processor on severity, or a sampling processor if the distribution supports one | Central and changeable without a deploy |
| Log backend | retention rules per severity or stream | Full-fidelity ingest, so you pay for volume you then discard |

Never route a log record through the trace sampler to make this decision. It
operates on assembled traces, and it will drop the log of an operation whose
span was sampled away — which is exactly the record you needed.

And a corollary with teeth here specifically: because a tail policy keeps traces by **span status**, a failure that was logged but left its span `UNSET` is sampled away exactly when you need it — and the orphan log above is all that survives. `log.error(...)` does not set span status; see `../conventions/errors.md`, which owns that rule.

## Verify

- A log emitted inside a span has 32-hex `trace_id` and 16-hex `span_id`.
- The same trace ID appears on the span in the trace backend.
- For a new trace with a link, worker logs carry the worker trace ID, never the
  linked producer trace ID; `workflow_run_id` finds the complete durable run.
- Event names are stable strings, with variable data in fields.
- No prompt, completion, token, cookie, or authorization header appears in any log line — grep a captured log sample for a canary secret to prove it.
- An exception produces exactly one record: full traceback in non-production; safe projection and stable indicators without raw exception text in production.
- If named events are enabled: `event_name` is populated at the top level, and the record appears exactly once.

## Then

- GenAI services: `genai.md`
- final checks: `../verification.md`
