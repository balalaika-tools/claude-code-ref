---
name: python-service-architecture-audit
description: >-
  Audit or repair architectural drift inside an established Python backend
  service. Use for hexagonal dependency violations, misplaced modules, leaking
  framework contracts, speculative ports, centralized errors, GenAI boundary
  problems, duplicated cross-service infrastructure, or the final verification
  of a structural refactor. Do not use for
  ordinary feature edits that do not change or review service boundaries.
---

# Python Service Architecture Audit

Find architectural defects from repository evidence, distinguish enforceable
violations from judgment calls, and route confirmed findings to planning or
focused repair as described below. This is an operational review skill; `python-service-architecture` is
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

### Shared-capability review

In a workspace, compare the reviewed service's technical plumbing with existing
libraries and matching code in current consumers. Explicitly search for overlapping
modules and duplicated capabilities, including service-local copies of capabilities
already provided by shared libraries. Keep this read-only comparison
focused on candidate capabilities; it does not authorize repairs to siblings.
Read `python-service-architecture/references/shared-libraries.md` when a candidate
emerges, and `otel-observability/references/setup/shared_library.md` for repeated
provider lifecycle, logging processors, or propagation policy.

For each candidate, report the source paths and consumers, shared operational
meaning, actual differences, proposed minimal public inputs, service-local
policy, dependency/lifecycle costs, and smallest consumer-by-consumer migration.
Check that library inputs would be explicit typed values: environment, YAML,
secrets, and service settings remain service-owned and are mapped by bootstrap.
Recommend extraction when stable reuse removes duplicated policy or lifecycle;
explain retention when similar code has different semantics or dependency needs.
Classify justified extraction as an **Improvement**, unless an existing ownership
or compatibility contract is already violated. Do not recommend generic shared
dumping grounds or wrappers that merely rename SDK calls. Static import checks
and textual similarity cannot establish semantic reuse.

### Classification

Classify every finding as:

- **Violation:** dependency direction, contract leakage, or ownership is wrong.
- **Improvement:** a different shape materially improves isolation or navigation.
- **Preference:** cosmetic difference without architectural consequence.

Do not present preferences as violations. Move one coherent boundary at a time
when repairing, update all consumers, add or strengthen behavior/contract tests
for the defect, and run focused tests before the complete relevant suite.

### Route the findings

After completing the semantic and shared-capability review, choose and explain
one route. A normal invocation includes this follow-through; do not stop at a
chat-only report just because the user called the task an audit. An explicit
read-only, report-only, or no-changes instruction overrides this default: report
the findings and recommended route without writing files or implementing repairs.

- **No actionable findings:** report the checks and remaining uncertainty. Do
  not create an empty feedback file or proposal, or implement preferences.
- **Substantial findings or planning needed:** invoke
  [openspec-propose](../openspec-propose/SKILL.md) to create a complete change
  proposal, delta specs, design, and implementation tasks using that workflow's
  resolved paths and required artifacts. Choose this route for numerous findings,
  coordinated changes across boundaries or consumers, shared-library extraction,
  state-transition or compatibility changes, or material design uncertainty.
  Count alone does not decide: one consequential finding can require a proposal.
  Include evidence, classification, acceptance criteria, shared-capability
  conclusions, migration order, and verification tasks. Stop after presenting the
  completed planning artifacts; do not implement any of the proposed repairs in
  the same turn. Wait for a new user request to start the apply workflow.
- **Few, bounded findings:** when the fixes are local, understood, reversible,
  and do not require the coordination or decisions above, create `FEEDBACK.md`
  at the reviewed repository root before editing code, then implement the fixes
  directly. If that file already exists, preserve it and choose an unused
  descriptive prefix such as `worker-architecture-FEEDBACK.md`, adding a numeric
  prefix if needed. Record each finding's classification, source evidence,
  intended fix, and acceptance/verification steps as Markdown checkboxes. Start
  pending work with `- [ ]`; change it to `- [x]` only after the fix and its
  required checks succeed. Run the completion gate below and record results and
  any remaining unchecked work in the same file. Do not ask for redundant repair
  confirmation within this default scope.

Keep repairs scoped to the reviewed service and its necessary consumers. A
read-only comparison with sibling services does not authorize repairing them.
If focused repair reveals a need for coordinated design, preserve the feedback
and completed work, route the remaining work through `openspec-propose`, and
stop after planning. If the proposal workflow is unavailable, explain the
blocker and report the findings; do not substitute unplanned implementation.

## Completion gate

Before declaring a structural repair complete:

1. rerun `scripts/audit_service.py`;
2. run the service's architecture contract tests;
3. run formatting, lint, type checking, and the relevant test profiles;
4. report remaining semantic risks that static checks cannot prove.

Never claim that the audit proves port usefulness, error ownership, bootstrap
composition, or runtime behavior when only static imports were checked.
