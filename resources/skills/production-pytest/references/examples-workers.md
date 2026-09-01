# Worker pytest examples

Adapt these patterns to the installed Celery/RQ or consumer framework. They do
not replace a production-broker and production-pool smoke when those mechanics
are the risk.

## Celery task-adapter retry translation

Keep the business action outside the task. Patch it where the task module looks
it up, then assert only the worker-specific translation. This assumes Celery's
default `retry(..., throw=True)` behavior.

```python
from unittest.mock import patch

import pytest
from celery.exceptions import Retry

from app.application.delivery import TransientDeliveryError
from app.workers.invoice import deliver_invoice_task


def test_transient_delivery_failure_requests_retry() -> None:
    failure = TransientDeliveryError("provider unavailable")

    with (
        patch(
            "app.workers.invoice.deliver_invoice",
            autospec=True,
            side_effect=failure,
        ),
        patch.object(
            deliver_invoice_task,
            "retry",
            side_effect=Retry(),
        ) as retry,
        pytest.raises(Retry),
    ):
        deliver_invoice_task.run("invoice-8")

    retry.assert_called_once()
    assert retry.call_args.kwargs["exc"] is failure
```

Add a terminal-failure case asserting no retry. Test application-owned backoff
calculation as pure policy, and use a real worker test for broker scheduling
instead of sleeping here.

## Bounded worker round trip

This shape applies to Celery's embedded worker fixture when already configured.
It proves more than eager execution but may still differ from the production
broker and pool.

```python
import pytest

from app.workers.events import normalize_event_task


@pytest.mark.worker
def test_event_survives_worker_serialization(celery_worker) -> None:
    result = normalize_event_task.delay(
        {"event_id": "event-17", "amount": "10.20"}
    )

    assert result.get(timeout=10) == {
        "event_id": "event-17",
        "amount_minor": 1020,
    }
```

Use a Docker/process smoke with the real broker, backend, and worker pool for
registration, fork safety, acknowledgements, crash/redelivery, and delivery
semantics that the embedded harness cannot prove.
