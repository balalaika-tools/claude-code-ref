# Package Layout and Configuration

Where the observability code lives, and how its settings reach it.

---

## Follow the project, don't impose a layout

Look at what the service already has and extend it. Two shapes are common and both are fine:

**A small service with an existing `core/` package:**

```
core/
    config.py            <- existing; add the telemetry settings here
    logging.py           <- existing or new; structlog setup
    observability.py     <- new; SDK bootstrap
```

**A service large enough that telemetry deserves a package:**

```
observability/
    __init__.py          <- exports configure_observability / shutdown_observability
    tracing.py           <- Resource, TracerProvider, span processors, propagators
    metrics.py           <- MeterProvider, readers, instrument definitions
    logging.py           <- structlog configuration and trace correlation
    genai_attributes.py  <- GenAI convention constants        }
    genai_usage.py       <- token usage normalization         } GenAI
    genai_content.py     <- message/payload serializers       } services
    genai_metrics.py     <- GenAI instruments and recorders   } only
    agent_counters.py    <- per-invocation fan-out counters   }
```

Pick the second when the service has GenAI instrumentation, more than one boundary type, or business metrics — those three together outgrow a single module quickly.

---

## What belongs in the shared package

Within one service, "shared package" below means its common observability
module. When extracting a workspace library consumed by several deployables,
read `shared_library.md`; it adds the reuse threshold, dependency boundary,
explicit lifecycle, shared-logging contract, and consumer-by-consumer migration
rules.

Only generic, framework-agnostic SDK wiring:

- the `Resource`
- `TracerProvider`, `MeterProvider`, and (if used) `LoggerProvider`
- exporters and span/metric/log processors
- propagator configuration
- SDK initialization and shutdown, or the managed-runtime force-flush lifecycle
- shared helper functions — a `set_usage_attributes()`, a stable cross-service
  outcome enum when one genuinely exists, or a duration-measuring context manager

---

## What must stay out of it

Framework and agent-specific instrumentation. A LangChain callback handler, a `@wrap_tool_call` middleware, or an OpenAI response parser does **not** belong in the module that builds the `TracerProvider`.

Put them next to the code they instrument:

```
observability/
    tracing.py                  generic SDK setup
    metrics.py
    logging.py
    genai_attributes.py         shared constants — no framework imports

agents/
    observability/
        callbacks.py            OTelModelCallback  (imports langchain_core)
        middleware.py           trace_tool_call  (imports langchain.agents.middleware)
        agent_span.py           invoke_agent wrapper
```

Why this split is worth enforcing: the generic module is imported by every entry point in the service, including ones with no LLM code. If it imports `langchain_core`, every worker and CLI job now depends on LangChain, startup slows, and a LangChain upgrade can break a service that never calls a model.

---

## Configuration

**Every environment variable this work introduces goes into the service's existing configuration mechanism** — usually `config.py` or `settings.py`. Instrumentation code reads the settings object, not `os.environ`.

This matters because config objects are where a service already does validation, defaults, type coercion, and documentation. A `os.getenv("CAPTURE_AI_CONTENT")` buried in a callback is untyped, untested, and invisible to anyone reading the config.

Typical addition to a `pydantic-settings` config:

```python
# core/config.py
from functools import lru_cache
from uuid import uuid4

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- existing application settings above ---

    # --- observability ---
    # Required: a reusable skill cannot choose a stable repository-specific
    # service identity. Missing it fails during settings construction.
    otel_service_name: str = Field(alias="OTEL_SERVICE_NAME")
    service_namespace: str = Field(alias="SERVICE_NAMESPACE")
    service_version: str = Field("unknown", alias="SERVICE_VERSION")
    # The platform should override this with the Pod UID, container identity,
    # or ECS task/container identity. UUID v4 is the safe process fallback.
    service_instance_id: str = Field(
        default_factory=lambda: str(uuid4()), alias="SERVICE_INSTANCE_ID"
    )
    environment: str = Field("development", alias="ENVIRONMENT")

    otel_exporter_otlp_endpoint: str = Field(
        "http://localhost:4318", alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    otel_traces_endpoint: str | None = Field(
        None, alias="OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"
    )
    otel_metrics_endpoint: str | None = Field(
        None, alias="OTEL_EXPORTER_OTLP_METRICS_ENDPOINT"
    )
    otel_logs_endpoint: str | None = Field(
        None, alias="OTEL_EXPORTER_OTLP_LOGS_ENDPOINT"
    )
    # Enable only when named OTel log events are exported. Plain JSON stdout
    # logging and trace correlation do not need an OTel LoggerProvider.
    otel_logs_enabled: bool = Field(False, alias="OTEL_LOGS_ENABLED")

    # Batch span processor. Keep these in the application settings object so
    # deployment overrides are validated and visible with the rest of config.
    otel_bsp_max_queue_size: int = Field(2048, alias="OTEL_BSP_MAX_QUEUE_SIZE")
    otel_bsp_max_export_batch_size: int = Field(
        512, alias="OTEL_BSP_MAX_EXPORT_BATCH_SIZE"
    )
    otel_bsp_schedule_delay_millis: int = Field(
        5000, alias="OTEL_BSP_SCHEDULE_DELAY"
    )
    otel_bsp_export_timeout_millis: int = Field(
        30000, alias="OTEL_BSP_EXPORT_TIMEOUT"
    )

    # Periodic metric export. The 15-second interval is an intentional
    # responsiveness trade-off; the OpenTelemetry SDK default is 60 seconds.
    otel_metric_export_interval_millis: int = Field(
        15000, alias="OTEL_METRIC_EXPORT_INTERVAL"
    )
    otel_metric_export_timeout_millis: int = Field(
        30000, alias="OTEL_METRIC_EXPORT_TIMEOUT"
    )

    # Capture prompts, completions, tool arguments, and tool results.
    # Off by default: these carry user content.
    capture_ai_content: bool = Field(False, alias="CAPTURE_AI_CONTENT")

    log_level: str = Field("INFO", alias="LOG_LEVEL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

For a plain-dataclass or `os.environ`-based config, add fields in the same style the file already uses. Match the house pattern; do not introduce `pydantic-settings` into a project that does not use it.

### Variables you will typically add

| Variable | Purpose | Default |
| --- | --- | --- |
| `OTEL_SERVICE_NAME` | Logical service identity. Required. | none — fail loudly |
| `SERVICE_NAMESPACE` | System/application grouping. Required. | none — fail loudly |
| `SERVICE_VERSION` | Immutable build identity; prefer the full Git commit SHA | `unknown` |
| `SERVICE_INSTANCE_ID` | Runtime instance identity; platform-supplied when possible | UUID v4 per process |
| `ENVIRONMENT` | Becomes `deployment.environment.name` | `development` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Base OTLP endpoint | `http://localhost:4318` |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | Per-signal override | derived from base |
| `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` | Per-signal override | derived from base |
| `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT` | Per-signal override for named OTel events | derived from base |
| `OTEL_LOGS_ENABLED` | Build and own an OTel `LoggerProvider` | `false` |
| `OTEL_BSP_MAX_QUEUE_SIZE` | Maximum queued spans waiting for export | `2048` |
| `OTEL_BSP_MAX_EXPORT_BATCH_SIZE` | Maximum spans in one export batch | `512` |
| `OTEL_BSP_SCHEDULE_DELAY` | Delay between scheduled span exports, in milliseconds | `5000` |
| `OTEL_BSP_EXPORT_TIMEOUT` | Span batch export timeout, in milliseconds | `30000` |
| `OTEL_METRIC_EXPORT_INTERVAL` | Interval between metric exports, in milliseconds | `15000` |
| `OTEL_METRIC_EXPORT_TIMEOUT` | Metric export timeout, in milliseconds | `30000` |
| `OTEL_PROPAGATORS` | Set explicitly in deployment; add baggage only when routed by `SKILL.md` | `tracecontext` |
| `CAPTURE_AI_CONTENT` | GenAI content capture switch | `false` |
| `LOG_LEVEL` | structlog level | `INFO` |

Sampling configuration follows the provider owner and the policy selected in
discovery. For a code-owned provider, pass `ALWAYS_ON` directly for Collector
tail sampling; for head sampling, add a validated ratio to the existing settings
object and construct the parent-aware sampler shown in `sdk_bootstrap.md`. Do
not also add `OTEL_TRACES_SAMPLER` variables to a code-owned provider. For
zero-code setup, use `OTEL_TRACES_SAMPLER=always_on` for Collector tail sampling
or `parentbased_traceidratio` plus `OTEL_TRACES_SAMPLER_ARG` for head sampling.

Resolve namespace and version ownership using `resource_identity.md`, then
resolve instance ownership using only the runtime reference selected by
`SKILL.md`. In particular, do not replace the `SERVICE_INSTANCE_ID` fallback
with a pod name, Compose service name, ECS service name, Lambda request ID, or
static replica ordinal.

### The OTLP/HTTP path trap

The base and per-signal endpoint variables behave differently, and this is the most common cause of a `404` with no other symptom:

| Setting | Behaviour |
| --- | --- |
| `OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4318` | treated as a base; `/v1/traces` etc. are appended |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://collector:4318/v1/traces` | used exactly as given |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://collector:4318` | posts to `/`, which is not an OTLP endpoint — `404` |

Never append `/v1/traces` to an OTLP/**gRPC** target; gRPC dials `http://collector:4317` and calls a protobuf method.

---

## Wire it into the deployment

Add the new variables wherever the service's environment is declared — `docker-compose.yaml`, the Helm values file, the task definition, `.env.example`. A settings field with no deployment entry is a field that only works on the author's machine.

Keep credentials out of the application entirely when a Collector is in use: the application knows one internal OTLP endpoint and nothing about Langfuse, Datadog, or Prometheus keys.
