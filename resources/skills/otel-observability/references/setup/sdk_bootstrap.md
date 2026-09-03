# SDK Bootstrap

One module, one owner, one call at startup, one flush at shutdown.

## Contents

- [Provider ownership](#before-writing-anything-does-a-provider-already-exist)
- [Bootstrap module and metric views](#the-bootstrap-module)
- [Common startup and shutdown order](#startup-order)
- [Propagators and sampling](#propagators)
- [Verification and failures](#verifying-the-bootstrap)

---

## Before writing anything: does a provider already exist?

Two ways to configure the SDK, and they must not both be active in one process:

| Style | Who owns the provider |
| --- | --- |
| Code-based | Your startup module builds `TracerProvider`/`MeterProvider` |
| Zero-code (`opentelemetry-instrument ...`) | The launcher builds them from environment variables |

Mixing them yields duplicate spans, a no-op provider, or silently discarded telemetry. Check first:

```bash
grep -rn "set_tracer_provider\|TracerProvider(\|opentelemetry-instrument" \
  --include='*.py' --include='Dockerfile' --include='*.yaml' --include='*.sh' .
```

If the service already launches with `opentelemetry-instrument`, do **not** add `configure_observability()`. Add only what the launcher cannot produce: business spans, custom metrics, and — if you need a custom span processor — register it on the *existing* provider rather than building a second one:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

provider = trace.get_tracer_provider()
# A no-op or API-only provider means the launcher has not run yet. Fail here
# rather than silently attaching a processor to a provider that discards spans.
if not isinstance(provider, TracerProvider):
    raise RuntimeError("OpenTelemetry SDK must be configured before app startup")
provider.add_span_processor(MyCustomSpanProcessor())
```

Most services need no custom processor at all. The one case this skill covers is baggage enrichment, and only when the user asked for baggage — `../tracing/baggage.md` defines that processor.

The rest of this file assumes code-based setup, which is the default for a production service because it gives explicit control over processors, views, and shutdown.

Resolve the static resource values using `resource_identity.md` and the runtime
value using only the platform reference selected by `SKILL.md` before creating
any provider. The resource is immutable after provider construction;
discovering a Pod UID, container ID, ECS task ARN, or process UUID later is too
late.

---

## The bootstrap module

Idempotent, so reloaders, test suites, and worker forks cannot configure providers twice.

```python
# observability/tracing.py
from __future__ import annotations

from dataclasses import dataclass

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import (
    ExplicitBucketHistogramAggregation,
    View,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ALWAYS_ON

from core.config import get_settings


@dataclass(slots=True)
class Providers:
    tracer_provider: TracerProvider
    meter_provider: MeterProvider
    logger_provider: LoggerProvider | None = None


_providers: Providers | None = None


# OpenTelemetry GenAI semantic-convention boundaries, pinned by
# ../compatibility.md. Keep these in the provider module: creating a histogram
# does not configure its aggregation.
GENAI_CLIENT_DURATION_BUCKETS = (
    0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.64,
    1.28, 2.56, 5.12, 10.24, 20.48, 40.96, 81.92,
)
GENAI_TOKEN_BUCKETS = (
    1, 4, 16, 64, 256, 1024, 4096, 16384,
    65536, 262144, 1048576, 4194304, 16777216, 67108864,
)
GENAI_AGENT_DURATION_BUCKETS = (
    0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4,
    12.8, 25.6, 51.2, 102.4, 204.8, 409.6,
)
GENAI_WORKFLOW_DURATION_BUCKETS = (
    1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600, 7200,
)
FAN_OUT_BUCKETS = (1, 2, 4, 8, 16, 32, 64, 128)
LONG_JOB_DURATION_BUCKETS = (
    1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600, 7200,
)


def metric_views() -> list[View]:
    """Explicit histogram boundaries for every long-running instrument."""
    boundaries_by_name = {
        "gen_ai.client.operation.duration": GENAI_CLIENT_DURATION_BUCKETS,
        "gen_ai.client.operation.time_to_first_chunk": (
            GENAI_CLIENT_DURATION_BUCKETS
        ),
        "gen_ai.client.token.usage": GENAI_TOKEN_BUCKETS,
        "app.gen_ai.client.token.cache_read.usage": GENAI_TOKEN_BUCKETS,
        "app.gen_ai.client.token.cache_write.usage": GENAI_TOKEN_BUCKETS,
        "app.gen_ai.client.token.reasoning.usage": GENAI_TOKEN_BUCKETS,
        "gen_ai.execute_tool.duration": GENAI_CLIENT_DURATION_BUCKETS,
        "gen_ai.invoke_agent.duration": GENAI_AGENT_DURATION_BUCKETS,
        "gen_ai.invoke_agent.inference_calls": FAN_OUT_BUCKETS,
        "gen_ai.invoke_agent.tool_calls": FAN_OUT_BUCKETS,
        "gen_ai.invoke_workflow.duration": GENAI_WORKFLOW_DURATION_BUCKETS,
        "app.agent.time_to_first_chunk": GENAI_AGENT_DURATION_BUCKETS,
        "app.worker.job.duration": LONG_JOB_DURATION_BUCKETS,
        "app.job.duration": LONG_JOB_DURATION_BUCKETS,
    }
    return [
        View(
            instrument_name=name,
            aggregation=ExplicitBucketHistogramAggregation(boundaries=boundaries),
        )
        for name, boundaries in boundaries_by_name.items()
    ]


def configure_observability() -> Providers:
    """Build and register the OTel providers. Safe to call more than once."""
    global _providers
    if _providers is not None:
        return _providers

    settings = get_settings()

    resource = Resource.create(
        {
            "service.namespace": settings.service_namespace,
            "service.name": settings.otel_service_name,
            "service.version": settings.service_version,
            "service.instance.id": settings.service_instance_id,
            "deployment.environment.name": settings.environment,
        }
    )

    base = settings.otel_exporter_otlp_endpoint.rstrip("/")
    traces_endpoint = settings.otel_traces_endpoint or f"{base}/v1/traces"
    metrics_endpoint = settings.otel_metrics_endpoint or f"{base}/v1/metrics"
    logs_endpoint = settings.otel_logs_endpoint or f"{base}/v1/logs"

    # This template assumes discovery selected Collector tail sampling. If the
    # selected policy uses head-side dropping, use the sampler documented below.
    tracer_provider = TracerProvider(resource=resource, sampler=ALWAYS_ON)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=traces_endpoint),
            max_queue_size=settings.otel_bsp_max_queue_size,
            max_export_batch_size=settings.otel_bsp_max_export_batch_size,
            schedule_delay_millis=settings.otel_bsp_schedule_delay_millis,
            export_timeout_millis=settings.otel_bsp_export_timeout_millis,
        )
    )
    trace.set_tracer_provider(tracer_provider)

    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[
            PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=metrics_endpoint),
                export_interval_millis=(
                    settings.otel_metric_export_interval_millis
                ),
                export_timeout_millis=(
                    settings.otel_metric_export_timeout_millis
                ),
            )
        ],
        views=metric_views(),
    )
    metrics.set_meter_provider(meter_provider)

    logger_provider: LoggerProvider | None = None
    if settings.otel_logs_enabled:
        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(OTLPLogExporter(endpoint=logs_endpoint))
        )
        set_logger_provider(logger_provider)

    _providers = Providers(
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
        logger_provider=logger_provider,
    )
    return _providers


def shutdown_observability() -> None:
    """Flush and stop the providers. Safe to call more than once."""
    global _providers
    if _providers is None:
        return

    providers, _providers = _providers, None
    try:
        if providers.logger_provider is not None:
            providers.logger_provider.shutdown()
    finally:
        try:
            providers.tracer_provider.shutdown()
        finally:
            providers.meter_provider.shutdown()
```

What each piece does:

| Piece | Role |
| --- | --- |
| `Resource` | Service identity stamped on every span, metric, and log |
| `TracerProvider` | Creates tracers; owns sampling and span export |
| `BatchSpanProcessor` | Buffers and exports spans in batches — never use `SimpleSpanProcessor` in a request path |
| `MeterProvider` + `PeriodicExportingMetricReader` | Aggregates and exports metrics on an interval, independently of traces |
| `View` + `ExplicitBucketHistogramAggregation` | Applies domain-appropriate boundaries instead of unsuitable SDK defaults |
| Optional `LoggerProvider` | Owns named OTel log events when `OTEL_LOGS_ENABLED=true` |
| `shutdown_observability()` | Clears its handles first, so a second call is a no-op |

`service.instance.id` must be unique for the running service instance and
stable for its lifetime. `resource_identity.md` defines the common contract;
the selected runtime reference defines its source. Do not derive it from an
ambiguous gateway Collector or a shared replica name.

### About the batching settings

The `BatchSpanProcessor` values and the metric reader's `export_timeout_millis` use the SDK defaults in the settings example from `package_layout.md`. The metric export interval is the one deliberate deviation: **60 s is the SDK default, while the settings example uses 15 s.**

Keep these values in the service's settings object. Although the SDK can read the `OTEL_BSP_*` and `OTEL_METRIC_EXPORT_*` variables when an argument is omitted, passing an argument changes who owns configuration:

| Written as | Behaviour |
| --- | --- |
| argument omitted | env var wins, SDK default if unset |
| literal passed | the literal wins and the SDK ignores its environment variable |
| settings field passed, as above | the service config validates the environment value and supplies its documented default |

This keeps every deployment override in the same typed configuration path instead of splitting ownership between the application and the SDK. A 60-second metric interval means an alert cannot fire on data younger than a minute, which is usually too slow for a request-rate or error-rate alert. Shortening it costs more export requests and more series churn; leave the documented default at 15 s unless the metrics backend complains, and coordinate it with the Collector batch/export cadence.

Drops from an undersized queue are silent. If spans go missing only under load, this is the first thing to check — and the Collector's `otelcol_receiver_accepted_spans` next to the application's own export count is how you confirm it (`../collector/component.md`).

---

## Startup order

The failure this prevents: a client created before its instrumentation is installed may never produce spans, and never inject propagation headers, with no error anywhere.

```
process starts
  -> configure_observability()
  -> install process-wide client/library instrumentation
  -> create the application object
  -> instrument the application instance
  -> create long-lived clients and start background work
  -> serve traffic
```

Shutdown runs in reverse, and telemetry goes last:

```
stop background work
  -> close clients        (their close() may still finish spans)
  -> shutdown_observability()
```

Shutting the providers down before closing clients silently drops the final spans.

Load the runtime-specific startup file selected by `SKILL.md` after applying
this common order. Conditions compose: FastAPI under Gunicorn needs both the
FastAPI and pre-fork references.

---

## Propagators

Set the propagator explicitly in the deployment so services cannot drift apart
during a migration. Trace context is the default contract:

```bash
export OTEL_PROPAGATORS=tracecontext
```

If discovery approved an allowlisted cross-service baggage value and
`../tracing/baggage.md` was loaded, use `tracecontext,baggage` for the services
that participate. Do not enable baggage merely because the SDK supports it. If
services disagree about trace context propagation, the trace breaks at that
boundary with no error.

---

## Sampling

When discovery selects Collector tail sampling, use **100% head recording with an explicit `AlwaysOn` sampler** in the application, which means no head-side dropping. Head sampling cannot know that a request will fail or be slow, which is exactly the trace you want to keep. Do not omit the sampler from a code-owned `TracerProvider`: omission allows `OTEL_TRACES_SAMPLER` to change the policy implicitly.

The W3C sampled flag carries this upstream recording/propagation decision. It does **not** carry the later keep/drop result from a tail sampler. Under `AlwaysOn` it is true even for traces the Collector eventually drops, so do not publish it as `trace_sampled` in logs or interpret it as effective retention. Use Collector/backend counts to measure retained traces.

If discovery instead selects head sampling, do **not** keep the hardcoded `ALWAYS_ON`. A code-owned provider receives the selected sampler explicitly, with the measured ratio coming from typed settings:

```python
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
tracer_provider = TracerProvider(resource=resource, sampler=ParentBased(root=TraceIdRatioBased(settings.otel_trace_sample_ratio)))
```

For zero-code provider ownership, the equivalent deployment configuration is:

```bash
export OTEL_TRACES_SAMPLER=parentbased_traceidratio
export OTEL_TRACES_SAMPLER_ARG=0.1
```

The ratio above is illustrative, not a default; derive it from `../tracing/production_policy.md`. Keep one configuration owner: code plus typed settings for a code-owned provider, or environment variables for a zero-code provider.

Set sampling-relevant attributes at span *creation* time — a sampler cannot see attributes added later. Token counts are known only after the response, so keeping high-token traces needs tail sampling.

Sampling is never a privacy control. Content capture and redaction must be correct whether or not a trace is sampled.

---

## Verifying the bootstrap

Before writing any instrumentation, prove the pipeline works. Temporarily add a console exporter:

```python
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
```

Start the service and hit it once. You should see a span printed with your `service.name` and a non-zero trace ID. If nothing prints, the provider was configured after the work ran, or the code path never executed. If spans print but the backend is empty, the problem is the endpoint, protocol, or Collector pipeline — not the instrumentation.

Remove the console exporter before committing.

Also export metrics once over OTLP and inspect the histogram boundaries in the
backend: client duration must include `81.92`, agent duration `409.6`, workflow
duration `7200`, and token usage `67108864`. If only generic SDK boundaries
appear, the `views=metric_views()` argument was omitted or the instrument name
no longer matches the view.

---

## Common failures

| Symptom | Cause |
| --- | --- |
| No spans at all | Providers configured after the app served requests; wrong exporter package; unreachable Collector |
| Duplicate spans | Zero-code and code-based setup both active; instrumentor called twice; dev reloader re-imported the app |
| `404` from the Collector | Per-signal endpoint set to a bare `host:port` instead of the full `/v1/traces` path |
| Spans vanish in CLI jobs and serverless | No flush before exit |
| Spans missing in Gunicorn workers | SDK configured in the parent before fork |
| Traces break at one service | That service uses a different propagator set |
