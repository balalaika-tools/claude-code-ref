# Worker Process Runtime

Read this file only for a long-running worker loop or when work crosses a
thread, executor, or independently scheduled in-process task. Queue carrier
semantics and durable DB handoffs live in their own references.

## Long-running worker loops

The process loop is lifecycle, not a trace boundary. Never keep one span current
around `while not stopping`: it creates an unbounded trace, gives child work the
wrong parent, and exports nothing until shutdown. Each independently owned
message, job, batch, or retry attempt gets its own bounded root/consumer span
and custom child spans for its meaningful business phases.

Use the transport reference to decide causality. Prompt, synchronous work may
continue the extracted producer trace; delayed, durable, batched, or
independently retried work starts a new trace with a `SpanLink`. A poll/receive,
database claim, or previous loop iteration is never the parent merely because
its context happens to be current. Keep a stable workflow/job ID on spans and
important logs for cross-trace search, never as a metric label.

On the work boundary record bounded job/message type, attempt, outcome, and
queue or workflow identity. Child business spans record the decision, strategy,
result count/category, dependency, and `error.type` actually needed to explain
the phase; do not copy payloads or every available value.

Configure providers once at startup, not per message. Shut down on the termination signal, after the in-flight message finishes:

```python
import signal

stopping = False


def _request_stop(*_):
    global stopping
    stopping = True


def main() -> None:
    # Always this pair, in this order, with the provider passed through — the
    # same call in every entry point (`../setup/startup_worker_cli.md`).
    providers = configure_observability()
    configure_logging(providers.logger_provider)
    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
    try:
        while not stopping:
            for message in receive_messages():
                handle_message(message)
    finally:
        shutdown_observability()
```

## Context loss inside the worker

Context flows through normal calls and is copied by modern
`asyncio.create_task()` and `asyncio.to_thread()`. It is **not** copied by a raw
thread, `ThreadPoolExecutor.submit()`, or `loop.run_in_executor()`. Capture and
attach it only at those non-propagating boundaries; attaching a context that
already flows can create confusing ownership and detach errors. The symptom of
a real loss is a span that should be a child suddenly becoming a root.

```python
from opentelemetry import context


def submit_background_work(executor, payload: dict) -> None:
    current_ctx = context.get_current()
    executor.submit(_run_with_context, current_ctx, payload)


def _run_with_context(parent_ctx, payload: dict) -> None:
    token = context.attach(parent_ctx)
    try:
        with tracer.start_as_current_span("process payload", record_exception=False):
            process(payload)
    finally:
        context.detach(token)
```

Verify that child spans keep the boundary span's trace ID, that shutdown waits
for the in-flight unit of work, and that providers are configured exactly once
per process.

## Then

- the unit-of-work transport: `queue_messaging.md` or `durable_work.md`
- metrics: `../metrics/service.md` — queue depth, oldest-message age, job duration
- logs: `../logging/structlog.md`
- final checks: `../verification.md`
