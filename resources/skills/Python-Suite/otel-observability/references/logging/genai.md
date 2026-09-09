# Logging a GenAI Service

Sits on top of `structlog.md`, not instead of it. The setup, trace correlation, and named-event mechanics are all there; this file covers only what changes when the service calls a model.

Three things change: what you must never log, which events are worth emitting, and where the exception record belongs when a model call is retried inside an agent.

---

## Content never goes in the logs

`CAPTURE_AI_CONTENT` governs **span** attributes (`../tracing/genai/content_capture.md`). It is not a licence to log the same payload — the log backend has different retention, access control, and redaction than the trace backend, usually weaker, and content that reaches it is outside the switch that was supposed to control it.

```
never in a log record
  prompts, system instructions, completions
  tool call arguments and tool results
  retrieved document text
  embedding inputs
```

`log.info("prompt", prompt=prompt)` is the single most common way an LLM service leaks user content into a backend nobody audited. If prompts must be inspectable, they belong on the span, behind the switch, routed to the backend chosen for them.

Bounded facts about the payload are fine when a successful agent completion was
explicitly selected for audit/business search:

```python
log.info(
    "agent_invocation_completed",
    **{
        "gen_ai.agent.name": agent_name,
        "gen_ai.request.model": model,
        "gen_ai.provider.name": provider,
        "input_message_count": len(messages),
        "output_char_count": len(answer),
        "app.outcome": "success",
    },
)
```

---

## Default GenAI event matrix

`structlog.md` owns request/job/queue events. Apply this matrix after the
generic business-event baseline; “when it occurs” means the event is default
for that control-flow outcome, not that every invocation emits a log.

| Situation | Default logging decision | Event |
| --- | --- | --- |
| Successful model call | **Do not log**; span and metrics already carry latency, usage, and outcome | — |
| Terminal standalone/provider-boundary model failure | One `error` at that owning boundary | `model_request_failed` |
| Model failure that escapes to an HTTP/job/agent owner | **Do not log inside**; emit only the outer application failure record | outer `app.*.failed` event |
| Recovered provider/model retry | One `warning` per failed physical attempt | `model_request_failed`, `app.outcome=retried` |
| Recovered tool retry | One `warning` at the recovery boundary | `tool_execution_failed`, `app.outcome=retried` |
| Model/provider fallback | One `warning` when fallback activates | `model_fallback_activated`, `app.outcome=fallback` |
| Guardrail blocks an operation | Log when it occurs | `guardrail_blocked` |
| Agent reaches its step limit | Log when it occurs | `agent_step_limit_reached` |
| Agent invocation is cancelled | Log when it occurs | `agent_invocation_cancelled` |
| Retrieval returns no usable result | Log when it occurs | `retrieval_empty` |
| Summarization/compaction activates | Log when it occurs | `summarization_triggered` |
| Successful agent or retrieval completion | Conditional: only for audit/business search not answered by traces | `agent_invocation_completed` / `retrieval_completed` |

Event names are stable strings. Model names, tool names, attempts, fallback
source/target, policy, and reason are fields. Never create a success log for
every model/tool/span merely for symmetry.

These are structlog event bodies and remain useful when logs go to stdout. If
the record is exported as a named OpenTelemetry event, a provider-facing model
failure uses the standard `gen_ai.client.operation.exception` event name. An
outer HTTP/job/agent boundary failure is an application event such as
`app.request.failed`. The distinction describes ownership; it is not permission
to emit two exception records for one failure.

---

## Fields

On top of the mandatory `trace_id` / `span_id` / `service.name`:

| Field | Bounded? | Why |
| --- | --- | --- |
| `gen_ai.request.model` | yes | which model this record is about |
| `gen_ai.provider.name` | yes | which provider failed |
| `gen_ai.tool.name` | yes, normalized | which tool failed |
| `gen_ai.agent.name` | yes | which agent, when a service runs several |
| `attempt` | yes | distinguishes a first failure from a fifth |
| `error.type` | yes | groups failures |
| `app.outcome` | yes | `success` / `error` / `timeout` / `blocked` |
| `gen_ai.conversation.id` | **no** | high-cardinality, and that is fine here — logs index it, metrics cannot |
| `session.id`, `user.id` | **no** | same, subject to privacy policy |

The high-cardinality identifiers are the point of a log record: they are how someone finds *this* conversation after a user complains. Keep them off metrics (`../metrics/genai.md`).

---

## One record per failed operation, not one per retry layer

An agent can fail at four depths for a single user request: the model call, the model retry middleware, the tool, and the agent invocation. Logging at each produces one incident with four stack traces and no indication which is the cause.

```
model callback         span: ERROR + error.type          no log
tool middleware        span: ERROR + error.type          no log
agent wrapper          span: ERROR + error.type          no log
HTTP handler           span: ERROR + error.type          log.error(..., exc_info=True)
```

The owning boundary is whichever layer decides the request's outcome — the exception handler, the worker's per-message handler. Everything inside it sets `error.type` and re-raises. Full contract: `../conventions/errors.md`.

The exception to that rule is a failure that is **handled and recovered**: a tool attempt that a retry then fixes, or a model fallback that succeeds. Those never reach the boundary, so the default matrix gives them one record where recovery is decided — at `warning`, with `app.outcome` describing the recovery, and without marking the parent span `ERROR`.

For a recovered model-client attempt exported through the OTel logs signal,
set `otel_event_name="gen_ai.client.operation.exception"`. The shared structlog
pipeline derives the required `exception.type` / `exception.message` from
`exc_info` before rendering the stack and exports this standard event at
`WARN`. For a recovered tool attempt, keep the application-owned event because
the standard client-operation exception event does not describe tool execution.

```python
log.warning(
    "tool_execution_failed",
    otel_event_name="app.gen_ai.tool.failed",
    **{
        "gen_ai.tool.name": tool_name,
        "error.type": type(exc).__name__,
        "attempt": attempt,
        "app.outcome": "retried",
    },
)
```

---

## Langfuse does not ingest the logs signal

Its OTLP endpoint accepts **traces**. Named OpenTelemetry events go to a log backend or the Collector's logs pipeline; prompts and outputs reach Langfuse as span attributes, not as log records.

This is the split that catches people out on a GenAI service: the trace backend, the metrics backend, and the LLM-observability backend are three different destinations with three different content policies (`../tracing/genai/content_capture.md`).

---

## Verify

- No prompt, completion, tool argument, or retrieved document appears in any log line. Put a canary string through the service and grep the captured log output for it.
- A model failure inside an agent produces exactly **one** record at the request boundary, with full or masked detail according to `LOG_FULL_EXCEPTION_TRACE`.
- Named provider-client exception events use `gen_ai.client.operation.exception`; outer application failures use one `app.*` event instead.
- A retried-then-successful tool call produces a `warning` record and leaves the agent span `UNSET`.
- A successful model call emits no routine completion log; a selected successful agent/retrieval business event remains conditional and documented.
- Guardrail, step-limit, cancellation, empty-retrieval, summarization, and fallback canaries emit the matrix event once with bounded fields.
- Records emitted inside a model span carry that span's `trace_id` and `span_id`.
- `gen_ai.conversation.id` appears in logs and in no metric.

---

## Then

- metrics, if not done: `../metrics/genai.md`
- asserting redaction in tests: `../testing.md`
- final checks: `../verification.md`
