# Scheduled Jobs and CLI Batches

Always start a new root trace, one per run. There is no upstream queue or
durable carrier to extract unless the job is separately launched from such a
transport. The primary telemetry risk is flushing before the process exits.

```python
from opentelemetry import trace

from observability.logging import configure_logging
from observability.tracing import configure_observability, shutdown_observability

tracer = trace.get_tracer(__name__)


def main() -> None:
    providers = configure_observability()
    configure_logging(providers.logger_provider)
    try:
        with tracer.start_as_current_span(
            "run nightly-repricing",
            record_exception=False,
            attributes={"app.job.name": "nightly-repricing"},
        ) as span:
            result = run_job()
            span.set_attribute("app.pricing.product_count", result.product_count)
    finally:
        # Without this, the process exits before the batch processor exports.
        shutdown_observability()
```

Every exit path needs the flush, including the error path. A job that crashes
is exactly the run whose trace you need.

Use `app.job.name` and bounded `app.outcome` span attributes. Keep run IDs and
domain record identifiers on spans and logs, never on metrics. Read
`../metrics/service.md` for `app.job.duration` and `../logging/structlog.md` for
`job_started`, `job_completed`, and `job_failed`.
