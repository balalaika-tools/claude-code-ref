# Boundaries and dependency direction

## The core rule

Hexagonal structure means business logic knows the conversation shape, not the
technology conducting it.

```text
main ──> bootstrap ──> adapters/db/genai ───┐
                    └─> application actions ├──> ports <── domain
API/adapter consumer ─> application actions ┘
```

The composition root is the only ordinary runtime location that should know
which concrete implementation satisfies a port. Adapters, database
repositories, and GenAI implementations import their ports; ports, domain, and
application code never import those outer packages.

## Flat-first growth across boundaries

Use the fewest cohesive `.py` modules inside every owning boundary. Keep a small
set—roughly three to five related modules—flat until one narrower area has enough
content, independent change, distinct test setup, or naming pressure to justify
a subpackage. The number is a review signal, not a quota.

Do not create separate modules merely for one class, exception, constants group,
schema, or private helper. Keep small definitions with their owner and extract
them only after they develop independent weight. Conversely, do not combine
unrelated responsibilities into a catch-all to optimize file count. Root
boundaries such as `application/`, `adapters/`, and mandatory `genai/` still express
ownership even when they each contain only one module. GenAI tasks are the
explicit stable-structure exception: keep separate `prompts.py`, `schemas.py`,
and `llm.py`, plus a capability implementation when needed. Do not collapse
those responsibilities merely to reduce `.py` count.

## When a port earns its cost

`ports/` is not a dump folder for interfaces. A port represents a capability
that the application needs but an I/O, remote, nondeterministic, expensive, or
externally controlled boundary fulfills.

Introduce a port when at least two of these are true:

1. The dependency is remote, nondeterministic, expensive, or controlled by an
   external system.
2. Its failure modes materially affect business behavior and need deterministic
   tests.
3. Multiple implementations, local fakes, or future substitution have concrete
   value.

Typical ports include an LLM invocation, remote HTTP client, S3/object store,
message publisher, clock used in business decisions, workbook builder, or
browser portal. Pure validation, formatting, parsing, and ordinary in-memory
calculation do not need ports.

Prefer:

```text
ports/raw_email_store.py
ports/email_classifier.py
ports/ticket_repository.py          # Only when a DB port adds real isolation
```

Do not create:

```text
ports/email_parser.py
ports/eta_calculator.py
ports/correlation_service.py
```

when those behaviors are deterministic and in-process. Put them in `domain/` or
the owning application action and test them directly.

Name a port after the capability requested by its caller, not an implementation
assumption. `EmailClassifier` permits rule-based, LLM, hybrid, and remote API
implementations; `ClassificationModel` unnecessarily assumes a model.

A fixed database accessed through a cohesive repository layer often does not
need a second Protocol above it. Add one only if the application action gains
real isolation or alternative implementations—not for architectural symmetry.

## Contract ownership

A port owns both success and failure contracts:

```python
class WorkbookStoreError(RuntimeError):
    pass


class WorkbookStore(Protocol):
    async def store(self, workbook: BuiltWorkbook) -> StoredWorkbook: ...
```

Concrete adapters raise contract-level errors, translating boto3, HTTP,
LangChain, Kafka, filesystem, or vendor exceptions at the boundary. They may
define private integration errors below `adapters/` or `genai/`, but those errors
must not cross the port. Application code may catch `WorkbookStoreError`; it must
not catch `S3ReadError` or another implementation-owned error.

Keep typed inputs and outputs at the boundary. Avoid weak contracts such as
`dict[str, Any]`, unvalidated JSON, or raw provider responses when a stable
business shape exists.

## Centralized ports and adapters

Keep application-facing ports under root `ports/` and concrete integrations
under root `adapters/`. Do not colocate concrete S3, SQS, Kafka, browser, remote
HTTP, or vendor SDK implementations inside `application/` or a business-named
package. Group adapter modules by technology or external system when that makes
ownership clearer, such as `adapters/aws/` or `adapters/salesforce/`.

The generic flat-first rule applies here too. For three to five cohesive provider
modules, prefer
`adapters/aws/sqs_consumer.py`, `sqs_serialization.py`, and
`s3_raw_email_store.py`. When SQS or S3 develops several independently changing
modules, promote only that slice to `adapters/aws/sqs/` or `adapters/aws/s3/`.
Folder depth follows demonstrated growth; do not scaffold nested providers in
advance.

Use root `genai/` for every GenAI implementation and root `db/` for persistence;
these are deliberate specialized adapter families. HTTP remains in root `api/`.
Do not create a parallel root `messaging/`: broker-specific consumers, clients,
serialization, acknowledgement, and visibility behavior belong in
`adapters/<broker-or-provider>/`.

A port owns its stable success and failure contract. Broker delivery types that
never cross into application code are private adapter contracts and do not need to
be promoted to root `ports/`.

## Folder responsibilities

### `bootstrap/`

Allowed:

- Construct settings-derived policies and dependencies.
- Create engines, clients, GenAI implementations, repositories/factories,
  consumers, and application actions.
- Own application lifespan, task groups, supervisors, startup probes, and
  deterministic shutdown.
- Return a typed runtime dependency container.

Not allowed:

- Business classification, authorization, routing, or state-transition rules.
- Provider-specific parsing that belongs in an adapter.
- Repository queries.

Split a large runtime by construction concern, not arbitrary line count. For
example, `runtime.py`, `app.py`, and `supervisor.py` have distinct lifecycle
responsibilities.

### `config/`

`settings.py` validates non-secret configuration. `secrets.py` resolves secret
material and returns a typed value. Configuration describes policy; it does not
execute business work or instantiate the whole runtime graph.

### `core/`

Keep `core/` absent by default. Create it only for small, stable,
dependency-light primitives already needed across several boundaries, such as
application context or shared identity types. Errors and constants never belong
here. Do not place settings here when the standard is `config/`, and do not let
`core/` become a synonym for helpers or “important code.”

### `application/`

Application actions coordinate domain decisions and ports. They may accept
repositories or ports through typed constructor arguments. They must not read
global settings, environment variables, app state, or SDK singletons directly.
Independent business actions live in `application/`. Do not introduce root
`pipeline/`, `use_cases/`, `workflows/`, or `operations/` peers. Ordered stage,
command/query, or workflow machinery is optional below `application/` and must
reflect real execution semantics.

For an AI-backed classification action, this layer still contains substantive
use-case code: input acquisition, deterministic eligibility/policy, the decision
to request a classifier candidate, interpretation into a business result,
persistence/publication, and retry, defer, or handoff policy as applicable. The
GenAI implementation only fulfills the external classifier capability.

### Adapters and technical boundaries

Adapters translate technology-specific input, output, and failures into the
application's contracts. Database repositories are the only ordinary place
that executes queries. Queue consumers under `adapters/` translate delivery,
serialization, acknowledgement, and visibility semantics and call an application
action; they do not implement classification or state rules. GenAI code follows
the same inward dependency rule but lives under mandatory root `genai/`.

### `observability/`

Contains logging setup, trace/metric helpers, semantic conventions, propagation,
and SDK integrations. Application and domain packages may call a narrow telemetry
helper when instrumentation cannot be automatic, but observed data must not
control business decisions. Avoid importing application actions into observability.

When several deployables share the same generic provider lifecycle,
propagation, redaction, or structured-logging policy, that stable mechanics may
move to an internal observability library. Service vocabulary, instruments,
business event names, outcomes, and instrumentation adapters remain local. See
`shared-libraries.md` and use the `observability` skill for the shared API.

## Context versus state

When immutable execution context is genuinely shared across boundaries, use
`core/context.py` for tenant, actor, authorization claims, correlation
identifiers, or allowlisted baggage. Pass it explicitly.

Do not confuse it with mutable workflow state. Business checkpoint state belongs
to the application action that owns it; LangGraph state always belongs below the
relevant root `genai/<task>/graph/` package.

## Errors and constants follow ownership

Keep errors beside the boundary that gives them meaning. The following
`errors.py` locations are available when an owned taxonomy has enough content to
earn a file; otherwise keep a small error in its owning module:

- `domain/errors.py` for business invariant and domain-state failures;
- `application/errors.py` or an action-local `errors.py` for use-case orchestration
  failures;
- `ports/<capability>.py` for stable external failure contracts visible to
  application code;
- `adapters/aws/errors.py` or a narrower provider package for private AWS
  failures that are translated before crossing a port;
- `genai/errors.py` or `genai/<task>/errors.py` for private AI failures that are
  translated before crossing a port.

Do not create root, `core/errors.py`, or `common/errors.py` collections, even for
a shared base or taxonomy. Keep shared business failures in `domain/`,
cross-action use-case failures in `application/`, stable external failure
contracts in `ports/`, and implementation-private failures in their adapter or
GenAI owner.

Apply the same ownership rule to static values. Do not create root
`constants.py`, `core/constants.py`, or another global collection of unrelated
values:

```text
Business invariant/static value     -> domain/ or its owning module
Use-case-specific invariant         -> application/ or its owning action
AWS/provider-specific static value  -> adapters/<provider>/
LLM/agent-specific static value     -> genai/<task>/
Environment/deployment value        -> config/
```

A constant is invariant in code or domain semantics. A model ID, queue URL,
region, timeout, retention period, or concurrency limit that can vary by
environment is configuration. Prefer an enum, literal, or value object over a
`constants.py` module when it expresses the concept more precisely.

## Avoid utility gravity

Do not establish a generic `utils/`. Place behavior by meaning:

- retry policy near the boundary that retries;
- serialization near the transport or contract;
- time calculation in the domain or action that defines time semantics;
- cross-action use-case errors in `application/errors.py` and shared business
  failures in `domain/errors.py`, never in `core/` or `common/`;
- small private helpers in the module that owns the behavior.

When a helper becomes genuinely reused, extract a precisely named module or
package such as `email_normalization.py`, `trace_propagation.py`, or
`country_matching.py`.

## Dependency audit

Before accepting a structure, search imports and verify:

- domain and ports do not import adapters, bootstrap, API, DB, GenAI, SDKs, or
  ORM sessions;
- application actions do not import concrete adapters, DB, or GenAI packages;
- API and adapter consumers call public application entry points;
- adapters, DB repositories, and GenAI implementations depend inward on ports;
- ports represent I/O or nondeterministic capabilities rather than deterministic
  parsers, calculators, formatters, or business rules;
- port names describe caller needs rather than current implementation technology;
- bootstrap is the composition root and is not imported by business code;
- no concrete broker implementation exists in a root `messaging/` package;
- every LLM, agent, prompt, AI schema, tool, or graph lives below root `genai/`;
- every GenAI task keeps separate prompt, schema, and model-construction modules,
  with capability implementations free of those definitions;
- no root or `core/constants.py` mixes values from unrelated boundaries, and
  deployment-varying values live in `config/`;
- no root, `core/errors.py`, or `common/errors.py` centralizes failures from
  different owners;
- small packages remain flat across every boundary, without speculative
  file-per-class or one-file subpackages;
- no deployable imports another deployable's private package;
- tests can replace costly boundaries with small typed fakes without patching
  SDK internals.
