# Core production-testing principles

Use these rules for every pytest task, regardless of framework.

The entrypoint defines risk selection, proof profiles, and the quality gate.
This reference covers the mechanics that keep otherwise valuable tests honest,
isolated, and maintainable. Load the framework or integration reference for
boundary-specific behavior rather than generalizing from a test double.

## Use doubles deliberately

Choose the least magical double that expresses the contract:

- **Stub:** returns a controlled outcome.
- **Fake:** small working implementation, useful for stateful port behavior.
- **Spy or recorder:** captures meaningful interactions for later assertions.
- **Mock:** encodes interaction expectations; reserve it for interaction
  contracts or awkward third-party boundaries.

Prefer an explicit typed fake at an application port. It makes setup readable,
supports state assertions, and survives harmless call rearrangement. A concrete
adapter unit test may replace its direct HTTP, SDK, model, clock, or filesystem
collaborator because that adapter is the subject.

When patching is necessary:

- patch the name where the code under test looks it up, not where the object was
  originally defined;
- use `autospec=True` or `spec_set` when practical so the double cannot accept a
  nonexistent API;
- let missing attributes and environment keys fail instead of silently creating
  them;
- scope and restore every patch through a context manager, fixture, or
  `monkeypatch`;
- do not patch several architectural layers to reach one behavior. That signals
  a missing boundary or a test at the wrong level.

Avoid mocks of the subject, private helpers, SQLAlchemy internals, FastAPI
internals, Celery delivery machinery, or LangGraph runtime internals. Do not
assert calls that merely restate the implementation unless call count, order,
or arguments carry business or protocol meaning.

## Fixtures reveal ownership and cost

Use fixtures for lifecycle and reusable setup, not to conceal the scenario.

- Default to function scope and fresh mutable state.
- Keep a fixture at the narrowest common ancestor of its consumers. Expensive
  database, broker, browser, model, or worker fixtures belong under the profile
  that needs them, not root `conftest.py`.
- Prefer explicit fixture parameters over distant `autouse` behavior. A narrow
  autouse safety guard, such as blocking the public network in unit tests, is a
  justified exception.
- Make each fixture perform one state-changing setup action and pair that action
  with its teardown. Composing small yield fixtures keeps cleanup safe when later
  setup fails.
- Use `yield` for lifecycle resources and restore pre-existing global state in a
  `finally` path.
- Broaden resource startup scope only when per-test mutable state is still
  isolated by unique database/schema, transaction, queue, namespace, tenant,
  directory, or identifier.
- Keep builders, scenario factories, recorders, and fake implementations in
  ordinary importable support modules. Never import `conftest.py`.
- Type fixture returns and test parameters when the repository type-checks tests.

Use a plain local value or builder when the facts are important to reading the
test. Deep fixture graphs that manufacture the entire application make it hard
to see causality and often create accidental shared state.

### Parametrization

Parametrize true equivalence classes or boundary values that share one action
and oracle. Give complex cases meaningful IDs. Split cases whose setup, expected
behavior, or failure explanation differs materially.

Pytest passes parameter objects as-is rather than copying them. Never mutate a
shared mutable parameter across cases; build a fresh object inside the test or
through a factory.

## Make time, randomness, and concurrency observable

- Inject clocks, sleep/backoff functions, ID generators, and random sources into
  application logic where the architecture already permits it.
- Freeze wall time only when injection is impractical. Remember that a frozen
  test-process clock does not advance a broker, worker container, database, or
  provider clock.
- Never coordinate concurrency with `sleep()`. Use events, barriers, task
  groups, channels, database locks, or a poll for a semantic condition. Put a
  defensible timeout around every wait.
- Force the intended interleaving explicitly, then assert from the main test
  thread or task. Join every spawned thread and finish or cancel every task in
  fixture teardown.
- Avoid order dependence and uncontrolled global state even in a serial suite.
  When parallel execution is used or planned, give each worker unique ports,
  queues, broker namespaces, database schemas, paths, IDs, and graph thread IDs.
- Seed ordinary randomness when it is part of a deterministic example. For
  property-based testing, preserve and replay the framework's minimized
  failures rather than replacing exploration with a few random loops.

A rerun plugin may collect evidence, but it is not a repair for a flaky test.
Quarantine only with an owner, narrow condition, deadline or issue, and visible
reporting.

## Async discipline

Inspect the installed async stack before choosing syntax. Do not combine recipes
for AnyIO and pytest-asyncio blindly.

- Pick one owner for each async test. When AnyIO and pytest-asyncio are both
  installed, avoid conflicting auto modes; use explicit markers or the
  repository's strict-mode convention.
- Create loop-bound clients, pools, sessions, and checkpointers inside the loop
  and lifecycle in which they run, never at module import time.
- Align async fixture lifetime with event-loop lifetime. Do not share one
  `AsyncSession` across concurrent tasks.
- Wrap asynchronous completion in a bounded timeout and assert after all
  relevant tasks have joined.
- Test cancellation and cleanup when the production code promises them; do not
  merely cancel and ignore leaked work.

Framework plugin APIs and loop-scope defaults change. Honor locked versions and
current repository configuration rather than adding a global `event_loop`
fixture copied from an old example.

## Property-based and stateful testing

Use Hypothesis when invariants cover an input or operation space better than a
handwritten example:

- parse/serialize and encode/decode round trips;
- normalization idempotence;
- balances, quotas, conservation, and ordering properties;
- schemas with missing, extra, malformed, and boundary values;
- duplicate delivery and retry classification;
- state-machine transitions, deduplication, and outbox sequences.

Keep properties deterministic and give each generated example isolated mutable
state. Compare complex systems with a deliberately simple reference model. Add
important discovered failures as explicit `@example` or named regressions so
they remain part of the permanent contract. Do not suppress health checks,
deadlines, or flaky failures without understanding their cause.

Property-based testing complements named examples; it does not replace a clear
business oracle.

## Coverage, mutation, and test sensitivity

Use line and branch coverage to locate important code with no executed scenario
and to notice that a test command did not run what was expected. Never infer
test quality from the percentage: a test can execute every line and assert the
wrong thing.

If the repository enforces a threshold, preserve it unless asked to change it,
but do not weaken assertions or add valueless tests to satisfy it. Explain
whether uncovered code represents risk, defensive impossibility, generated
code, or a different test profile.

For compact high-risk deterministic logic, targeted mutation testing can reveal
tests that execute code without detecting behavioral changes. Use it as a
diagnostic when the project already supports it or adding it is in scope; review
surviving mutations semantically rather than chasing a mutation score.

## Primary references

- [pytest good integration practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html)
- [pytest fixtures and safe teardown](https://docs.pytest.org/en/stable/how-to/fixtures.html#safe-teardowns)
- [pytest parametrization](https://docs.pytest.org/en/stable/how-to/parametrize.html)
- [pytest monkeypatch guidance](https://docs.pytest.org/en/stable/how-to/monkeypatch.html)
- [pytest assertions and expected exceptions](https://docs.pytest.org/en/stable/how-to/assert.html)
- [pytest flaky-test guidance](https://docs.pytest.org/en/stable/explanation/flaky.html)
- [Python mock patching and autospeccing](https://docs.python.org/3/library/unittest.mock.html#where-to-patch)
- [Hypothesis introduction and useful properties](https://hypothesis.readthedocs.io/en/latest/tutorial/introduction.html)
- [Hypothesis stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html)
- [coverage.py branch coverage](https://coverage.readthedocs.io/en/latest/branch.html)
- [pytest's example of a bug despite full coverage](https://docs.pytest.org/en/stable/explanation/types.html)
- [Test Coverage as a diagnostic, not a quality number](https://martinfowler.com/bliki/TestCoverage.html)
