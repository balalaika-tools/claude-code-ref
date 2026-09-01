# Internal shared-library structure

Use this reference for a non-deployable Python package under `libs/` or
`packages/`, whether creating it, extracting it from services, or modularizing
an existing member. The `python-uv-workspace-monorepo` skill owns workspace
admission, `pyproject.toml`, lockfile, scoped-install, and Docker mechanics.
This reference owns the package's internal modules, dependencies, public API,
tests, and migration boundaries.

## A library is not a smaller service

A library publishes a cohesive capability to its consumers. It normally has no
process entry point, runtime composition root, deployment settings, background
supervisor, API, or infrastructure lifecycle of its own. Do not copy the
canonical service tree into it:

```text
libs/<distribution-name>/
├── pyproject.toml
├── src/
│   └── <import_package>/
│       ├── __init__.py
│       └── <cohesive modules>
└── tests/
```

Create `application/`, `domain/`, `ports/`, `adapters/`, `bootstrap/`, `api/`,
or `config/` inside a library only when those words describe real independent
responsibilities in that library. They are not default folders. A package that
has a `main.py`, owns long-running resources, or ships independently may be a
service or CLI and belongs under `services/`, even if other members import some
of its code.

## Confirm the boundary before arranging it

Foldering cannot rescue an unjustified shared abstraction. Before moving code,
identify:

- current consumers and the public behavior each needs;
- the one stable meaning shared by those consumers;
- inputs, outputs, failures, and compatibility obligations;
- external dependencies and whether every consumer should inherit them;
- service-specific policy that must stay with its owner;
- the reason this package can evolve without importing a deployable's private
  implementation.

Ordinarily require demonstrated use by at least two current members. A single-
consumer package can still be valid when it is an independently valuable
protocol/client/schema boundary with a concrete compatibility reason, but do
not split for hypothetical future reuse. Similar syntax with different business
meaning is not reuse.

Prefer a precise capability name such as `edm_client`, `db_models`,
`workflow_contracts`, or `company_observability`. Avoid library distributions
or import packages named only `common`, `shared`, `utils`, `helpers`, `core`, or
`base`.

## Flat first

Begin with the fewest cohesive modules directly under the import package:

```text
src/edm_client/
├── __init__.py
├── client.py
├── auth.py
├── models.py
├── errors.py
└── rate_limit.py
```

This is intentionally less prescriptive than a backend service structure.
Module names follow the capability's own concepts. A small dataclass, exception,
or private helper stays with its owner; do not create one file per class or a
subpackage for every noun.

Introduce a nested package only when one narrower slice:

- contains several cohesive modules;
- changes for a different reason from its siblings;
- has its own external dependency or test setup;
- owns a distinct public sub-API; or
- creates real naming collisions or navigation pressure while flat.

Promote only that slice:

```text
src/vendor_client/
├── __init__.py
├── models.py
├── errors.py
├── auth/
│   ├── credentials.py
│   └── tokens.py
└── transport/
    ├── session.py
    └── retry.py
```

Do not pre-create `interfaces/`, `implementations/`, `factories/`, `plugins/`,
`schemas/`, or `types/` packages for one implementation. A large mixed module
is not preferable to folders; the target is the minimum coherent set, not the
minimum number of files.

## Organize by capability and change ownership

Useful internal shapes depend on what the library publishes:

- A client library may separate authentication, transport, retry/rate limiting,
  wire models, and public errors.
- A schema/model library may group models by stable business capability once a
  flat set becomes difficult to navigate; it must not acquire repositories,
  sessions, migrations, or service orchestration.
- A contract library may group versioned wire contracts, serializers, and
  compatibility validation, while adapters remain with consumers.
- An observability library may own generic providers, spans, propagation,
  resource helpers, structured-logging processors, redaction, and trace/log
  correlation. Business span names, metrics, log events, and outcomes remain
  with each service. Use the `observability` skill for the exact lifecycle and
  logger contract.

Do not mix unrelated horizontal concerns into one organisation library. A
package containing logging, HTTP retries, date helpers, database types, and
business constants has no cohesive owner and will couple every consumer to
unrelated dependencies.

## Dependency direction

An internal library:

- never imports a deployable's source package, settings class, bootstrap,
  application action, domain implementation, or tests;
- accepts configuration as explicit typed values, a library-owned dataclass, or
  a narrow protocol rather than reading service environment variables;
- does not choose deployment policy or construct resources it cannot dispose;
- keeps optional/framework-specific integrations separate from its dependency-
  light core when only some consumers need them;
- avoids cycles between workspace libraries and avoids a foundational package
  depending on a higher-level business package;
- declares every runtime dependency it imports, even if the shared developer
  environment happens to provide it through another member.

Prefer a small stable data or protocol boundary over passing a service's large
settings/domain object into the library. Translate at the consumer boundary.

## Public API and compatibility

Treat the import surface as a contract. Keep `__init__.py` small and deliberate:
re-export the common supported entry points, not every class and internal
helper. Consumers should normally import public package symbols rather than
private modules whose layout may change.

Use leading-underscore modules or documented internal packages when useful, but
do not rely on naming alone: tests and import searches must show that consumers
do not reach into implementation details. Avoid mutable module-global state and
import-time side effects. When process state is necessary, expose explicit
construction/configuration and deterministic disposal.

Do not add configuration flags to preserve every difference discovered during
extraction. If consumers require materially different semantics, keep thin
service-local adapters or leave the behavior local until a stable contract
emerges.

## Tests

The library owns tests under `libs/<library>/tests/`. A small deterministic
suite may stay flat. Once it has distinct execution profiles, apply the profile-
first structure in `testing.md`.

Test at three levels only when each proves a real boundary:

- library unit tests prove deterministic public behavior, failures, and state
  lifecycle;
- library integration tests prove concrete external protocols owned by the
  library against disposable infrastructure;
- consumer contract tests prove that each service's adapter/configuration still
  matches the shared public API.

Do not copy every library test into every consumer. Conversely, library tests
cannot prove service startup, dependency closure, configuration mapping, or
shutdown order; keep those focused tests with the consumer.

## Extraction and modularization sequence

1. Inventory candidate code, imports, current consumers, behavior differences,
   settings, dependencies, tests, and lifecycle ownership.
2. Define the smallest shared public contract and explicitly list what remains
   service-local.
3. Create or reshape the library around that contract, initially flat, with
   focused tests.
4. Keep compatibility re-exports or thin service-local facades when consumers
   cannot migrate atomically.
5. Migrate one consumer at a time; run the library tests plus that consumer's
   contract, startup/lifecycle, import, and type checks.
6. Introduce narrower subpackages only where the extracted responsibilities now
   demonstrate independent ownership.
7. Remove duplicated code and transitional imports only after all intended
   consumers have moved.

Preserve behavior during a structure-only extraction. Do not standardize
business semantics merely because the implementations now sit nearby.

## Review questions

- Does the package have current reuse or a concrete independent compatibility
  boundary?
- Can its responsibility be described without “and” joining unrelated areas?
- Does it avoid service-private imports, environment reads, and deployment
  ownership?
- Is the dependency footprint appropriate for every consumer?
- Are the modules flat while cohesive and nested only where ownership justifies
  the navigation cost?
- Is the public API intentional, with consumers kept away from private layout?
- Are service-specific policies and business decisions still service-local?
- Can the package and every consumer be installed and tested independently?
- Is migration additive and consumer-by-consumer rather than a repository-wide
  rewrite for symmetry?
