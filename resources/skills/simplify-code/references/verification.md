# Verification contract

## Verification ladder

Run the narrowest reliable checks first and broaden with the change surface:

1. Parse/import and configured format/lint checks for touched files.
2. Tests that exercise the changed behavior.
3. Configured type checks for the affected package.
4. Integration or repository tests for cross-module changes.
5. Final diff inspection for API, exception, serialization, dependency, test, and behavior drift.

Record exact commands and outcomes. Distinguish pre-existing failures by running an appropriate baseline before edits when practical. A skipped or unavailable check is a coverage gap, not a pass.

## Behavior checklist

For every proposed batch, name which of these apply:

- Public signatures, import paths, entry points, and CLI behavior.
- Values, types, mutation, identity, ordering, and determinism.
- I/O, logs, metrics, tracing, and other side effects.
- Exception types, messages, chaining, and timing.
- Serialization, schemas, aliases, defaults, and wire/storage formats.
- Transaction boundaries, commits, retries, idempotency, and cleanup.
- Async scheduling, cancellation, eagerness/laziness, generators, and backpressure.
- Performance-sensitive complexity, query count, memory use, caching, and batching.
- Security, authorization, tenancy, trust, and process boundaries.

## Match evidence to risk

| Change shape | Minimum useful evidence |
| --- | --- |
| Private local expression/control-flow rewrite | Focused tests plus parse/lint; inspect side effects and exception timing |
| Inline or remove a private helper | Repository reference search plus focused tests and caller inspection |
| Collapse a wrapper or abstraction | All callers and implementations, test doubles, registration, boundary checks, focused tests |
| Cross-module representation change | Serialization/validation tests, type checks, integration tests, public-boundary inspection |
| Async, transaction, cache, or concurrency change | Explicit semantic tests for ordering/failure/cancellation or leave as recommendation |
| Public API, schema, persistence, security, or compatibility change | Do not auto-apply; require case-specific authority and broader verification |

When no meaningful test covers behavior, add a characterization test only if tests are within scope and the test itself does not freeze an accidental implementation detail. Otherwise defer the refactor.

## Final diff review

Confirm that the batch:

- Removes an obligation rather than moving it elsewhere.
- Does not introduce a new abstraction larger than the removed complexity.
- Does not mix unrelated formatting or cleanup.
- Preserves useful rationale and removes stale narration.
- Changes only disclosed, owned files.
- Leaves the working tree's pre-existing changes intact.

Never weaken assertions, delete difficult tests, over-mock collaborators, update snapshots blindly, or describe inferred equivalence as proven.
