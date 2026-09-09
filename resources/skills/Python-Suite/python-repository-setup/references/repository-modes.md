# Repository Modes and Boundaries

Read this reference when choosing between a single project and a uv workspace,
naming workspace roots, deciding whether code earns a shared package, or adding
and moving members.

## Single deployable

Keep one ordinary installable project at the repository root:

```text
repo/
├── pyproject.toml
├── uv.lock
├── .python-version
├── .pre-commit-config.yaml
├── .env.example
├── Dockerfile
├── compose.yaml
├── src/
│   └── my_service/
└── tests/
```

Do not place the import package directly at `src/`. Do not introduce
`services/`, `libs/`, or `[tool.uv.workspace]` until the repository contains
multiple independently built artifacts.

## Workspace layout

Use a virtual uv workspace for multiple independently deployable artifacts:

```text
repo/
├── pyproject.toml
├── uv.lock
├── .python-version
├── .pre-commit-config.yaml
├── .dockerignore
├── services/
│   ├── api/
│   │   ├── pyproject.toml
│   │   ├── Dockerfile
│   │   └── src/api/
│   └── worker/
│       ├── pyproject.toml
│       ├── Dockerfile
│       └── src/worker/
└── libs/
    └── company_observability/
        ├── pyproject.toml
        ├── src/company_observability/
        └── tests/
```

Use plural glob members such as `services/*` and `libs/*`. An explicit list can
silently exclude a newly added member.

## Naming workspace roots

- **`services/`** contains every independently deployable unit: API, worker,
  queue consumer, scheduled job, CLI, or separately shipped frontend build.
  Use it even when no HTTP service exists. Do not add a parallel `apps/` root
  for the same category.
- **`libs/` or `packages/`** contains cohesive reusable internal packages with
  no deployable of their own. Pick one name and use it consistently. These
  packages are consumed with `{ workspace = true }` and do not get Dockerfiles.

The directory names are semantic conventions, not uv requirements.

## Before creating a shared library

A member adds a public contract, dependency edge, test surface, and migration
cost. Create one only when the code has cohesive meaning outside a single
deployable and concrete reuse: normally two current consumers, or a stable
protocol/client/schema boundary with a real compatibility or dependency-
isolation reason. Hypothetical reuse is insufficient.

Check that:

- it removes duplicated behavior or publishes one stable contract, rather than
  merely grouping similar syntax;
- its API does not import a service's private settings, application, domain,
  bootstrap, or tests;
- its dependencies suit every consumer and do not pull a service framework or
  vendor stack into unrelated images;
- it has one reason to change and will not become a `common`, `shared`, `utils`,
  or organisation-wide dumping ground;
- consumers can migrate independently through additive APIs when an atomic move
  is unsafe;
- the boundary materially improves dependency direction, consistency, testing,
  or release safety.

Good candidates include stable vendor clients, shared wire/schema contracts,
database metadata consumed by several members, and generic observability
plumbing. For observability, shared provider lifecycle, propagation, redaction,
and logging processors may belong together; service span names, business
metrics, event vocabulary, and outcome decisions remain service-local.

Keep a candidate inside its service when it has one consumer, no stable
independent contract, or different business semantics despite similar code.
Two processes that always deploy as one release unit also need not be split.

## Internal library shape

Every library uses `src/<import_package>/`, keeps tests beside the member, and
exposes a small intentional public API. Start with the fewest cohesive modules.
Do not copy a deployable's `main.py`, `bootstrap/`, `application/`, `adapters/`,
and `config/` shell into a non-deployable package.

Introduce a subpackage only when a narrower capability has several cohesive
modules, changes independently, needs distinct test setup, or creates real
naming pressure. Avoid file-per-class layouts, one-file subpackages,
speculative registries/factories, and generic `common`, `shared`, `utils`, or
`core` packages. Use `python-service-architecture` for detailed module
ownership, dependencies, exports, tests, and consumer migration.

## Adding or moving a member

1. Apply the shared-library admission test; keep code service-local if it does
   not earn the boundary.
2. Create `services/<name>/` or the selected library root with its own
   `pyproject.toml`, `src/<package>/`, tests, and only its own dependencies.
3. For an internal library consumer, declare the package in dependencies and
   add `<library> = { workspace = true }` under `[tool.uv.sources]`.
4. Confirm workspace globs include the member.
5. Inspect pre-commit and CI for explicit roots, filters, mypy paths, pytest
   collection, and coverage sources; update only affected scopes.
6. Run `uv lock` at the root, then package-scoped syncs for the new member and
   consumers to expose sibling dependency leakage.
7. Run the member's tests and focused contract/startup tests for each migrated
   consumer.
8. Add a Dockerfile only for a deployable. Libraries enter images through a
   consumer's workspace-root build context.
