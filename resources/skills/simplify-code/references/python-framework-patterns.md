# Conditional Python framework patterns

Read only the sections matching detected repository dependencies and versions. Repository configuration and documentation override this guidance.

## Asyncio and task runners

- Preserve scheduling, ordering, cancellation, timeout, retry, idempotency, and exception aggregation.
- Avoid wrapper tasks that only await one coroutine, unless they establish naming, context, instrumentation, ownership, or lifecycle.
- Do not replace sequential awaits with concurrency without tests for ordering, load, and partial failure.
- Preserve worker registration and import side effects used by Celery, Dramatiq, RQ, or similar systems.

## FastAPI, Pydantic, and dependency injection

- Treat dependency providers as trust, lifecycle, caching, or test boundaries until disproved.
- Preserve validation, aliases, serialization modes, response schemas, status codes, and OpenAPI-visible contracts.
- Check installed Pydantic major version before proposing model, validator, or serialization syntax.
- Do not remove apparently unused routes, dependencies, or models based only on Python references; decorators and schema generation are registration mechanisms.

## Django and ORMs

- Treat model managers, querysets, fields, signals, app configuration, migrations, and admin registrations as framework-discovered surfaces.
- Preserve query count, laziness, transaction scope, locks, relationship loading, and exception behavior.
- Do not replace query construction with an in-memory simplification or delete migrations.
- Verify factory/repository layers for tenancy, authorization, transaction, and query-policy ownership before collapsing them.

## SQLAlchemy

- Preserve session ownership, flush/commit timing, identity-map behavior, transaction boundaries, eager/lazy loading, and generated SQL shape where relevant.
- Keep adapters that isolate sync/async sessions, external schemas, or database-specific behavior.
- Measure query changes and exercise rollback/error paths for structural refactors.

## Pytest

- Parameterize near-identical cases only when the table remains easier to understand than separate scenario names.
- Extract fixtures for shared setup with a stable meaning; do not build a hidden testing DSL.
- Keep test doubles that establish a real dependency seam, even when production has one implementation.
- Avoid mocks of private call order when observable assertions can support safer refactoring.

## Dataclasses, attrs, TypedDict, and Pydantic models

- Keep one representation per meaningful boundary; do not force runtime and wire/storage models into one type when their validation or ownership differs.
- Prefer a simple built-in representation for short-lived local data with no invariant.
- Do not introduce a data class only to reduce parameter count, or remove one that makes invalid states harder to express.

## Typing and protocols

- Preserve types that document or enforce public contracts and variance.
- Remove a protocol only after checking production implementations, test doubles, plugins, and downstream consumers.
- Avoid runtime wrappers that exist solely to satisfy a type checker when a direct annotation or narrow cast matches repository policy.
