# Canonical backend template

Use this reference to produce a concrete target tree after applying the
ownership and dependency rules in [boundaries.md](boundaries.md). Omit unused
directories; never add empty packages merely to complete a drawing.

## Application shell

```text
src/<package>/
├── __init__.py
├── main.py                         # Thin executable entry point
├── bootstrap/                      # Composition and process lifecycle
│   ├── runtime.py                  # Build/dispose long-lived dependencies
│   ├── app.py                      # ASGI/FastAPI factory, when applicable
│   └── supervisor.py               # Background lifecycle, when applicable
├── config/
│   ├── settings.py
│   └── secrets.py
├── api/                            # HTTP transport, when present
├── application/                    # Business actions and orchestration
├── domain/                         # Reused business nouns and pure rules
├── ports/                          # Application-facing external contracts
├── adapters/                       # Concrete external integrations
├── genai/                          # Mandatory when any GenAI exists
├── db/                             # Persistence boundary, when present
├── observability/
└── diagnostics/                    # Optional operator diagnostics
```

`core/` is deliberately absent. Add it only for a dependency-light primitive
already shared across several boundaries, such as immutable application
context. For APIs, workers, consumers, and hybrid processes, use the concrete
trees in [api-and-workers.md](api-and-workers.md).

## Representative service tree

This example demonstrates placement, not required contents:

```text
src/<package>/
├── application/
│   ├── email_admission.py
│   ├── email_classification.py
│   └── email_replay.py
├── domain/
│   ├── email.py
│   └── parsing.py
├── ports/
│   ├── raw_email_store.py
│   └── email_classifier.py
├── adapters/
│   └── aws/
│       ├── clients.py
│       ├── sqs_consumer.py
│       ├── sqs_serialization.py
│       └── s3_raw_email_store.py
└── genai/
    └── email_classification/
        ├── llm.py
        ├── schemas.py
        ├── prompts.py
        └── classifier.py
```

When several application actions form one cohesive capability, promote only
that slice, for example:

```text
application/
├── email/
│   ├── admission.py
│   ├── classification.py
│   └── replay.py
└── alerts/
    └── send.py
```

For the enforced GenAI variants and growth rules, use [ai.md](ai.md). For the
criteria that justify any file-to-package promotion, use
[boundaries.md](boundaries.md#flat-first-growth-across-boundaries).

## Placement test

Use these questions in order when ownership is ambiguous:

| Question | Location |
| --- | --- |
| Does it deliver an understandable business action or outcome? | `application/` |
| Is it a reusable business noun, value object, or pure rule? | `domain/` |
| Does it define an external or nondeterministic capability an action needs? | `ports/` |
| Does it implement that need with an ordinary external SDK or system? | `adapters/` |
| Does it contain any LLM, agent, prompt, AI schema, tool, graph, or model binding? | `genai/` |
| Does it expose HTTP transport concerns? | `api/` |
| Does it execute persistence queries or own sessions/repositories? | `db/` |
| Does it construct or dispose the runtime graph? | `bootstrap/` |

GenAI, API, and database code use their specialized root boundaries rather than
the general `adapters/` category.

## Tests

Keep tests beside the member, outside its import package. Use
[testing.md](testing.md) as the single authority for the target test tree,
execution profiles, fixture ownership, markers, CI selection, and migration.
