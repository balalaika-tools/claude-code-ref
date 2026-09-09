---
name: python-service-architecture-audit
description: >-
  Audit or repair architectural drift inside an established Python backend
  service. Use for hexagonal dependency violations, misplaced modules, leaking
  framework contracts, speculative ports, centralized errors, GenAI boundary
  problems, or the final verification of a structural refactor. Do not use for
  ordinary feature edits that do not change or review service boundaries.
---

# Python Service Architecture Audit

Find architectural defects from repository evidence, distinguish enforceable
violations from judgment calls, and repair only when the user's request includes
changes. This is an operational review skill; `python-service-architecture` is
the canonical source of structure and ownership rules.

## Required context

Read the `python-service-architecture` skill and the references it routes for the
service under review. Inspect the real source tree, imports, application entry
points, ports, concrete implementations, bootstrap wiring, tests, and runtime
configuration. Never infer architecture from filenames alone.

Run the bundled deterministic audit against the import package:

```bash
python scripts/audit_service.py path/to/src/package
```

Treat script failures as concrete violations. Its review notices are prompts for
semantic inspection, not proof.

## Semantic audit

Trace at least one real business action from its process boundary through
application code, ports, concrete implementations, and bootstrap. Check:

- dependencies point inward and application code never imports concrete DB,
  adapter, API, bootstrap, or GenAI implementations;
- every port expresses a caller-needed external capability, passes the port
  admission test, and avoids framework operations, configuration controls,
  vendor types, broad `Any`, and concrete telemetry lifecycle APIs;
- concrete implementations translate their SDK failures into the port-owned
  failure contract, without a universal adapter hierarchy or central translator;
- errors, constants, validation, and helpers stay with their semantic owner;
- bootstrap injects a capability implementation rather than a raw client,
  model, agent, graph, checkpointer, session, or telemetry handle;
- GenAI tasks own their model binding, prompts, schemas, tools, middleware, and
  application-facing capability adapter without leaking LangChain/LangGraph;
- multiple tools are organized vertically, one exposed tool per module, with
  tool-only schemas, normalization, and helpers colocated;
- `genai/shared/` contains demonstrated identical reuse, stays flat initially,
  and does not mix schemas, middleware, retry mechanics, invocation behavior,
  registries, and provider policy under vague filenames;
- package depth and abstractions are justified by current ownership, change, or
  test pressure rather than anticipated reuse.

Search for unused ports and protocols, but inspect callers before recommending
deletion. Structural typing, a passing type checker, and test fakes do not prove
that a port is technology-neutral or useful.

## Findings and repair

Classify every finding as:

- **Violation:** dependency direction, contract leakage, or ownership is wrong.
- **Improvement:** a different shape materially improves isolation or navigation.
- **Preference:** cosmetic difference without architectural consequence.

Do not present preferences as violations. For an audit-only request, report
evidence and the smallest migration sequence without writing files. For an
authorized repair, move one coherent boundary at a time, update all consumers,
add or strengthen behavior/contract tests for the defect, and run focused tests
before the complete relevant suite.

## Repair planning gate

After the audit, unless the user explicitly requested a report-only review,
choose exactly one workflow for confirmed violations and worthwhile
improvements. Preferences alone do not justify either workflow.

Use the following rubric to decide whether the repair deserves a durable
specification.

**OpenSpec hard triggers.** Use the
[`openspec-propose`](../openspec-propose/SKILL.md) skill when any one is true:

- the repair intentionally changes a public API, event or message shape,
  persisted data schema, CLI contract, shared-library interface, authorization
  rule, or other behavior relied on outside the owning module; restoring behavior
  already established by tests or documentation is not a contract change;
- old and new behavior or data must coexist, consumers must migrate in a
  coordinated order, or the change needs a backfill, deprecation, feature flag,
  compatibility shim, or rollback design;
- implementation cannot start safely until the user chooses between viable
  designs with materially different behavior, ownership, compatibility, data,
  security, or operational tradeoffs.

**Complexity signals.** Also use OpenSpec when at least two are true:

- the repair changes three or more of these boundaries with non-mechanical
  consequences: process/API, application, port, adapter/infrastructure,
  bootstrap/composition;
- it spans multiple independently deployed services, publishable packages, or
  separately owned components;
- it introduces or removes a compatibility surface, abstraction, or dependency
  direction rather than merely relocating an existing implementation;
- acceptance criteria remain materially uncertain after inspecting current
  tests, documentation, callers, and repository history.

Follow `openspec-propose` completely, create the proposal artifacts, and then
stop. Do not implement the proposed repair in the same response.

Prefer the retained `PLAN*.md` workflow when there is no hard trigger and fewer
than two complexity signals. Typical direct repairs are localized or mechanical,
preserve an already established contract, have clear acceptance criteria, can be
validated in one repository, and do not require coordinated rollout. File count
and line count alone never determine the branch.

When an OpenSpec change would be disproportionate, implement the repair
directly through a retained Markdown plan:

1. Create `PLAN.md` in the project root before editing project code. If that
   file already exists, do not overwrite or modify it; use
   `ARCHITECTURE-AUDIT-PLAN.md`, then add the first available numeric suffix
   such as `ARCHITECTURE-AUDIT-PLAN-2.md` if necessary.
2. Record every in-scope repair and validation step as a Markdown task checkbox.
   Keep the plan focused on confirmed violations and worthwhile improvements.
3. Implement all items in the plan, updating each checkbox as work completes.
   Add brief notes for any item that cannot be completed and leave it unchecked.
4. Run the completion gate below, record the validation outcome in the same
   plan, keep the plan file in the project root for review, and stop.

Do not create both an OpenSpec proposal and a `PLAN*.md` repair plan for the same
audit. The OpenSpec branch is planning-only; the retained-plan branch includes
implementation.

## Completion gate

Before declaring a structural repair complete:

1. rerun `scripts/audit_service.py`;
2. run the service's architecture contract tests;
3. run formatting, lint, type checking, and the relevant test profiles;
4. report remaining semantic risks that static checks cannot prove.

Never claim that the audit proves port usefulness, error ownership, bootstrap
composition, or runtime behavior when only static imports were checked.
