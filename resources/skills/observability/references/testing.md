# Testing Telemetry

Read this when the repository has a test suite and the work added logic that can
break silently: usage parsing, content serialization, redaction, streaming
bookkeeping, retry counting, or carrier propagation.

This is **not** a substitute for `verification.md`. Tests prove a helper is
correct; verification proves the deployed pipeline actually carries the result.
Both, and in that order.

Do not introduce a new test framework for observability. The fixtures below are
`pytest`; translate them to whatever the repository already uses.

---

## The fixtures

Isolated providers, in-memory exporters, nothing global. `Resource.create({})`
keeps the assertions independent of the service's real identity.

<!-- complete-python-template -->
```python
# tests/conftest.py
from collections.abc import Iterator

import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)


@pytest.fixture
def span_exporter() -> Iterator[InMemorySpanExporter]:
    """A TracerProvider whose spans land in a list.

    SimpleSpanProcessor, not Batch: the test must see the span the moment it
    ends, with no flush and no timing dependency.
    """
    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource.create({}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    yield exporter
    provider.shutdown()


@pytest.fixture
def metric_reader() -> Iterator[InMemoryMetricReader]:
    reader = InMemoryMetricReader()
    provider = MeterProvider(
        resource=Resource.create({}),
        metric_readers=[reader],
        # Pass the same View list production uses, or bucket assertions here
        # will pass while production histograms overflow into +Inf.
        views=[],
    )
    yield reader
    provider.shutdown()
```

Pass the provider into the code under test rather than calling
`trace.set_tracer_provider()`. The global provider can only be set once per
process, so a test that sets it makes every later test depend on ordering. If
the code under test resolves its tracer at import time, that is itself worth
fixing — take the provider or the tracer as a parameter.

---

## Assertion helpers

Three helpers cover most of what is worth asserting.

<!-- complete-python-template -->
```python
# tests/telemetry_assertions.py
from typing import Any


def spans_named(exporter: Any, name: str) -> list[Any]:
    return [s for s in exporter.get_finished_spans() if s.name == name]


def assert_one_span(
    exporter: Any,
    name: str,
    *,
    parent_name: str | None = None,
    linked_to_trace_ids: set[int] | None = None,
    attributes: dict[str, Any] | None = None,
) -> Any:
    """Exactly one span with this name, this parent, and these links."""
    matches = spans_named(exporter, name)
    assert len(matches) == 1, (
        f"expected 1 span named {name!r}, got {len(matches)}: "
        f"{[s.name for s in exporter.get_finished_spans()]}"
    )
    span = matches[0]

    if parent_name is None:
        # A root span. `parent is None` is the only proof; an empty links list
        # is not, and neither is a matching trace_id.
        assert span.parent is None, f"{name} should be a root span"
    else:
        parent = assert_one_span(exporter, parent_name)
        assert span.parent is not None, f"{name} has no parent"
        assert span.parent.span_id == parent.context.span_id, (
            f"{name} is not a child of {parent_name}"
        )
        assert span.context.trace_id == parent.context.trace_id

    if linked_to_trace_ids is not None:
        actual = {link.context.trace_id for link in span.links}
        assert actual == linked_to_trace_ids, (
            f"{name} links {actual} != expected {linked_to_trace_ids}"
        )

    for key, expected in (attributes or {}).items():
        assert span.attributes.get(key) == expected, (
            f"{name}.{key} == {span.attributes.get(key)!r}, expected {expected!r}"
        )
    return span


def assert_no_forbidden_metric_attribute(reader: Any, forbidden: set[str]) -> None:
    """No metric data point carries an unbounded label."""
    found: set[str] = set()
    data = reader.get_metrics_data()
    for resource_metric in getattr(data, "resource_metrics", []):
        for scope_metric in resource_metric.scope_metrics:
            for metric in scope_metric.metrics:
                for point in metric.data.data_points:
                    found |= forbidden & set(point.attributes or {})
    assert not found, f"forbidden metric attributes present: {sorted(found)}"


def assert_no_span_events(exporter: Any) -> None:
    """The error contract: status and attributes, never span events."""
    offenders = [
        (s.name, [e.name for e in s.events])
        for s in exporter.get_finished_spans()
        if s.events
    ]
    assert not offenders, f"span events present: {offenders}"
```

`assert_one_span` reads **exported** spans, which is the point. A span's
in-memory `links` list, or a `Link` object the code holds, proves that the code
constructed something — not that the exported span carries it. `tracing/async_handoffs.md`
and `tracing/durable_work.md` both say this; these fixtures are how you act on it.

---

## What is worth a test

Deterministic logic, not the SDK. Do not test that OpenTelemetry creates spans.

| Test | Catches |
| --- | --- |
| Usage adapter against a recorded provider response | A renamed SDK field, silently zeroing token counts |
| Same adapter with fields missing | Instrumentation raising inside a request |
| Content serializer with batched input, several generations, multimodal parts, tool calls | Merged conversations and dropped finish reasons |
| Capture off | Any payload attribute present at all |
| Capture on, oversized response | Truncation marked rather than unbounded growth |
| Empty stream, error after first chunk, cancelled stream, abandoned generator | Spans that never end, and chunk counts that disagree with capture |
| Carrier extraction from a valid, missing, malformed, and oversized carrier | A bad carrier failing the work, or silently authorizing it |
| Linked-consumer path | `context=None` where `Context()` was meant — asserted as `span.parent is None` plus one link |
| Retry of the same work item | A regenerated carrier breaking the causal link |
| Redaction canary through the serializer | A secret reaching a span attribute |
| GenAI projection membership on a mixed business/GenAI/operational tree | An orphaned model leaf, a missing business ancestor, or DB/HTTP noise selected for Langfuse |
| Both success and failure paths of every recorder | An error rate with a denominator that excludes errors |

---

For GenAI projection classification, test the application-owned marking before
testing Collector routing. Build a realistic mixed tree, for example
`run ingestion -> index document -> invoke_workflow -> embeddings`, with an
unrelated database or HTTP-client sibling. For the spans carrying
`app.telemetry.category="genai"`, assert all of these invariants:

- exactly one marked span is the trace root;
- every marked span with an in-trace parent has a marked parent;
- the workflow, GenAI leaves, and real business ancestors are marked;
- unrelated operational siblings are not marked; and
- structural ancestors do not gain fabricated `gen_ai.operation.name` values.

That unit test proves classification, not destination behavior. An exported-
telemetry acceptance test must still send the mixed trace through the pinned
Collector config and confirm that the main backend/capture has the complete
tree without verbose GenAI payloads, while the GenAI backend/capture has the
same trace ID, unchanged retained span identities, and only the connected
projection. Do not recreate the Collector filter in application test code and
mistake that for an integration test.

---

## Two examples

```python
def test_linked_consumer_starts_new_trace(span_exporter, tracer):
    producer_trace_id = publish_and_return_trace_id(tracer)

    handle_message(message_with_carrier())

    consumer = assert_one_span(
        span_exporter,
        "process pricing-jobs",
        parent_name=None,                                 # a root
        linked_to_trace_ids={producer_trace_id},          # with one link
    )
    assert consumer.context.trace_id != producer_trace_id


def test_duration_recorded_on_the_error_path(metric_reader):
    with pytest.raises(TimeoutError):
        run_failing_operation()

    points = data_points(metric_reader, "app.worker.job.duration")
    assert len(points) == 1
    assert points[0].attributes["app.outcome"] == "error"
    assert points[0].attributes["error.type"] == "TimeoutError"
```

The second one is the test most worth having and least likely to be written: it
is the only thing that stops an error-rate metric from getting quieter as the
service gets worse.

---

## Then

- exported-telemetry acceptance: `verification.md`
- if a test cannot run in this environment, say so explicitly rather than
  claiming the path is covered — `verification.md`, "Report honestly"
