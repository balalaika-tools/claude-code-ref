# Service and Business Metrics

Metrics detect fleet-level problems; traces explain individual requests. Neither substitutes for the other, and metrics must be emitted **independently of trace sampling** — a 5% trace sample cannot tell you the real error rate.

Metrics are not optional for a GenAI service either. GenAI metrics (`genai.md`) sit on top of these, not instead of them.

---

## Choose by what the service is responsible for

Do not add every metric on this page. Take the rows that match the service's actual responsibilities.

### HTTP / API service

| Metric | Instrument | Source |
| --- | --- | --- |
| `http.server.request.duration` | Histogram (`s`) | auto-instrumentation |
| `http.server.active_requests` | UpDownCounter | auto-instrumentation |
| `http.client.request.duration` | Histogram (`s`) | auto-instrumentation |
| `db.client.operation.duration` | Histogram (`s`) | auto-instrumentation |

Framework instrumentation emits these already. Check what you get before writing a custom counter that duplicates one — a duplicate with slightly different labels is worse than nothing, because two dashboards will disagree.

Traffic, error rate, and latency percentiles all come from the duration histogram's count, status labels, and buckets. You do not need a separate request counter unless you need a label the standard metric does not carry (an SLO good/bad marker, for instance).

That is also why the worker table below has **both** `app.worker.job.duration`
and `app.worker.jobs`, which looks like the duplication just warned against and
is not: the standard HTTP histogram already carries the outcome through
`http.response.status_code`, while a job has no such standard label. The counter
exists to carry `app.outcome`. If you drop it, you lose the outcome split; if
you add its HTTP equivalent, you gain nothing.

### Worker / queue consumer

| Metric | Instrument | Unit | Detects |
| --- | --- | --- | --- |
| `messaging.client.operation.duration` | Histogram | `s` | publish/consume latency |
| `app.worker.queue.depth` | ObservableGauge | `{message}` | backlog |
| `app.worker.oldest_message.age` | ObservableGauge | `s` | user-visible delay |
| `app.worker.job.duration` | Histogram | `s` | processing time |
| `app.worker.jobs` | Counter | `{job}` | throughput and failure rate, by `app.outcome` |
| `app.worker.retries` | Counter | `{retry}` | retry storms |
| `app.worker.dead_letter` | Counter | `{message}` | messages given up on |

Queue depth alone is misleading — a depth of 1000 is fine if it drains in a second. Pair it with oldest-message age, which is the number that maps to user impact.

### Scheduled job

| Metric | Instrument | Detects |
| --- | --- | --- |
| `app.job.duration` | Histogram (`s`) | runs getting slower |
| `app.job.runs` | Counter, by `app.outcome` | failed runs |
| `app.job.last_success.timestamp` | ObservableGauge | a job that stopped running at all |

The third one matters most: a job that never starts emits no duration and no failure. Only an age-since-last-success can detect it.

### Any service with dependencies

Dependency latency and error rate per downstream, from the client instrumentation's duration histogram. If a dependency is called through a library with no instrumentation, add one histogram with a bounded `server.address` or a logical dependency name.

---

## Instruments and units

| Instrument | For | Not for |
| --- | --- | --- |
| Counter | monotonic totals | latency |
| UpDownCounter | in-flight work | totals |
| Histogram | distributions | a single current value |
| ObservableGauge | current state read at collection time | totals |

Units: `s` for duration (not `ms`), `By` for bytes, `{request}`/`{job}`/`{token}`/`{message}` for counts. Full naming rules in `../conventions/naming.md`.

Histogram buckets must match the domain. The default buckets are tuned for sub-second HTTP calls; a 30-second LLM histogram or a 5-minute job histogram needs explicit bucket boundaries via a `View`, or every value lands in the overflow bucket and p95 becomes a lie. The reusable `View` definitions in `../setup/sdk_bootstrap.md` cover `app.worker.job.duration`, `app.job.duration`, and every standard GenAI duration/fan-out histogram; pass them to `MeterProvider(views=...)` rather than merely declaring a histogram.

---

## Defining instruments

Create them once at module load. Recording is cheap; creating is not.

```python
# observability/metrics.py
from opentelemetry import metrics

meter = metrics.get_meter(__name__)

job_duration = meter.create_histogram(
    "app.worker.job.duration",
    unit="s",
    description="Time to process one job, measured from dequeue to completion.",
)

jobs = meter.create_counter(
    "app.worker.jobs",
    unit="{job}",
    description="Jobs processed, by outcome.",
)

jobs_in_flight = meter.create_up_down_counter(
    "app.worker.jobs.in_flight",
    unit="{job}",
    description="Jobs currently being processed.",
)


def observe_queue_depth(options):
    yield metrics.Observation(
        queue_client.depth("pricing-jobs"), {"messaging.destination.name": "pricing-jobs"}
    )


meter.create_observable_gauge(
    "app.worker.queue.depth",
    callbacks=[observe_queue_depth],
    unit="{message}",
    description="Messages waiting in the queue.",
)
```

Gauge callbacks run on the SDK's collection interval. Keep them fast and failure-tolerant — a callback that calls a slow API blocks metric collection for every metric in the process.

---

## Recording measurements

Use one helper so duration, count, and in-flight always move together and every path is covered.

```python
import time
from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def measure_job(*, queue: str, job_type: str) -> Iterator[None]:
    attributes = {"messaging.destination.name": queue, "app.job.type": job_type}
    jobs_in_flight.add(1, attributes)
    started = time.perf_counter()
    outcome = "success"
    error_type = "_NONE"

    try:
        yield
    except Exception as exc:
        outcome = "error"
        error_type = type(exc).__name__
        raise
    finally:
        final = {**attributes, "app.outcome": outcome, "error.type": error_type}
        jobs.add(1, final)
        job_duration.record(time.perf_counter() - started, final)
        jobs_in_flight.add(-1, attributes)
```

The `finally` is the point. Recording only on success produces an error rate whose denominator excludes errors — a metric that gets quieter exactly as the service gets worse.

`error.type` needs a fixed placeholder on the success path (`_NONE`), or success and failure land in different label sets and cannot be divided against each other.

This applies to **application-owned** instruments only. Standard OpenTelemetry
instruments omit `error.type` on success instead, because the convention says
so and a sentinel would not match what other producers emit. The rule for both
lives in `../conventions/errors.md`, which owns `error.type`.

---

## Cardinality is a hard limit

Every unique attribute combination is a time series. Backends fall over from this, and the failure is expensive and slow to undo. The allowed and forbidden attribute lists are in `../conventions/naming.md`; check them before adding any label.

Two attributes that pass that check by eye and are still wrong:

- **`error.type` from an unwrapped exception.** If the exception message ends up in the class name (some SDKs generate dynamic exception classes), normalize to a known set with an `_OTHER` fallback.
- **`app.tenant.tier` versus `app.tenant.id`.** The tier is a handful of values; the ID is unbounded. Use the tier.

---

## Business metrics

Read the service's business logic and add the small number of metrics that would actually be watched. Examples of the shape:

```
app.exceptions_processed     Counter,   by app.outcome
app.exceptions_resolved      Counter,   by resolution category
app.pricing.updates          Counter
app.pricing.product_count    Histogram, per run
app.retrieval.document_count Histogram, per query
app.queue_items_processed    Counter,   by app.outcome
```

No `.count` on the counters, and `.count`/`.result_count` only where the
measured quantity really is "how many", per `../conventions/naming.md`.

Each one needs a stated purpose before you add it:

- what question does it answer?
- who looks at it?
- what would a bad value mean?
- what is its cardinality budget?

If any of those has no answer, leave it out. Every metric has storage, query, alerting, and cognitive cost.

Business metrics are not a loophole for cardinality. `app.pricing.updates` labelled by `supplier_id` is still one time series per supplier.

---

## Verify

Export once and check the actual output:

Send one canary through the OTLP path and query the metrics backend for its
`service.name` and expected `app.*` instruments. Without a Collector, use an
in-process `ConsoleMetricExporter` with a short export interval; the checks
below apply to either output.

Confirm:

- the metric exists, with the expected unit suffix;
- label values are the bounded ones you intended — no IDs;
- the counter increments on **both** success and failure;
- histogram buckets actually contain your values, rather than everything in `+Inf`;
- long-job histograms expose the intended `1, 5, 10, 30, ... 7200` second boundaries;
- the series count is stable across a load test. Growing series count under steady traffic means a high-cardinality label slipped in.

Backends can rename metrics on ingest. Write alerts against the names the
selected backend actually exposes, not names inferred only from the code.
