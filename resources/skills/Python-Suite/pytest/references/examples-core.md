# Core pytest examples

These examples demonstrate test shape, not project APIs. Adapt module names,
types, and configuration to the repository. Keep only the applicable pattern.

## Application behavior through explicit fakes

Prefer a small fake or recorder to a mock graph when application behavior is the
subject. This example proves application-level duplicate-handling policy, not
database durability or concurrent uniqueness.

```python
from dataclasses import dataclass, field
from decimal import Decimal

from app.application.capture_payment import CapturePayment, PaymentRequest
from app.domain.payments import PaymentStatus


@dataclass
class InMemoryPayments:
    by_operation: dict[str, PaymentStatus] = field(default_factory=dict)

    def status_for(self, operation_id: str) -> PaymentStatus | None:
        return self.by_operation.get(operation_id)

    def save(self, operation_id: str, status: PaymentStatus) -> None:
        self.by_operation[operation_id] = status


@dataclass
class RecordingGateway:
    charges: list[tuple[str, Decimal]] = field(default_factory=list)

    def charge(self, *, idempotency_key: str, amount: Decimal) -> str:
        self.charges.append((idempotency_key, amount))
        return "provider-payment-1"


def test_duplicate_operation_does_not_charge_twice() -> None:
    payments = InMemoryPayments()
    gateway = RecordingGateway()
    capture = CapturePayment(payments=payments, gateway=gateway)
    request = PaymentRequest(operation_id="op-42", amount=Decimal("19.50"))

    first = capture(request)
    replay = capture(request)

    assert first.status is PaymentStatus.CAPTURED
    assert replay.status is PaymentStatus.CAPTURED
    assert gateway.charges == [("op-42", Decimal("19.50"))]
    assert payments.status_for("op-42") is PaymentStatus.CAPTURED
```

Add a separate database concurrency test if the real uniqueness guarantee lives
in a constraint, and a provider contract if remote idempotency must be proved.

## Parameterize meaningful boundaries

Use IDs that explain each equivalence class. Do not mutate parameter objects.

```python
import pytest

from app.application.retry_policy import FailureKind, classify_failure


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        pytest.param(408, FailureKind.RETRYABLE, id="request-timeout"),
        pytest.param(429, FailureKind.RETRYABLE, id="rate-limited"),
        pytest.param(400, FailureKind.PERMANENT, id="invalid-request"),
        pytest.param(401, FailureKind.PERMANENT, id="bad-credentials"),
        pytest.param(500, FailureKind.RETRYABLE, id="provider-error"),
    ],
)
def test_provider_status_retry_classification(
    status_code: int,
    expected: FailureKind,
) -> None:
    assert classify_failure(status_code) is expected
```

If headers, exception types, or context change the policy, split those behaviors
or include the relevant inputs rather than hiding them in a generic fixture.

## Hypothesis round-trip invariant

Use generated data when a property is stronger than a few examples. Constrain
the strategy to the public domain and retain known regressions explicitly.

```python
from hypothesis import example, given, strategies as st

from app.adapters.events import decode_event, encode_event


event_ids = st.text(
    alphabet=st.characters(categories=("L", "N")),
    min_size=1,
    max_size=64,
)


@example(event_id="incident-escaped-unicode-1", payload={"label": "Δ"})
@given(
    event_id=event_ids,
    payload=st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.integers() | st.text(max_size=100) | st.none(),
        max_size=10,
    ),
)
def test_event_encoding_round_trips(event_id: str, payload: dict[str, object]) -> None:
    encoded = encode_event(event_id=event_id, payload=payload)

    assert decode_event(encoded) == {"event_id": event_id, "payload": payload}
```

Keep external I/O out of a high-volume property unless each generated example
has fast, deterministic isolation.

## Pytest configuration baseline

This is a design example, not authorization to change configuration. Preserve
the existing setup and add only options supported by the locked pytest version
when configuration work is explicitly in scope.

```toml
[tool.pytest.ini_options]
addopts = [
  "--strict-config",
  "--strict-markers",
  "--import-mode=importlib",
]
testpaths = ["tests"]
markers = [
  "contract: compatibility surfaces without a live provider",
  "integration: disposable real infrastructure",
  "worker: broker and worker lifecycle required",
  "e2e: whole deployable journey",
  "live: shared or paid external provider; explicit opt-in",
  "destructive_fault: controlled process or infrastructure failure",
]
```

Configure strict xfail behavior using the setting name supported by the locked
pytest version. Register only markers the repository uses, and ensure each
profile has a direct local and CI command. A selected infrastructure profile
must fail instead of silently skipping every intended test.
