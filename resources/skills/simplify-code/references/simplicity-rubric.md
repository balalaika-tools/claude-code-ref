# Simplicity rubric

## Contents

1. Objective
2. Candidate sources
3. Abstraction decisions
4. Evidence and risk
5. Finding schema
6. Prioritization and integration

## Objective

Reduce accidental complexity while preserving essential complexity and observable behavior. Prefer changes that reduce:

- Concepts a reader must hold at once.
- Branches, nesting, implicit state, and impossible-state combinations.
- Layers and files crossed to understand one operation.
- Pass-through calls, repeated arguments, and configuration plumbing.
- Representations of the same data and conversions between them.
- Sites that must change together for one feature.
- Dependencies or custom code duplicating an accepted capability.
- Duplicated policy, validation, error translation, or orchestration.
- Speculative extension points with no current use.

Do not optimize directly for line count, function/class count, metric thresholds, maximum idiom use, maximum library use, or global uniformity.

## Candidate sources

### Structure and indirection

- Pass-through wrappers, forwarding methods, one-line adapters, and manager/provider/factory/service/repository chains that add no policy.
- Single-use helpers or classes that scatter a linear operation.
- Inheritance, mixins, protocols, ABCs, strategies, builders, or plugin mechanisms without present variation.
- Generic frameworks built for one concrete case.
- Dependency-injection plumbing without a replaceable boundary.

### Control flow and state

- Nesting removable with guard clauses or a clearer state model.
- Repeated boolean branches, flag arguments, and invalid state combinations.
- Defensive conditions already excluded by an upstream invariant.
- Parallel success/error paths that repeat cleanup or response construction.
- State duplicated across attributes, contexts, and locals.

### Data and locality

- Repeated dict/model/DTO/entity conversions without boundary value.
- Values forwarded unchanged through several layers.
- Temporary collections or intermediate objects without explanatory value.
- Multiple sources of truth or redundant caches.
- Duplicated business rules, validation, query construction, and error mapping.
- Code fragmented across files despite changing together.

Distinguish genuine duplication from coincidental similarity. Accept small local duplication when sharing it would couple separate policies.

### Lifecycle and support code

- Catch/log/re-raise chains that add no context and create duplicate logs.
- Repeated setup/cleanup suitable for a context manager.
- Retry, timeout, parsing, serialization, or batching code duplicating an accepted capability.
- Hooks that only forward to another hook.
- Test setup suitable for a focused fixture or parameterization.
- Test helpers that hide behavior behind a new testing DSL.

## Abstraction decisions

Keep an abstraction when it materially:

- Encodes a domain concept or invariant.
- Enforces policy rather than forwarding values.
- Separates I/O, persistence, process, trust, or ownership.
- Supports multiple current consumers or implementations with meaningful variation.
- Stabilizes a public contract or isolates volatile external behavior.
- Improves testing without worsening production navigation.

Inline, merge, or remove only with evidence that it:

- Forwards calls, fields, or configuration unchanged.
- Has one trivial caller and no domain meaning.
- Exists only for hypothetical variation.
- Renames an operation without changing semantics.
- Adds navigation but reduces neither coupling nor duplication.

Names such as `Factory`, `Manager`, `Repository`, or `Strategy`, a single implementation, a long function, or a parameter count are signals only. Never decide from a name or threshold alone.

## Evidence and risk

Keep confidence separate from risk:

| Dimension | Low | Medium | High |
| --- | --- | --- | --- |
| Confidence | Pattern-only lead or unresolved counter-evidence | Direct local evidence but incomplete caller/boundary proof | Callers, implementations, contracts, and tests support the judgment |
| Risk | Private, local, covered, behavior-mechanical | Several callers or incomplete coverage | Public/dynamic boundary, persistence, concurrency, security, or broad cross-package surface |

A high-confidence public rewrite remains high risk. A low-risk edit with weak evidence should still be rejected.

Record counter-evidence: tests using a fake implementation, framework registration, external imports, metrics/instrumentation, policy enforcement, compatibility history, performance measurements, or distinct ownership.

## Finding schema

Use this shape for structured candidates:

```json
{
  "fingerprint": "billing/service.py:42|design|remove-tax-forwarder",
  "path": "billing/service.py",
  "line": 42,
  "end_line": 45,
  "category": "design",
  "detector": "pass-through-function",
  "summary": "Remove the tax lookup forwarder",
  "evidence": ["Forwards every argument unchanged to TaxTable.lookup", "One internal caller"],
  "counter_evidence": [],
  "proposal": "Call TaxTable.lookup directly from calculate_invoice",
  "behavior_contract": ["Preserve return value", "Preserve exception propagation"],
  "confidence": "high",
  "risk": "low",
  "conceptual_reduction": 3,
  "affected_files": ["billing/service.py"],
  "verification": ["pytest tests/billing/test_service.py -q"],
  "crosses_boundary": false
}
```

Generate fingerprints as `{relative_path}:{start_line}|{category}|{short-summary-slug}`. Keep the slug lowercase, hyphenated, semantic, and at most 40 characters. Preserve it across reruns when line movement is the only change.

Treat analyzer candidates as unresolved until code reading fills missing evidence, behavior contracts, and verification. Do not manufacture a confidence percentage.

## Prioritization and integration

Prioritize net simplification:

1. Conceptual reduction and obligations deleted.
2. Evidence strength and test support.
3. Narrowness of change surface.
4. Public, dynamic, package, ownership, and runtime risk.
5. Whether the proposal removes complexity rather than relocating it.

Ordinary maintainability findings are `P3`; cosmetic polish is rarely `Nit`. Reserve `P2` for a material design issue with a named failure mode. Correctness, compatibility, security, access, data, concurrency, performance, operations, dependency, and testing defects belong to a correctness-focused review.
