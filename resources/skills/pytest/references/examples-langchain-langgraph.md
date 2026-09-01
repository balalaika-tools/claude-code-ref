# LangChain and LangGraph pytest examples

Adapt field names and APIs to the installed versions. Generated checkpoint and
interrupt fields are not stable application contracts unless your wrapper makes
them so.

## Pure router plus compiled graph

Test deterministic route policy directly, then keep a smaller graph test for
wiring. Build a fresh graph and checkpointer per test.

```python
import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.genai.refunds.graph import build_refund_graph, route_after_risk
from tests.support.models import ScriptedRiskModel


@pytest.mark.parametrize(
    ("state", "expected_route"),
    [
        pytest.param({"risk_score": 0.10}, "auto_approve", id="low-risk"),
        pytest.param({"risk_score": 0.91}, "human_review", id="high-risk"),
    ],
)
def test_risk_route(state: dict[str, float], expected_route: str) -> None:
    assert route_after_risk(state) == expected_route


@pytest.fixture
def refund_graph():
    definition = build_refund_graph(model=ScriptedRiskModel(score=0.10))
    return definition.compile(checkpointer=InMemorySaver())


def test_low_risk_refund_reaches_approval(refund_graph) -> None:
    config = {"configurable": {"thread_id": "low-risk-refund-1"}}

    result = refund_graph.invoke(
        {"refund_id": "refund-4", "amount_minor": 500},
        config=config,
    )

    assert result["decision"] == "approved"
    assert result["risk_score"] == pytest.approx(0.10)
```

This does not prove the production model or saver. Test those in explicit
integration or live profiles.

## Interrupt and resume

The exact interrupt result representation is version-sensitive. The invariant
is stable: pause before the effect, resume on the same thread, and never
duplicate effects when the interrupted node restarts from its beginning.

```python
from langgraph.types import Command


def test_approval_resume_charges_once(approval_graph, recording_gateway) -> None:
    config = {"configurable": {"thread_id": "approval-22"}}

    paused = approval_graph.invoke(
        {"operation_id": "op-22", "amount_minor": 2500},
        config=config,
    )

    assert paused["__interrupt__"][0].value == {
        "operation_id": "op-22",
        "amount_minor": 2500,
    }
    assert recording_gateway.charges == []

    finished = approval_graph.invoke(
        Command(resume={"approved": True}),
        config=config,
    )

    assert finished["status"] == "captured"
    assert recording_gateway.charges == [("op-22", 2500)]
```

If code before the interrupt has a side effect, extend the recorder assertion
to prove resume does not repeat it. Add a real production-saver test for restart
and resume rather than inferring durability from `InMemorySaver`.
