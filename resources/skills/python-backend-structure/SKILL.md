---
name: python-backend-structure
description: >-
  Design, scaffold, refactor, or review the internal folder structure of a
  Python backend service or reusable internal library, including FastAPI
  applications, workers, event consumers, scheduled jobs, business workflows,
  AI-enabled services, and packages under `libs/` or `packages/`.
  Standardize business execution under application, technology-neutral contracts
  under ports, concrete integrations under adapters, and all GenAI code under
  a root genai package, with clear bootstrap, API, persistence, configuration,
  observability, and test-suite boundaries. Use when deciding where backend code
  or its unit, integration, contract, and end-to-end tests belong, or when
  standardizing package layouts. Do not use for uv workspace/Docker organization
  alone or for database-layer mechanics alone.
---

# Python Backend Structure

Enforce the canonical structure below across Python backend deployables. Use the
lighter shared-library structure for non-deployable packages; never copy a
service shell into a library. Ownership and dependency direction take priority
over cosmetic symmetry.

## Required discovery

Before proposing or changing a structure:

1. Inspect the actual package tree, entry points, imports, tests, and deployment
   process. For tests, inspect collection configuration, markers, fixture scope,
   support-module imports, external-resource requirements, pre-commit/pre-push
   scopes, and CI selection. Do not infer architecture or test type from
   filenames alone.
2. Classify the member as an independently deployable service or a
   non-deployable internal library; do not infer that from its current folder.
3. For a service, identify meaningful business actions, outcomes, and process
   types. For a library, identify its public capability, current consumers, and
   compatibility contract.
4. Identify external effects and lifecycle resources owned by the member:
   database, HTTP clients, storage, queues, browser, files, LLMs, telemetry, and
   clocks. A library should own only effects intrinsic to its published capability.
5. Trace current dependency direction and locate service-private imports,
   concrete external implementations, and consumer reach-through into private
   library modules.
6. Preserve repository conventions unless changing them provides a clear,
   stated benefit. Never reorganize unrelated services merely for symmetry.

## Reference routing

For a deployable service, read:

- [references/templates.md](references/templates.md) for the canonical tree and
  placement map;
- [references/boundaries.md](references/boundaries.md) for dependency,
  ownership, ports, errors, constants, and package-growth rules;
- [references/testing.md](references/testing.md) for test classification,
  fixtures, markers, CI, and migration.

For an internal library, read
[references/shared-libraries.md](references/shared-libraries.md) and
[references/testing.md](references/testing.md) instead; the library reference is
authoritative wherever service rules would imply extra folders. Load only the
additional references that apply:

- Read [references/api-and-workers.md](references/api-and-workers.md) for an HTTP
  API, worker, scheduled process, queue/Kafka/SQS consumer, or hybrid service.
- Read [references/ai.md](references/ai.md) when the package invokes an LLM,
  builds an agent or graph, exposes AI tools, or has prompts/model middleware.
- Read [references/modularization.md](references/modularization.md) when splitting
  existing modules, migrating an established service, or reviewing structure
  that has grown unclear.
- Keep [references/shared-libraries.md](references/shared-libraries.md) loaded
  when extracting service code into `libs/*` or reorganizing an existing library.

## Enforced invariants

These are requirements, not optional examples:

1. **Business execution lives in `application/`.** Use it for executable
   business-value actions, use cases, and orchestration. Do not create root
   `pipeline/`, `use_cases/`, `workflows/`, `operations/`, generic service
   catch-alls, or root business-capability packages as alternatives. A true
   transport-only or health-only process is an explicit exception that must be
   explained.
2. **Dependencies point inward.** Application code never imports `bootstrap`,
   `api`, consumers, `adapters`, `db`, or `genai`; domain and ports never know
   framework or SDK details. `bootstrap/` is the ordinary runtime composition
   root. See `boundaries.md` for the complete dependency and contract rules.
3. **Concrete integrations have stable owners.** HTTP belongs in `api/`,
   persistence in `db/`, and all other non-GenAI integrations in root
   `adapters/`, grouped by provider or technology. Do not create root
   `messaging/` or place concrete integrations in business packages.
4. **Every GenAI concern lives in root `genai/`.** This includes every LLM,
   agent, prompt, AI schema, tool, graph, model binding, and AI middleware.
   Application code sees a typed port and business result. Every GenAI task
   keeps model construction in an `llm.py` factory; an agent adds an `agent.py`
   factory; `bootstrap/` calls those factories with resolved configuration and
   dependencies. An application-facing implementation is named after its port
   capability. Read `ai.md` for the enforced internal shape and ownership rules.
5. **Package growth is flat-first.** Start with the fewest cohesive modules and
   introduce only the narrower subpackage whose independent ownership, change,
   setup, or naming pressure justifies it. Do not create file-per-class layouts,
   speculative extension points, or catch-alls.
6. **Names, errors, constants, and contracts follow ownership.** Ports describe
   caller-needed external capabilities, not implementations or deterministic
   in-process logic. Never create global `utils`, `common`, `shared`, root
   `constants.py`, or root/`core`/`common` error collections. Translate concrete
   failures to the port-owned contract before application code sees them.
7. **Tests belong to their member and actual execution profile.** Keep them
   beside the member's `src/`. When multiple profiles exist, classify them as
   `unit`, `integration`, `contract`, or `e2e` by what they execute, then by
   behavioral owner. Fixtures and support code stay at the narrowest shared
   scope; markers and CI selectors must match the profiles.
8. **Internal libraries use the library shape.** They do not acquire a service
   shell for symmetry, import deployable-private code, or become generic shared
   dumping grounds. Promote code only after real reuse or a concrete independent
   compatibility boundary exists.
9. **All Python imports are absolute.** Always import through the full package
   path in production code, tests, scripts, migrations, and support modules.
   Never use relative imports, including single-dot imports within one package.

Create only directories required by the current member. The canonical tree is
a placement policy, not permission to add empty packages.

## Output and implementation behavior

For a design or review, provide:

1. How the canonical shape applies and any explicit, justified exception.
2. A target source and test tree containing only relevant directories.
3. A short dependency map and ownership notes for ambiguous source and test
   files, including each test's execution profile when it is not obvious.
4. Current violations, fixture/CI migration risks, and the smallest coherent
   migration sequence.

For implementation, state how the service or library shape applies before broad
file movement. Move one coherent boundary, business action, library capability,
or test profile at a time; update imports, entry points, consumers, fixture
scope, markers, pre-commit paths/filters, and CI selectors; and run focused tests
after each meaningful slice. Preserve behavior during a structure-only refactor;
do not mix business redesign into file movement unless the user explicitly
requests both.

## Related skills

- Use `python-uv-workspace-monorepo` to decide whether shared code earns a
  workspace member and for `pyproject.toml`, dependency isolation, lockfiles,
  scoped installs, root pre-commit/pre-push tooling, and Docker build layout.
- Use `settings-config` for detailed settings/secrets implementation.
- Use `sqlmodel-alembic-db-layer` for SQLModel, repositories, sessions, and
  Alembic structure.
- Use `otel-observability` for actual OpenTelemetry implementation or audit,
  including the lifecycle and logging contract of a shared observability library.
