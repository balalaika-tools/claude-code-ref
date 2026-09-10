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
semantic inspection, not proof. Report its result as **static checks**, never as
the result of the architecture audit as a whole. A zero-finding script run does
not reduce or replace the semantic work below.

Before tracing individual paths, inventory every public application action and
long-running process runner. For each one, record its input and output contract,
caller, injected collaborators, business decisions, external effects, and the
owner of any loop or lifecycle. Use that inventory to ensure a healthy action
does not hide drift in an uninspected sibling. Then trace every action far enough
to assign its decisions and effects to owners, with at least one complete
process-to-implementation trace for each distinct external capability family.

## Semantic audit

Trace real business actions from their process boundary through application
code, ports, concrete implementations, and bootstrap. Check:

- dependencies point inward and application code never imports concrete DB,
  adapter, API, bootstrap, or GenAI implementations;
- every port expresses a caller-needed external capability, passes the port
  admission test, and avoids framework operations, configuration controls,
  vendor types, broad `Any`, and concrete telemetry lifecycle APIs;
- concrete implementations translate their SDK failures into the port-owned
  failure contract, without a universal adapter hierarchy or central translator;
- errors, constants, validation, and helpers stay with their semantic owner;
- application actions contain the business decision they claim to represent;
  a method that only delegates an intent-named operation such as `complete`,
  `fail`, `expire`, or `approve` is a review prompt, especially when the concrete
  DB or adapter implementation chooses statuses, classifications, public error
  codes, messages, or downstream transitions;
- database and other concrete adapters execute queries and atomically realize
  caller-owned decisions rather than inventing business transitions hidden
  behind a broad command-shaped port;
- long-running loops, stop events, idle sleeps, task creation, graceful
  shutdown, and health supervision stay in bootstrap/supervisor code; keep the
  independently invokable `*_once`, `execute`, or equivalent business action in
  `application/`;
- inbound API, broker, and SDK DTOs are translated at the process adapter;
  inspect fields recursively rather than trusting a wrapper named `domain` or
  `command`, and reject receipt handles, acknowledgements, Kafka topics,
  partitions, offsets, provider messages, raw requests/responses, and equivalent
  delivery metadata that cross into application, domain, or ports;
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

For each application action, compare its focused unit tests with its concrete
integration tests. Missing unit coverage is not automatically an architecture
violation, but if business outcomes can only be demonstrated through a real DB,
broker, model, or SDK, inspect whether policy has escaped into that concrete
implementation.

Summarize the semantic pass with a compact ownership matrix containing, as
applicable: action, business decision, boundary input, port, concrete
implementation, state-transition owner, and lifecycle owner. Explicitly label
static-script findings separately from semantic findings.

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

## Completion gate

Before declaring a structural repair complete:

1. rerun `scripts/audit_service.py`;
2. run the service's architecture contract tests;
3. run formatting, lint, type checking, and the relevant test profiles;
4. report remaining semantic risks that static checks cannot prove.

Never claim that the audit proves port usefulness, error ownership, bootstrap
composition, or runtime behavior when only static imports were checked.
