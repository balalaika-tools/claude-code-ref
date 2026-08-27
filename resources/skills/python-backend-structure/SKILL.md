---
name: python-backend-structure
description: >-
  Design, scaffold, refactor, or review the internal folder structure of a
  Python backend service, including FastAPI applications, workers, event
  consumers, scheduled jobs, business workflows, and AI-enabled services.
  Standardize business execution under application, technology-neutral contracts
  under ports, concrete integrations under adapters, and all GenAI code under
  a root genai package, with clear bootstrap, API, persistence, configuration,
  and observability boundaries. Use when deciding where backend code belongs or
  standardizing package layouts. Do not use for uv workspace/Docker organization
  alone or for database-layer mechanics alone.
---

# Python Backend Structure

Apply the canonical structure in this skill consistently across backend services.
Omit categories that the service does not use, but do not substitute competing
folder schemes merely because the service is small. Deviate only when the
canonical category genuinely has no coherent meaning, and state the reason
before implementation. Dependency direction and ownership remain the primary
invariants.

## Required discovery

Before proposing or changing a structure:

1. Inspect the actual package tree, entry points, imports, tests, and deployment
   process. Do not infer architecture from filenames alone.
2. Identify independently meaningful business actions and their outcomes.
3. Identify process types: HTTP API, long-running worker, queue consumer,
   scheduled batch, CLI, or a combination.
4. Identify external effects and process-lifecycle resources: database, HTTP
   clients, object storage, queues, browser, files, LLMs, telemetry, and clocks.
5. Trace current dependency direction and locate business code that imports a
   concrete external implementation.
6. Preserve repository conventions unless changing them provides a clear,
   stated benefit. Never reorganize unrelated services merely for symmetry.

Read [references/templates.md](references/templates.md) and
[references/boundaries.md](references/boundaries.md) for every structural design
or refactor. Then load only the mode-specific references that apply:

- Read [references/api-and-workers.md](references/api-and-workers.md) for an HTTP
  API, worker, scheduled process, queue/Kafka/SQS consumer, or hybrid service.
- Read [references/ai.md](references/ai.md) when the package invokes an LLM,
  builds an agent or graph, exposes AI tools, or has prompts/model middleware.
- Read [references/modularization.md](references/modularization.md) when splitting
  existing modules, migrating an established service, or reviewing structure
  that has grown unclear.

## Canonical business execution

Use **`application/` as the stable home for executable business-value actions**.
An action belongs there when a reader can describe it in business language,
such as `email_admission`, `email_classification`, `email_replay`,
`alert_sending`, `response_understanding`, or `source_projection`.

`application/` is the canonical application/business-execution namespace. It
contains use cases, workflows, commands, queries, and business actions without
implying ordered stages. Do not use root `pipeline/`, `use_cases/`, `workflows/`,
or `operations/` as peer or alternative names. A service has one stable
business-execution namespace: `application/`.

- Start with action-focused modules such as `email_classification.py`.
- When several actions form a coherent capability, promote only that slice, for
  example `application/email/{admission,classification,replay}.py`.
- Introduce deeper `commands/`, `queries/`, `workflows/`, or action packages
  below `application/` only when the code actually has those semantics and the
  flat capability layout no longer remains cohesive.
- Use `domain/` for stable business nouns, value objects, and pure rules reused
  across actions. Do not move executable use-case orchestration into `domain/`.
- Use `ports/` for technology-neutral contracts required by application actions.
- Do not create root-level capability packages or generic `services.py`,
  `handlers.py`, and `managers.py` catch-alls.

Place business execution outside `application/` only when the service truly has no
business action, such as a transport-only proxy or health-only process. Treat
that as an explicit exception and explain it in the structural design.

## Stable application shell

Use these locations consistently when the responsibility exists:

- `main.py`: minimal process entry point; load settings and delegate to
  `bootstrap`.
- `bootstrap/`: composition root and lifecycle only—application/ASGI factory,
  runtime dependency graph, supervisors, startup and shutdown.
- `config/`: settings models, YAML/environment loading, and secret retrieval.
- `core/`: rare, dependency-light primitives already shared across several
  boundaries, such as immutable request context. Keep it absent by default; do
  not create it as a general home for errors, constants, helpers, or important
  code.
- `api/`: HTTP transport boundary—routers, request dependencies, middleware,
  transport schemas, and exception mapping.
- `application/`: executable business-value actions, use cases, and orchestration.
- `domain/`: reusable business nouns and pure rules, only when they exist.
- `ports/`: technology-neutral contracts consumed by application actions.
- `adapters/`: concrete non-HTTP, non-database, non-GenAI integrations, grouped
  by technology or external system.
- `genai/`: mandatory root boundary for every LLM, agent, prompt, model binding,
  AI schema, tool, graph, or AI middleware responsibility.
- `db/`: persistence boundary, repositories, sessions, and queries.
- `observability/`: telemetry mechanics and conventions, never business
  decisions.
- `diagnostics/` or `maintenance/`: explicit operator-facing commands; keep
  them out of runtime business packages.

Create only directories used by the current service. A template is a placement
policy, not a requirement to commit empty folders.

## Flat first, with the fewest cohesive modules

Apply flat-first growth inside every boundary: `application/`, `domain/`, `ports/`,
`adapters/`, `genai/`, `api/`, `db/`, `bootstrap/`, tests, and any capability
subpackage. This is not an adapter-only convention.

- Aim for the fewest cohesive `.py` files that keep responsibilities clear.
  Do not create a file merely to hold one class, one exception, a few constants,
  or a private helper when those definitions naturally belong in an existing
  owning module.
- Keep roughly three to five related modules flat beneath their current owner.
  This range is a review signal, not a quota or an automatic split point.
- Introduce a nested package only when one narrower responsibility has several
  cohesive modules, evolves independently, needs distinct test setup, or causes
  naming collisions in the parent package. Promote only that growing slice.
- Do not merge unrelated responsibilities into a large catch-all merely to
  reduce file count. “Fewest files” means the minimum coherent structure, not
  the minimum possible number of filesystem entries.

The canonical root boundaries still apply even when each starts with one file.
Flat-first controls growth *within* an owner; it does not justify putting GenAI
code in `application/` or concrete adapters in `domain/`. It also does not collapse
the required GenAI definition/setup modules described below: stable semantic
structure takes precedence over minimizing the raw file count.

## GenAI is always a root boundary

If the service contains any GenAI behavior, create root `genai/`; there is no
small-model or capability-colocation exception. All LangChain, LangGraph, model
provider SDK, prompt, AI output schema, tool, graph state, and AI-specific
middleware imports stay below it. Application code sees a typed port and business
result, never a provider response or model handle.

`genai/` never owns or orchestrates a business action. The action remains in
`application/`, for example `application/email_classification.py`. GenAI modules define
prompts, schemas, tools, middleware, graphs, and model/agent construction; a
boundary module such as `genai/email_classification/classifier.py` may invoke the
configured handle and implement `ports/email_classifier.py`, but it does not
decide the larger business workflow, deterministic fallback, or handoff policy.

The application action is therefore real executable code, not a forwarding alias.
It owns the use-case sequence: load or accept the business input, apply
deterministic eligibility and policy, decide whether the classifier capability
is needed, interpret its typed candidate as a business decision, persist or
publish the result, and select retry, defer, or human-review outcomes. Include
only the steps the actual use case needs.

Every GenAI task starts with a stable flat definition/setup structure:

```text
genai/<business-task>/
├── prompts.py                      # Prompt definitions/builders
├── schemas.py                      # AI input/output schemas
└── llm.py                          # Model construction and binding only
```

Do not merge prompts, schemas, or model construction into a capability
implementation to save files. Add a capability-named module such as
`classifier.py`, `generator.py`, `extractor.py`, or `resolver.py` when the GenAI
task implements the corresponding application port. It invokes the handle from
`llm.py` and translates inputs, outputs, and failures; it does not define prompts
or construct the model. Never use generic `adapter.py` or `service.py` by
default. For an agent harness, add `agent.py`; it imports the model from `llm.py`
rather than replacing that module.

Use `genai/<business-task>/` such as `genai/email_classification/`. Always name
model construction `llm.py`, never `model.py`; add `agent.py` only for agent
harness construction. Read [references/ai.md](references/ai.md) for the required
internal shape.

## Centralized adapter ownership

Place concrete external-system implementations under root `adapters/`, grouped
by technology or provider, for example `adapters/aws/s3_raw_email_store.py` and
`adapters/aws/sqs_consumer.py`. This includes broker polling, wire-envelope
translation, acknowledgement, visibility, remote HTTP clients, object stores,
and vendor SDK wrappers.

Following the application-wide flat-first rule, keep a provider package flat
while it has only a few cohesive modules. When one provider area grows
independently, promote only that area to a subpackage, for
example `adapters/aws/sqs/{consumer,serialization}.py` and
`adapters/aws/s3/raw_email_store.py`. Do not pre-create nested provider trees.

Do not create a root `messaging/` package for SQS, Kafka, or another concrete
broker. Put technology-neutral contracts needed by business execution in
`ports/`; keep broker-specific delivery contracts private to the relevant
adapter when the application layer never sees them.

`api/`, `db/`, and `genai/` are deliberate first-class technical boundaries and
remain at the root even though they play adapter roles in a broad hexagonal
sense. `adapters/` owns all other concrete integrations. Do not colocate a
concrete adapter inside `application/`, `domain/`, or `ports/`.

## Dependency rules

The desired direction is:

```text
main                  -> bootstrap
api/adapter consumer  -> application action -> domain + ports
bootstrap             -> adapters + db + genai + application
adapters/db/genai     -> ports
```

Application code must not import `bootstrap`, `api`, consumers, `adapters`, `db`,
or `genai`. Domain and ports must not know FastAPI, LangChain, boto3, Kafka, SQL
sessions, or telemetry SDK details. Bootstrap is the only ordinary runtime
location that selects concrete implementations for ports.

Use ports primarily for I/O, remote, nondeterministic, expensive, or externally
controlled effects. Do not wrap deterministic parsing, ETA calculation,
correlation, formatting, or pure business rules in Protocols; those belong in
`domain/` or the owning application action. A repository may be the accepted
persistence boundary when another abstraction adds no testability or
substitution value.

Name ports after the capability the caller needs, not the current implementation:
prefer `ports/email_classifier.py` and `EmailClassifier` over
`classification_model.py` and `ClassificationModel`. Put stable failure
contracts beside the port so application code never imports adapter-defined
exceptions.

## Naming and shared code

- Prefer precise names such as `email_parsing.py`, `workbook_store.py`, or
  `case_correlation.py` over `utils.py`, `helpers.py`, `common.py`, or
  `misc.py`.
- Put an error beside its owning contract, initially in the same module when it
  is small. Extract `errors.py` only when the owned error taxonomy has enough
  content or reuse to justify a separate file. Errors always remain under their
  owning `domain/`, `application/`, `ports/`, `adapters/`, or `genai/` boundary;
  never create root, `core/errors.py`, or `common/errors.py` collections.
- Keep errors and static values beside the boundary that owns their meaning:
  business failures in `domain/`, use-case failures in `application/`, AWS failures
  in `adapters/aws/`, and AI failures in the relevant `genai/` task. Translate
  adapter/GenAI failures to a port-owned error before they reach application code.
- Do not create root `constants.py` or `core/constants.py`. Put true invariants
  beside their domain, application, adapter, or GenAI owner; prefer enums, literals,
  or value objects when they express the concept better. Values that can vary by
  environment or deployment belong in `config/`, not constants.
- Promote code to `shared/` only after real reuse exists and the abstraction has
  one stable meaning. Shared code must still have a precise subpackage name.
- A deployable service must not import another deployable's private package.
  Move truly shared contracts or deterministic logic into an internal library.
- Keep external names consistent across distribution, directory, import
  package, CLI, runtime service name, container configuration, and telemetry.

## Output and implementation behavior

For a design or review, provide:

1. How the canonical shape applies and any explicit, justified exception.
2. A target tree containing only relevant directories.
3. A short dependency map and ownership notes for ambiguous files.
4. Current violations, migration risks, and the smallest coherent migration
   sequence.

For implementation, state how the canonical shape applies before broad file
movement. Move one coherent boundary or business action at a time, update imports and entry points,
and run focused tests after each meaningful slice. Preserve behavior during a
structure-only refactor; do not mix business redesign into file movement unless
the user explicitly requests both.

## Related skills

- Use `python-uv-workspace-monorepo` for repository members, `pyproject.toml`,
  workspace dependency isolation, lockfiles, and Docker build layout.
- Use `settings-config` for detailed settings/secrets implementation.
- Use `sqlmodel-alembic-db-layer` for SQLModel, repositories, sessions, and
  Alembic structure.
- Use `observability` for actual OpenTelemetry implementation or audit.
