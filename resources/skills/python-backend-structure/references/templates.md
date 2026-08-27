# Canonical backend template

Use one stable structural vocabulary across services. Omit unused directories,
but do not replace these categories with a competing business-execution layout
merely because a service is small.

## Application shell

```text
src/<package>/
├── __init__.py
├── main.py                         # Thin executable entry point
├── bootstrap/                      # Composition and process lifecycle
│   ├── runtime.py                  # Build/dispose long-lived dependencies
│   ├── app.py                      # ASGI/FastAPI factory, when applicable
│   └── supervisor.py               # Background task lifecycle, when applicable
├── config/
│   ├── settings.py
│   └── secrets.py
├── api/                            # HTTP transport, when present
├── application/                    # Use cases and business-value actions
├── domain/                         # Reused business nouns and pure rules
├── ports/                          # Technology-neutral application contracts
├── adapters/                       # Concrete external integrations
├── genai/                          # Mandatory when any GenAI exists
├── db/                             # Persistence boundary, when present
├── observability/
└── diagnostics/                    # Optional operator diagnostics
```

`main.py` should normally be boring. It may load configuration and select a
process command, then delegate. Resource construction and shutdown belong in
`bootstrap/runtime.py`; business work does not.

`core/` is deliberately absent from the default tree. Create it only after a
small, dependency-light primitive is genuinely application-wide across several
boundaries, for example `core/context.py` or shared identity types. Errors and
constants never belong there. Never create `core/` as the initial home for
helpers or important-looking code.

## Business actions

`application/` is the canonical namespace for business execution. It holds
independent use cases as well as genuinely ordered workflows:

```text
application/
├── email_admission.py
├── email_classification.py
├── email_replay.py
├── alert_sending.py
└── submit_batch.py
```

Each module coordinates one understandable business action through domain rules
and ports. The folder name does not imply that every action participates in one
ordered sequence. Do not create peer root `pipeline/`, `use_cases/`,
`workflows/`, or `operations/` namespaces.

When several actions form a coherent business capability, promote only that
slice to a capability package:

```text
application/
├── email/
│   ├── admission.py
│   ├── classification.py
│   └── replay.py
├── cases/
│   ├── correlate.py
│   ├── resolve.py
│   └── escalate.py
└── alerts/
    └── send.py
```

Introduce `commands/`, `queries/`, `workflows/`, a deeper action package,
`runner.py`, checkpoint contracts, or stage-level retry below `application/`
only when execution actually has those semantics. A process polling loop
remains in `bootstrap/supervisor.py` or an inbound adapter.

## Domain, ports, adapters, and GenAI

```text
domain/
├── email.py
├── authentication.py
├── parsing.py
├── eta.py
└── correlation.py
ports/
├── raw_email_store.py
└── email_classifier.py
adapters/
└── aws/
    ├── clients.py
    ├── sqs_consumer.py
    ├── sqs_serialization.py
    └── s3_raw_email_store.py
genai/
└── email_classification/
    ├── prompts.py                  # Stable prompt definitions/builders
    ├── schemas.py                  # Stable AI input/output schemas
    ├── llm.py                      # Model construction/binding only
    └── classifier.py               # EmailClassifier implementation
```

Keep `domain/` absent when no concepts are genuinely shared across application
actions. Create a port only when the application benefits from isolating the
effect. Every concrete non-HTTP, non-database, non-GenAI implementation belongs
under `adapters/`, even when only one action uses it. Every GenAI implementation
belongs under root `genai/`, even when it is small or used by one action.

Do not create root `operations/`, root business-capability packages, or root
`messaging/`. `api/`, `db/`, and `genai/` are deliberate specialized root
boundaries; all other concrete integration code belongs under `adapters/`.

The business action remains `application/email_classification.py`. The GenAI
`classifier.py` is only the concrete implementation of the caller-owned
`EmailClassifier` port: it invokes the configured handle and translates the
provider result. It does not own classification workflow, deterministic rules,
fallback selection, persistence, or handoff decisions.

`application/email_classification.py` is not an empty wrapper. Depending on the
use case, it accepts or retrieves the email, runs eligibility and deterministic
rules, decides whether to call `EmailClassifier`, turns its typed candidate into
a business decision, persists or publishes the result, and selects retry,
defer, or human-review behavior. The GenAI classifier owns prompt/model
invocation and provider translation only.

## Flat-first package growth

Use the fewest cohesive modules inside every boundary. Keep roughly three to
five related files flat beneath their current owner; treat that range as a
review signal rather than a target. Do not introduce a package for every class,
exception group, constants group, or private helper. Small owned definitions
can stay in the module that uses them.

This rule does not collapse the stable GenAI responsibilities. A simple
structured-model task always keeps these four flat modules:

```text
genai/email_classification/
├── prompts.py
├── schemas.py
├── llm.py
└── classifier.py
```

`prompts.py` defines/builds prompts, `schemas.py` owns AI-facing schemas,
`llm.py` constructs and binds the model, and the capability-named implementation
invokes that handle and implements its port. Do not fold the first three into
`classifier.py` to reduce file count. If the task builds an agent, add
`agent.py`; it imports the configured model from `llm.py`.

When one narrower area has several cohesive modules or an independent reason to
change, promote only that slice. This applies equally to a growing application
action, API version, database capability, GenAI task, or adapter provider. Do
not merge unrelated responsibilities into a catch-all solely to reduce the file
count.

## Errors and constants follow ownership

Keep failures and static values beside the boundary that gives them meaning.
Small definitions stay in their owning module; extract `errors.py` or
`constants.py` only when the owner has enough cohesive definitions to justify a
separate file.

```text
domain/errors.py                         # Business/domain failures
application/errors.py                    # Cross-action use-case failures
application/email/errors.py              # Capability-local use-case failures
ports/email_classifier.py                # Port-visible success/failure contract
adapters/aws/errors.py                    # Private AWS failures
genai/email_classification/errors.py      # Private AI failures
```

Adapter and GenAI errors must be translated to a port-owned failure before they
reach `application/`. Do not create root, `core/errors.py`, or
`common/errors.py` collections, even for a shared base or taxonomy. Shared
business failures stay in `domain/`, cross-action use-case failures stay in
`application/`, and stable external failure contracts stay with their port.

Apply the same ownership rule to true constants:

```text
Business invariant/static value     -> domain/ or its owning module
Use-case-specific invariant         -> application/ or its owning action
AWS/provider-specific static value  -> adapters/<provider>/
LLM/agent-specific static value     -> genai/<task>/
Environment/deployment value        -> config/
```

When an owned set is large enough to earn a module, concrete locations include
`domain/constants.py`, `application/email/constants.py`,
`adapters/aws/constants.py`, and
`genai/email_classification/constants.py`.

Do not create root `constants.py` or `core/constants.py`. Model IDs, regions,
queue URLs, timeouts, retention periods, and concurrency limits are normally
configuration even when written in uppercase; place them in `config/`. Prefer
an enum, literal, or value object when it expresses a domain invariant better
than a constants module.

## Adapter growth example

Keep a small provider package flat. Three to five cohesive AWS modules are easier
to scan directly:

```text
adapters/
└── aws/
    ├── clients.py
    ├── sqs_consumer.py
    ├── sqs_serialization.py
    └── s3_raw_email_store.py
```

When one provider area develops several files or an independent reason to
change, promote only that area to a subpackage:

```text
adapters/
└── aws/
    ├── clients.py
    ├── sqs/
    │   ├── consumer.py
    │   └── serialization.py
    └── s3/
        └── raw_email_store.py
```

Do not create `sqs/`, `s3/`, `http/`, or other nested extension points before
their contents justify the navigation cost.

## Port discipline

Ports describe externally fulfilled capabilities needed by application actions:

```text
ports/
├── raw_email_store.py
├── email_classifier.py
└── ticket_repository.py            # Only when a DB port earns its cost
```

Do not create ports for deterministic in-process logic:

```text
domain/
├── parsing.py
├── eta.py
└── correlation.py
```

Name a port for what the caller needs, not how it happens. `EmailClassifier`
can be implemented by rules, an LLM, a hybrid, or a remote API;
`ClassificationModel` prematurely assumes one implementation.

## Placement test

Use these questions in order when a file's owner is ambiguous:

| Question                                                                             | Location         |
| ------------------------------------------------------------------------------------ | ---------------- |
| Does it deliver an understandable business action or outcome?                        | `application/` |
| Is it a reusable business noun, value object, or pure rule?                          | `domain/`      |
| Does it define an I/O or nondeterministic capability an application action needs?    | `ports/`       |
| Does it implement that need with AWS, Kafka, browser, HTTP, storage, or another SDK? | `adapters/`    |
| Does it contain any LLM, agent, prompt, AI schema, tool, graph, or model binding?    | `genai/`       |
| Does it expose HTTP transport concerns?                                              | `api/`         |
| Does it execute persistence queries or own sessions/repositories?                    | `db/`          |
| Does it construct or dispose the runtime graph?                                      | `bootstrap/`   |

GenAI wins over the general adapter category: an LLM implementation always goes
to `genai/`, never `adapters/`. API and database code likewise use their
specialized root boundaries.

## Test layout

Keep tests beside the service or library that owns them. A small suite with one
execution profile may remain flat; a suite with distinct infrastructure,
lifecycle, isolation, or CI needs is organized by execution profile first and
behavioral owner second. Do not mirror every source file mechanically.

Read [testing.md](testing.md) for the canonical test tree, mutually exclusive
classification rules, fixture and support-code ownership, markers, CI selection,
and migration guidance.
