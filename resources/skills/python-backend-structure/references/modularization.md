# Modularizing an existing service

Folder restructuring is useful only when it makes ownership, dependency
direction, testing, or change isolation clearer. Preserve behavior unless the
task explicitly includes behavioral change.

## Find boundaries before moving files

For every current module, record:

- its public entry points;
- the business action or technical boundary that owns it;
- external effects it performs;
- who imports it;
- what it imports;
- the failure contracts it exposes;
- the lifecycle in which it runs.

Files that change for the same business reason should usually stay together.
Files that share only a framework or SDK do not necessarily belong together.

## Split by responsibility signals

Consider splitting when a module:

- combines process lifecycle with business execution;
- combines deterministic policy with network/model/storage invocation;
- owns several unrelated public entry points;
- has distinct groups of tests that require different setup;
- has imports from several outer technologies mixed with domain decisions;
- is repeatedly edited for unrelated business actions;
- forces consumers to import private details to access one contract.

Line count, function count, and nesting are review signals, not reasons by
themselves. Do not turn every 40-line file into a package.

## Grow every boundary progressively

Flat-first is an application-wide rule, not an adapter exception. Start with the
fewest cohesive modules directly below the boundary that owns them. For roughly
three to five related modules, prefer direct navigation over another package
level. Do not create one-file subpackages or file-per-class layouts by default.

Extract a narrower package only when it contains several related modules,
changes independently from its siblings, needs different test setup, or starts
causing naming collisions. The count is a signal, not a mechanical threshold.
Do not create a large mixed-responsibility module merely to minimize `.py`
files; optimize for the minimum *coherent* set of modules. The stable GenAI
definition/setup modules are an explicit invariant, not speculative splitting.

Start with action-focused application modules:

```text
application/
├── email_admission.py
├── email_classification.py
└── email_replay.py
```

When several actions form a coherent capability, grow only that slice below
`application/`:

```text
application/
├── email/
│   ├── admission.py
│   ├── classification.py
│   └── replay.py
└── alerts/
    └── send.py
```

Introduce deeper action packages or `commands/`, `queries/`, and `workflows/`
only after those structures have demonstrated meaning. Do not add root
`pipeline/`, `use_cases/`, `workflows/`, or `operations/` peers.

External contracts stay in root `ports/`, concrete integrations in root
`adapters/`, and every GenAI responsibility in root `genai/`:

```text
ports/
└── email_classifier.py
adapters/
└── aws/
    ├── clients.py
    ├── sqs_consumer.py
    ├── sqs_serialization.py
    └── s3_raw_email_store.py
genai/
└── email_classification/
    ├── prompts.py
    ├── schemas.py
    ├── llm.py
    └── classifier.py
```

Never move prompts or `llm.py` into the application action as a small-service
shortcut, and never fold them into the GenAI classifier to reduce file count.
Every GenAI task keeps `prompts.py`, `schemas.py`, and `llm.py` as stable flat
definition/setup modules. A capability implementation such as `classifier.py`
is separate and invokes the configured handle. Avoid other empty extension
points and speculative `base.py`, factory, registry, or plugin layers for one
implementation.

Grow adapter folders one demonstrated responsibility at a time. Keep a small
`adapters/aws/` flat; promote only a growing slice to `aws/sqs/` or `aws/s3/`
when it has several cohesive files or an independent reason to change. Do not
create nested packages for three to five easily scanned modules preemptively. See
[templates.md](templates.md#flat-first-package-growth) for the concrete
before-and-after tree.

Do not create a port merely because a class has collaborators or benefits from a
test double. Ports isolate I/O and nondeterministic external capabilities. Keep
parsing, ETA calculation, correlation, validation, and other pure business logic
in `domain/` or the owning application action.

## Migration sequence

1. Establish the target ownership map and dependency direction.
2. Stabilize or introduce typed contracts at the boundary being moved.
3. Move contract/errors first when current business code imports adapter errors.
4. Move deterministic logic and keep its tests passing.
5. Move concrete integrations into root `adapters/`, persistence into `db/`,
   and all GenAI implementation into root `genai/`; translate failures at the
   owning port boundary.
6. Flatten speculative subpackages across every boundary, or introduce a
   narrower package only where demonstrated growth now justifies it.
7. Move composition/lifecycle code into `bootstrap/` and keep `main.py` thin.
8. Update API, adapter consumers, diagnostics, configuration, Docker/CLI entry
   points, telemetry names, and tests.
9. Remove compatibility imports only after all internal consumers migrate.

Use temporary re-exports only when downstream code cannot migrate atomically.
Mark them as transitional and remove them in the same planned change when
possible.

Move one coherent boundary or business action at a time. After each slice, run
focused tests plus import/type checks. Finish with repository-wide lint, type,
and test verification proportional to the change.

## Review questions

- Can a reader find startup wiring without reading business code?
- Can a reader find each public business action under `application/` and each
  application contract under `ports/`?
- Does each external technology have an explicit boundary owner?
- Can business tests replace external effects with typed fakes?
- Does each port isolate a real I/O or nondeterministic capability, and is it
  named after the caller's need rather than its current implementation?
- Do failure types point inward, or does business code import SDK/adapter errors?
- Are action modules under `application/` named in understandable business
  language, with ordered machinery added only where real sequencing exists?
- Are settings and secrets in `config/`, with resolved values injected?
- Are API middleware and routers transport-only?
- Are background task lifecycles isolated in bootstrap/supervision code?
- Does every service with GenAI have root `genai/`, containing every prompt,
  schema, model binding, agent, tool, and graph state without exception?
- Are all concrete broker, storage, HTTP, browser, and vendor integrations below
  root `adapters/`, with no competing root `messaging/` package?
- Are small packages flat across all boundaries, with nested folders introduced
  only after demonstrated growth and without file-per-class fragmentation?
- Do errors and static values live with their owner, while deployment-varying
  values live in `config/` rather than a global constants module?
- Are `utils`, `shared`, `common`, and `core` being used as catch-alls?
- Does any deployable import another deployable's private source package?
- Were empty directories or abstractions created without a current consumer?

## Reporting a structural review

Distinguish:

- **Violation:** dependency direction or ownership is concretely wrong.
- **Improvement:** the current structure works, but another shape would improve
  navigation or test isolation.
- **Preference:** naming or layout difference without a material effect.

Recommend migrations only for violations or improvements with a clear benefit.
Do not present personal aesthetic consistency as an architectural requirement.
