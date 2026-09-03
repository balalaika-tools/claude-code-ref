# Worker and CLI Startup

Read this file for a generic worker or short-lived CLI process. Scheduled jobs
use the more specific tracing and flush pattern in `../tracing/scheduled_jobs.md`.

Short-lived processes lose telemetry by exiting before the batch processor
flushes:

```python
def main() -> None:
    providers = configure_observability()
    configure_logging(providers.logger_provider)
    try:
        run()
    finally:
        shutdown_observability()
```

For a long-running consumer loop, configure once at startup and shut down on
the termination signal after the in-flight unit finishes. See
`../tracing/worker_runtime.md`.
