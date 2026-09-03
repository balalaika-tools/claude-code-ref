---
name: observability
description: "Add, audit, repair, upgrade, or troubleshoot OpenTelemetry tracing, metrics, and structured logging in a Python application, service, or shared internal observability library — FastAPI/HTTP APIs, background workers, queue consumers, DB-backed state machines, scheduled jobs, AWS Lambda functions, LangChain/LangGraph agents, and direct provider-SDK LLM code — including GenAI semantic conventions, token and TTFC capture, trace propagation across queues and durable database handoffs, allowlisted baggage, an OpenTelemetry Collector component, and OTLP-first backend routing. Use whenever the user wants to instrument a service, consolidate reusable telemetry/logging, fix or review existing signals, investigate missing or duplicate signals, or update an observability implementation."
---

# Observability Implementation

You are adding or consolidating OpenTelemetry in software that already works. The code exists; your job is to make its behaviour visible without changing what it does.

This file is a router. It holds the rules that apply to every implementation and tells you which reference files to read. **Do not read the whole `references/` tree.** Load only the files the routing table sends you to — unrelated reference material contaminates the implementation.

---

## Scope

**One service at a time by default.** Instrument exactly the service the user named. In a monorepo, do not touch sibling services merely for symmetry. If shared code must change, say so and keep the change additive so other services keep working unchanged.

**Shared-library exception.** When the user explicitly requests a shared observability package or a cross-service consolidation, inspect every current consumer for compatibility, but extract and migrate one coherent capability and one consumer at a time. The shared package must earn its boundary through stable reuse; it is not permission to redesign unrelated services.

If the user has named neither a service nor an explicit shared-library scope and the repo contains more than one service, ask which one before editing anything.

**Python, and FastAPI for HTTP.** Every code sample here is Python, and the HTTP framework hooks are FastAPI's. The routing, conventions, retention policy, and Collector material are language-neutral — for another runtime use those and skip `setup/`, `tracing/genai/`, and `logging/`, whose code does not transfer.

---

## Step 0 — Which kind of work is this?

The description covers six modes and they do not need the same files. Pick one before loading anything else:

| Mode | Load |
| --- | --- |
| **Add** instrumentation to a service | Step 1 discovery, then the Step 3 routing tables |
| **Audit or review** existing telemetry | `references/conventions/naming.md` + `references/conventions/errors.md`, `references/verification.md`, and the one boundary file matching the service type. Skip discovery's greenfield intake. |
| **Troubleshoot** a specific symptom — missing, duplicated, orphaned, or zero-valued signals | `references/troubleshooting.md` only, then the single file it points at |
| **Upgrade** a package, convention revision, or Collector image | `references/compatibility.md` only, then the files its checklist names |
| **Collector-only** change | `references/collector/*`, plus `references/tracing/production_policy.md` if production retention is involved |
| **Shared observability library** | `references/setup/shared_library.md`, then the setup, logging, testing, and verification files it routes |

Only the first mode runs the whole workflow below. A one-line fix does not need a 23k-token intake, and an audit does not need `setup/`.

---

## Step 1 — Discovery

Read **`references/discovery.md`**. It carries the intake questions, the defaults you may assume without asking, and the decisions you must never guess: the **observability backends**; for a consumer, **how trace context arrives**; and, when deployment or export configuration is in scope, the **export topology**. Production sampling work also needs measured traffic and trace-shape inputs; do not turn example percentages or thresholds into production defaults.

Two questions block work if unanswered:

| Question | Why it blocks |
| --- | --- |
| Which backends receive traces, metrics, and logs? | Exporter and Collector configuration cannot be written without it. Never guess a backend. |
| For a queue consumer, worker, DB-backed state machine, or event-driven Lambda: how is trace context propagated from the producer or previous transition? | The carrier field determines whether the work continues a trace or starts a linked one. |

When deployment manifests or exporter routing are part of the task, one more
question blocks that part of the work: direct OTLP export, a colocated
Collector, a shared gateway Collector, or a combination? Application
instrumentation itself can remain topology-neutral by using a configurable OTLP
endpoint.

Everything else has a documented default or a condition under which to ask.
---

## Step 2 — Rules that apply to every implementation

These hold regardless of service type. They are short on purpose; the reasoning lives in the reference files.

1. **Repository guidance wins.** Read `opentelemetry/` and architecture/02_metrics_design_cheatsheet.md in this repo when present. Where they disagree with an example in a reference file, follow the repo, except for older pull/scrape transport examples: this skill's OTLP-first push contract below is the explicit current policy. Read `references/compatibility.md` before relying on any version-sensitive GenAI, LangChain, Collector, or backend example.
2. **Do not create first-party span events.** At the pinned Python version,
   `span.record_exception()` and `span.add_event()` remain supported Trace APIs;
   the exception-on-span semantic convention is deprecated as OpenTelemetry
   moves exception events to correlated logs. This skill adopts that migration
   as a house contract: pass `record_exception=False`, set a low-cardinality
   `error.type`, and emit the exception through the logging boundary. Full
   contract: `references/conventions/errors.md`. Treat any trace with an `ERROR` span as errored; mark the owning boundary for terminal failures (including failure-driven HITL), but keep expected business HITL non-error so filtering and tail sampling remain correct.
3. **Standard conventions first.** Use an OpenTelemetry semantic attribute when one exists. Use the organisation namespace `app.*` when none does. Never invent a key inside a standard namespace such as `gen_ai.*`.
4. **Span names are low-cardinality.** `chat gpt-5`, `execute_tool order_lookup`, `GET /orders/{order_id}`. Never an ID, prompt, or user value. Dynamic values are attributes.
5. **One owner per boundary.** A request, Lambda invocation, queue message, durable state transition, or model call gets exactly one span from exactly one source. Automatic instrumentation, a framework integration, a gateway, and your own code are all candidates — pick one and disable or skip the others. Two owners means duplicated spans and doubled token and cost analytics.
6. **New environment variables go into the app's existing config object** — `config.py`, `settings.py`, or whatever the service already uses. Never read `os.environ` from instrumentation code scattered through the codebase.
7. **Generic SDK setup and framework-specific instrumentation live in different modules.** A LangChain callback never belongs in the file that builds the `TracerProvider`.
8. **Content capture is off by default.** Prompts, completions, tool arguments, and tool results are captured only when `CAPTURE_AI_CONTENT` is true. Everything else — model, usage, latency, errors — is captured either way. When capture is enabled, preserve the provider/API request boundary: system instructions sent separately from chat history belong only in `gen_ai.system_instructions`; actual history belongs in `gen_ai.input.messages`. Never duplicate the instructions across both attributes. This telemetry split must not alter provider-reported token usage or trigger local re-tokenization; see `references/tracing/genai/content_capture.md` and `references/tracing/genai/token_usage.md`.
   Never infer provider serialization from generic framework names or backend rendering.
   Inspect the locked adapter source/current official docs and protect raw callback and export
   shapes with provider fixtures; see `references/tracing/genai/langchain/provider_compatibility.md`.
   Keep the standard `{role, parts}` attributes as the portable source of truth. When a backend
   needs a different shape for readable rendering, emit a content-gated `app.gen_ai.observation.*`
   presentation value and map it to the vendor namespace only in that backend's Collector branch.
   A presentation projection may omit provider-generated `reasoning` parts only when their
   normalized content is exactly empty; retain every non-empty reasoning or non-text part and
   always preserve the complete canonical envelope.
   Never deform `gen_ai.*` to satisfy one UI.
9. **Exception detail is environment-scoped.** When exception logs may contain sensitive or external content, use one typed logging setting independent of log level: local, dev, and staging emit the full exception traceback for debugging; production emits only a safe authored message, bounded `error.type` and failure/reason code, and trace/span correlation. Credential and token redaction stays active in every environment. Enforce the policy in the shared logging processor, never with scattered environment checks at call sites. Full contract: `references/conventions/errors.md`.
10. **Metrics are not derived from sampled traces.** They are emitted independently, with bounded attributes only.
11. **Instrument boundaries, not functions, and make auto-instrumentation earn its volume.** HTTP request, queue publish/consume, durable work claim/state transition, external call, LLM call, tool call, agent invocation, and business phase. Keep database-query spans only when query-level visibility has demonstrated operational value. If database/ORM spans scale with rows, candidates, flushes, or transactions and overwhelm the business shape, leave them off or make them a diagnostic mode; preserve a few business spans, independent metrics, and correlated structured failure logs without recreating O(N) repository spans or per-query logs. Read `references/setup/high_volume_database_tracing.md`. Not every helper is a boundary.
12. **Durable handoffs carry context.** Queue messages, outbox rows, leased jobs, and persisted state transitions carry an allowlisted W3C trace carrier written atomically with the work. Delayed or retried work normally starts a new trace with a link. Logs keep the current span's `trace_id`/`span_id`; a stable workflow/run ID correlates important logs and linked traces and never labels metrics.
13. **OTLP push is the default.** Applications send traces, metrics, and logs over OTLP to the Collector, which pushes them to their backends.
    Collector self-metrics use a bounded periodic OTLP reader to independent monitoring. Do not add Prometheus pull readers, scrape endpoints, or scrape verification.
    A backend-specific push exporter such as Prometheus remote write is allowed only when the selected backend requires it.
14. **A GenAI backend is a view of the same bounded trace, not a second application trace.**
    For one bounded execution, use one `TracerProvider`, root, and ordinary parentage. The main backend gets the complete operational tree with verbose GenAI payloads removed; the GenAI backend gets the same trace ID as a rooted, ancestor-closed projection containing GenAI spans, the entry root, and meaningful business ancestors.
    Mark projection members with `app.telemetry.category="genai"` and retain every parent to the root. Do not create another provider or detached roots for routing. Rule 12 still governs delayed, durably handed-off, or independently retried work. Full contract: `references/collector/genai_projection.md`.

### Material to load conditionally

- **Baggage.** Assume none is required. Read `references/tracing/baggage.md` only when the user names values that must travel between services — trace context alone already connects the spans.
- **Tests.** If the repository already has a test suite, add focused tests for deterministic telemetry helpers and critical success, error, cancellation, partial-stream, propagation, and duplicate-ownership paths as normal implementation work. The fixtures and assertion helpers are in `references/testing.md`. Follow the repository's conventions. Do not introduce a new test framework solely for observability unless the risk justifies it. Exported-telemetry verification (`references/verification.md`) remains a separate acceptance layer.
- **Symptoms.** If the user reports a symptom rather than requesting work — no spans, duplicate spans, orphan traces, zero token counts — go to `references/troubleshooting.md` first. It routes to one file instead of the whole workflow.

---

## Step 3 — Route to references

Work in this order: **tracing → metrics → logging → collector**. Load a file when you reach the part of the work it covers, not upfront.

The tree mirrors that order. It is a map only — the tables below are the authority on what to load and when. Each signal owns its own GenAI material rather than there being one detached GenAI pile:

```
references/
  discovery.md        the intake questions
  troubleshooting.md  symptom -> cause -> file
  compatibility.md    tested versions + upgrade checks
  conventions/        naming.md + errors.md
  setup/              resource_identity + runtime-specific identity,
                      package_layout, shared_library, sdk_bootstrap + startup variants,
                      auto_instrumentation
  tracing/            production_policy, http_service, async_handoffs, queue_messaging,
                      durable_work, scheduled_jobs, worker_runtime,
                      lambda_functions, baggage
    genai/            attributes, token_usage, content_capture, provider_sdk, retrieval
      langchain/      architecture + the three agent layers
  metrics/            service.md + genai.md
  logging/            structlog.md + genai.md
  collector/          component (including self-telemetry), dev_staging, production
  testing.md          in-memory exporter harness for telemetry assertions
  verification.md     the exported-telemetry checks
  local/              repository-specific mappings; load only on a match
scripts/
  estimate_trace_budget.py   production volume/capacity lower bounds
  validate_skill.py          deterministic checks on this package
```

### Always — the two files every code sample depends on

| File | What it gives you |
| --- | --- |
| `references/conventions/naming.md` | Span, attribute, metric, and log-event naming; the `app.*` registry; the cardinality allow/forbid lists |
| `references/conventions/errors.md` | The no-span-events error contract, `error.type` values, and the closed sentinel set |

Two facts from `references/compatibility.md` apply unconditionally, so they are
here rather than in a file you must open:

- the pinned GenAI convention revision is the one recorded in
  `references/compatibility.md`; never assume a `gen_ai.*` key that is not already used by
  this skill;
- a Langfuse exporter is OTLP/**HTTP** and sends
  `x-langfuse-ingestion-version: "4"`.

Read the rest of `references/compatibility.md` before copying any **version-sensitive**
example — GenAI attributes, LangChain/LangGraph stream shapes, Collector
component schemas, Lambda layers — and before any upgrade.

### Always when creating or changing SDK setup

Skip these three for a repair, audit, or debug task on an already-instrumented
service; they describe decisions that were already made.

| File | What it gives you |
| --- | --- |
| `references/setup/resource_identity.md` | Service namespace/name/version/instance identity contract; runtime identity is routed separately |
| `references/setup/package_layout.md` | Where the observability modules go and how config/env vars are wired |
| `references/setup/auto_instrumentation.md` | Which instrumentation packages to install, which to deliberately leave off |

### Resource identity, by deployment runtime

Load the common identity file above, then only the matching rows. Conditions
compose: a pre-fork service on ECS needs both ECS and multi-process identity.

| Runtime | Add these |
| --- | --- |
| Kubernetes | `references/setup/resource_kubernetes.md` |
| Docker Compose | `references/setup/resource_docker_compose.md` |
| Amazon ECS or Fargate | `references/setup/resource_ecs.md` |
| Multiple telemetry-producing processes in one container | `references/setup/resource_processes.md` |
| AWS Lambda | Identity is included in `references/tracing/lambda_functions.md` |
| Plain local process | `references/setup/resource_processes.md` only when no stable platform identity is available |

### SDK startup, by process shape

| Process shape | Add these |
| --- | --- |
| Code-based or zero-code provider ownership in a normal process | `references/setup/sdk_bootstrap.md` |
| FastAPI | `references/setup/sdk_bootstrap.md`, then `references/setup/startup_fastapi.md` |
| Worker or CLI | `references/setup/sdk_bootstrap.md`, then `references/setup/startup_worker_cli.md` |
| Gunicorn/uWSGI or another pre-fork server | `references/setup/sdk_bootstrap.md`, `references/setup/startup_prefork.md`, and `references/setup/resource_processes.md` |
| AWS Lambda | `references/tracing/lambda_functions.md`; read `references/setup/sdk_bootstrap.md` only for a fully manual provider, not for a managed layer |

### Tracing, by primary execution boundary

| Service type | Add these |
| --- | --- |
| HTTP/API service (FastAPI) | `references/tracing/http_service.md` |
| Long-running background worker process | `references/tracing/worker_runtime.md` |
| Scheduled job or CLI batch | `references/tracing/scheduled_jobs.md` |
| AWS Lambda function | `references/tracing/lambda_functions.md` |
| Root service that must introduce baggage — **only if the user asked** | `references/tracing/baggage.md` |

### Tracing, by production goal

| Situation | Add these |
| --- | --- |
| Production deployment, sampling or filtering policy, telemetry cost/capacity work, release burn-in, or observability rollout | `references/tracing/production_policy.md` |

Load this policy reference before writing a production Collector configuration. It owns the retention decisions and required measurements; `references/collector/production.md` owns their Collector implementation.

### Tracing, by asynchronous handoff

Apply this table independently of the primary boundary. An HTTP endpoint that
publishes SQS work needs both the HTTP and queue producer references.

| Handoff | Add these |
| --- | --- |
| Queue publish or direct queue consumer | `references/tracing/async_handoffs.md`, then `references/tracing/queue_messaging.md`; add `references/tracing/worker_runtime.md` only for a long-running consumer process |
| DB-backed queue, outbox, lease, or durable state transition | `references/tracing/async_handoffs.md`, then `references/tracing/durable_work.md`; add `references/tracing/worker_runtime.md` only for a long-running poller |
| SQS-triggered Lambda | `references/tracing/lambda_functions.md`; add `references/tracing/queue_messaging.md` only if the function also publishes messages |

### Tracing, if the service calls a model

Start at `references/tracing/genai/attributes.md`; it is the entry point for everything else under `tracing/genai/`.

| Situation | Add these |
| --- | --- |
| Any GenAI code | `references/tracing/genai/attributes.md` — span vocabulary, conversation correlation, TTFC taxonomy |
| — recording token counts | `references/tracing/genai/token_usage.md` — the normalized shape and every provider adapter |
| — capturing prompts or payloads | `references/tracing/genai/content_capture.md` |
| Direct provider SDK (OpenAI, Anthropic, Bedrock, Azure, Vertex/Gemini) | `references/tracing/genai/provider_sdk.md` |
| LangChain or LangGraph | `references/tracing/genai/langchain/architecture.md` first; also read `references/tracing/genai/langchain/provider_compatibility.md` for a provider/adapter integration or version change, then only the layers you are building |
| — model spans, TTFC | `references/tracing/genai/langchain/model_callback.md` |
| — tool spans, retry middleware, summarization | `references/tracing/genai/langchain/tools_and_middleware.md` |
| — outer agent span, streaming, conversation correlation | `references/tracing/genai/langchain/streaming_and_agent_span.md` |
| RAG — embedding and retrieval spans, on **either** path | `references/tracing/genai/retrieval.md` |

GenAI tracing code imports `observability/genai_metrics.py` and
`observability/agent_counters.py`, which are specified in
`references/metrics/genai.md`. Create those two modules **before** the tracing
layer that imports them, then come back — otherwise the tracing step cannot run,
and inventing local recorder functions to get past the `ImportError` is the
label drift the shared module exists to prevent.

### Metrics and logging, after tracing works

| File | When |
| --- | --- |
| `references/metrics/service.md` | Every service — request/job/dependency/queue and business metrics |
| `references/metrics/genai.md` | GenAI services — model, tool, and agent instruments on top of the above |
| `references/logging/structlog.md` | Every service |
| `references/logging/genai.md` | GenAI services — content rules, event names, where the exception record goes |

### If a Collector is being deployed

| File | When |
| --- | --- |
| `references/collector/component.md` | Always, for layout, image pinning, backend routing, and Collector self-telemetry; add `references/collector/genai_projection.md` when a GenAI backend needs a noise-reduced view of the same trace |
| `references/collector/dev_staging.md` | Writing the dev/staging configs |
| `references/collector/production.md` | Writing the production config: sampling, redaction, resilience |

### Before reporting the work complete

| File | When |
| --- | --- |
| `references/testing.md` | The repository has a test suite and this work added deterministic parsing, serialization, redaction, streaming, retry, or propagation logic — it holds the in-memory exporter harness those tests need |
| `references/verification.md` | Always, last. The exported-telemetry checks. |

---

## Step 4 — Business telemetry

Generic instrumentation tells you the service is slow. Domain telemetry tells you *what the business was doing* when it was slow. Read the service's business logic and add the small number of attributes, metrics, and log fields that would actually be used in an incident.

Ask of each candidate: does this help debugging, filtering, aggregation, incident investigation, performance analysis, or business monitoring? If not, leave it out. A value being available is not a reason to record it.

Prefer domain words over implementation words: `app.pricing.product_count`, not `processed_items`. Naming rules are in `references/conventions/naming.md`.

---

## What not to do

- Don't instrument more than the requested service.
- Don't add `span.record_exception()` or `span.add_event()` anywhere.
- Don't put a model name, tool name, prompt, user ID, or request ID into a span name.
- Don't put a user ID, session ID, conversation ID, trace ID, or raw payload into a metric attribute.
- Don't enable every available auto-instrumentation package. Noisy low-level instrumentation such as full `botocore` call tracing needs a stated reason.
- Don't capture prompts or tool payloads unconditionally.
- Don't create a second `TracerProvider` when one already exists, and don't mix `opentelemetry-instrument` with in-code provider setup.
- Don't create a span per streamed token.
- Don't hold `start_as_current_span` across a `yield`. A generator shares the consumer's context, so the span stays current after control returns.
- Don't add baggage unless the user asked for it.
- Don't copy example sampling percentages, latency thresholds, trace capacities, cache sizes, or token thresholds into production. Derive them from measured traffic and the retention policy.
- Don't accept a force-sampling signal from an untrusted request, message, or baggage carrier.
- Don't skip focused tests when the repository already has a test suite and the instrumentation adds deterministic parsing, serialization, redaction, streaming, retry, or propagation logic.
- Don't pick a backend for the user.
- Don't report the work done before running `references/verification.md`.
