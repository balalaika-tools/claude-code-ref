---
name: python-uv-workspace-monorepo
description: >-
  Structure or review a multi-service Python monorepo with a virtual uv
  workspace root, one `pyproject.toml` per deployable under `services/`, one
  per internal library under `libs/` or `packages/`, and workspace sources for
  internal dependencies. Standardize centralized Ruff, pytest, coverage, mypy,
  and pre-commit/pre-push tooling; exact Python and uv versions across local
  development, CI, and Docker; one shared lockfile; scoped per-service installs;
  and lean multi-stage production images. Use when deciding whether each service
  needs its own `pyproject.toml`, splitting root dependencies, creating or
  reviewing `.pre-commit-config.yaml`, scaffolding uv workspaces and Dockerfiles,
  deciding whether code earns a shared internal package, wiring shared packages,
  or preventing sibling-service dependencies and dev tools from entering an image.
---

# Python Monorepo: uv Workspaces Across Services

Apply this rule first; everything else in this skill follows from it:

> **Independently deployable = its own `pyproject.toml`. Genuinely reusable
> internal code = its own `pyproject.toml`. The root `pyproject.toml` declares
> the workspace and repo-wide development tooling, but no runtime dependencies
> any service ships.**

This applies once a repository holds more than one independently built artifact
(more than one Dockerfile, more than one Lambda, more than one deployed
process). A single-service repository does not need a workspace; give it one
plain `pyproject.toml` at its root and stop reading here.

## Naming The Top-Level Directory: `services/` vs `libs/`/`packages/`

The workspace mechanics in this skill — one `pyproject.toml` per member, glob
workspace members, one shared lockfile, `--package`-scoped installs — work
identically no matter what the top-level directories are named. The names
themselves are a semantic choice, not a `uv` requirement, and are worth
getting right before laying out the repo:

- **`services/`** — every independently deployable unit in the repo: an API,
  a worker, a queue consumer, a scheduled batch job, a CLI, a frontend build —
  whatever it is, if it ships as its own deployable it's a service. Use this
  name for all of them, even a worker-only repo with no HTTP API in sight —
  it's still a deployable service unit. Don't introduce an `apps/` directory
  alongside it; every "things that get built and deployed on their own"
  member lives under `services/`.
- **`libs/`** or **`packages/`** — cohesive reusable internal code with no
  deployable of its own: consumed by other members via `{ workspace = true }`,
  never has its own `Dockerfile`. A directory does not become a library merely
  by being placed here; apply the admission test below. Pick one top-level name
  and use it consistently.

The rest of this skill illustrates the setup with `services/api` and
`services/worker` because that's the common case for a Python workspace.

## Before Creating A Shared Library

A workspace member adds a public contract, dependency edge, test surface, and
migration cost. Create one only when the code has one cohesive meaning outside
any single deployable and there is concrete reuse: normally at least two current
consumers, or an independently valuable protocol/client/schema boundary with a
concrete compatibility or dependency-isolation reason. Hypothetical reuse alone
is not enough.

Check all of these before adding `libs/<name>`:

- the candidate removes duplicated behavior or publishes one stable contract,
  not merely similar syntax;
- its inputs and outputs can be expressed without importing a service's private
  settings, application, domain, bootstrap, or tests;
- its dependencies are appropriate for every consumer and do not pull one
  service's framework or vendor stack into unrelated images;
- it has one reason to change and will not become a `common`, `shared`, `utils`,
  or organisation-wide dumping ground;
- consumers can migrate independently through an additive API when an atomic
  move is unsafe;
- owning it as a package improves consistency, dependency direction, testing,
  or release safety enough to justify the boundary.

Good candidates include a stable vendor client, shared wire/schema contracts,
database model metadata consumed by several members, and generic observability
plumbing. An observability library may coherently own provider lifecycle, span
helpers, propagation, trace/log correlation, redaction, and shared structured-
logging processors when those policies are common. Service span names, business
metrics, event vocabulary, and outcome decisions remain service-local. Use the
`observability` skill for that package's API and lifecycle.

## Why Not One Root `pyproject.toml`

A single shared dependency list forces every service to install every other
service's dependencies. A worker that only needs `boto3` and `celery` still
ships `fastapi` and `uvicorn` because the API service declared them in the same
file. This is invisible at small scale and gets worse as services and
dependencies accumulate — every Docker image grows, every image rebuild
reinstalls unrelated packages, and `uv add <pkg>` for one service silently
changes what every other service resolves and ships.

A uv workspace fixes this without giving up a single, consistent dependency
resolution: each service and library keeps its own dependency list, but `uv`
still resolves the whole workspace into one lockfile and can scope an install
to exactly one member's dependency closure.

## Repository Layout

```text
repo/
├── pyproject.toml              # virtual root: workspace + shared dev tooling
├── uv.lock                     # single lockfile for the entire workspace
├── .python-version             # exact local/CI/Docker Python patch
├── .dockerignore               # must not exclude .python-version
│
├── services/
│   ├── api/
│   │   ├── pyproject.toml      # api's own dependencies
│   │   ├── Dockerfile
│   │   └── src/
│   │       └── api/
│   │           └── main.py
│   │
│   └── worker/
│       ├── pyproject.toml      # worker's own dependencies
│       ├── Dockerfile
│       └── src/
│           └── worker/
│               └── main.py
│
└── libs/
    └── company_observability/
        ├── pyproject.toml
        └── src/
            └── company_observability/
                ├── __init__.py
                ├── config.py
                ├── providers.py
                ├── spans.py
                ├── propagation.py
                └── logging.py
```

Use plural glob members (`services/*`, `libs/*`) rather than an explicit list.
An explicit list silently excludes a new service that forgets to update it; a
glob has no such failure mode.

## Choose And Align Toolchain Versions First

Before scaffolding, verify the current stable patch release for the chosen
Python minor and the current stable uv release from official sources. Propose
the defaults, then ask one concise question: “I will use Python X.Y.Z and uv
A.B.C; do you want different versions?” Skip the question when the user has
already supplied both versions.

Use these verified defaults for the bundled template:

- Python `3.13.14`, with `.python-version` containing exactly `3.13.14`.
- uv `0.12.4`.
- Every member: `requires-python = ">=3.13,<3.14"`.

Apply them in this order:

1. Put `requires-python = ">=3.13,<3.14"` in every service and library
   `pyproject.toml`.
2. Run `uv python pin 3.13.14` at the workspace root to create
   `.python-version`.
3. Read that exact value into each Dockerfile's `ARG PYTHON_VERSION` default
   and keep the in-build equality check.
4. Put `required-version = "==0.12.4"` in the root `[tool.uv]` table and use
   the same exact uv version in Docker and CI.

Treat these as a coherent set. If the user changes the Python minor, update
all member `requires-python` ranges, Ruff's `target-version`,
`.python-version`, the Docker `PYTHON_VERSION`, and CI. If only the patch
changes within 3.13, update `.python-version`, Docker, and CI. If uv changes,
update root `required-version`, Docker, and CI.

Do not add mise. Let uv read `.python-version` locally; `uv python install`
can install the pinned interpreter when needed. A Dockerfile cannot derive a
pre-`FROM` `ARG` from a file in the build context, so repeat the exact Python
pin in `ARG PYTHON_VERSION` and fail the build if it differs from
`.python-version`.

In CI, install the exact root `required-version`, run `uv python install`, and
then use the root lockfile. `required-version` enforces the uv pin but does not
install the matching uv binary by itself.

## Root `pyproject.toml`: Workspace And Shared Tooling

```toml
[tool.uv]
required-version = "==0.12.4"

[tool.uv.workspace]
members = [
    "services/*",
    "libs/*",
]

[dependency-groups]
dev = [
    "mypy>=2.3.0,<3",
    "pre-commit>=4.6.1,<5",
    "pytest>=9.1.1,<10",
    "pytest-cov>=7.1.0,<8",
    "ruff>=0.16.3,<0.17",
]

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I", "UP", "B", "TID252"]

[tool.ruff.lint.flake8-tidy-imports]
ban-relative-imports = "all"

[tool.pytest.ini_options]
addopts = ["-ra", "--strict-config", "--strict-markers"]
testpaths = ["services", "libs"]

[tool.coverage.run]
branch = true

[tool.coverage.report]
show_missing = true
skip_covered = true

[tool.mypy]
python_version = "3.13"
strict = true
```

`TID252` with `ban-relative-imports = "all"` rejects every relative import
(`from .foo import bar`, `from ..core import baz`) in favor of absolute
imports rooted at the package name (`from api.core import baz`). Absolute
imports stay unambiguous and grep-able regardless of which module does the
importing, and they don't silently need updating when a module moves to a
different nesting depth.

uv supports a root with no `[project]` table at all — this is a "virtual"
workspace root: nothing is built or installed for the root itself, it only
groups members, anchors the single `uv.lock`, pins uv, and configures shared
development tools. Keep repo-wide lint, test, coverage, and type-check tools in
the root `dev` group. Keep framework-specific test plugins or type stubs used
by only one member in that member's own dependency group.

Do not add root `[project]`, root `[project.dependencies]`, or a root
`[build-system]` merely to express Python compatibility. Put
`requires-python` on every installable workspace member instead.

## Pre-commit And Pre-push

Read [references/pre-commit.md](references/pre-commit.md) whenever creating or
reviewing `.pre-commit-config.yaml`, changing a repo-wide tool version, adding or
moving a workspace member/root, changing quality commands in CI, or diagnosing
hooks that pass locally but fail in a scoped or clean environment.

The configuration is root-owned development tooling. Keep fast, filename-based
checks in the `pre-commit` stage and reserve workspace-wide type/test checks for
`pre-push` or CI. Local hooks that need the uv environment run through
`uv run --locked`; hook versions, root tool pins, CI, and Docker must not drift.
Discover the repository's actual service and internal-library roots rather than
assuming the example `services/` and `libs/` names.

## Service `pyproject.toml`

```toml
[project]
name = "api"
version = "0.1.0"
requires-python = ">=3.13,<3.14"
dependencies = [
    "fastapi",
    "uvicorn",
    "company-observability",
]

[tool.uv.sources]
company-observability = { workspace = true }

[build-system]
requires = ["hatchling>=1.32.0,<2"]
build-backend = "hatchling.build"
```

```toml
[project]
name = "worker"
version = "0.1.0"
requires-python = ">=3.13,<3.14"
dependencies = [
    "boto3",
    "company-observability",
]

[tool.uv.sources]
company-observability = { workspace = true }

[build-system]
requires = ["hatchling>=1.32.0,<2"]
build-backend = "hatchling.build"
```

`workspace = true` tells uv to satisfy `company-observability` from
`libs/company_observability/` instead of PyPI, and installs it editable. Each
service declares only what it imports — `api` never sees `boto3`, `worker`
never sees `fastapi`.

Give every workspace member a `src/<package>/` layout with the import package
matching the project name with hyphens replaced by underscores
(`company-observability` → `src/company_observability/`). Hatchling
autodetects that layout with no extra `[tool.hatch.build.targets.wheel]`
config; add `packages = ["src/<package>"]` explicitly only if autodetection
fails (for example, a project name that doesn't normalize to the directory
name).

## Shared Library `pyproject.toml`

```toml
[project]
name = "company-observability"
version = "0.1.0"
requires-python = ">=3.13,<3.14"
dependencies = [
    "opentelemetry-api",
    "opentelemetry-sdk",
    "opentelemetry-exporter-otlp-proto-http",
    "structlog",
]

[build-system]
requires = ["hatchling>=1.32.0,<2"]
build-backend = "hatchling.build"
```

A shared library is a workspace member exactly like a service — it gets its
own `pyproject.toml`, its own dependencies, and is consumed by
`{ workspace = true }` from whichever services import it. It does not need to
know which services depend on it. The observability dependency list above is an
example, not a default for other libraries; every member declares only what its
own source imports.

## Internal Library Layout

This skill owns the workspace boundary and installation mechanics, not a rigid
internal architecture. Every library still uses `src/<import_package>/`, keeps
tests beside the member, exposes a small intentional public API, and starts with
the fewest cohesive modules. Do not copy a deployable's `main.py`, `bootstrap/`,
`application/`, `adapters/`, and `config/` shell into a non-deployable library.

Keep a small package flat. Introduce a subpackage only when one narrower
capability has several cohesive modules, changes independently, needs distinct
test setup, or causes real naming pressure. Avoid file-per-class layouts,
one-file subpackages, speculative registries/factories, and generic `common`,
`shared`, `utils`, or `core` packages.

Use the `python-backend-structure` skill's shared-library guidance for detailed
module ownership, dependency direction, public exports, tests, and
consumer-by-consumer modularization. Use the domain-specific skill as well when
the library has one—for example, `observability` determines the internals of a
shared telemetry and logging package.

## One Lockfile, Scoped Installs

This is the mechanism that actually delivers the isolation, and it is easy to
get wrong by assuming the opposite:

- **There is exactly one `uv.lock`, at the workspace root**, resolving every
  member together. Do not hand-write a `uv.lock` inside `services/api/` — uv
  does not create or read one there, and one left behind by mistake is just
  dead weight.
- `uv lock` always operates on the whole workspace.
- Plain `uv run` / `uv sync` (no `--package`) operate on the workspace root.
  With a virtual root, that means installing **every** member into one shared
  `.venv` — confirmed: syncing a two-service, one-library workspace with no
  flags installed all three. That shared environment is the intended local
  dev setup — you can edit `api`, `worker`, and `company_observability`
  together with one interpreter, one `pytest` run, one IDE environment.
- `uv sync --package api` (or `uv run --package api …`, `uv export --package
  api`) scopes to `api` **and its transitive workspace dependencies only**.
  Confirmed directly: `uv sync --package api` installed `api` and
  `company-observability`, and left `worker` out entirely.

The shared dev venv is not a dependency firewall. uv's own docs say so
explicitly: *"uv can't ensure that packages don't import dependencies declared
by another workspace member."* A stray `import worker` inside `api`'s source
will run fine in the shared dev environment and only surface once something
actually does a `--package`-scoped install — a production Docker build, or CI.
Don't treat "it works locally" as proof of a clean dependency boundary; a
scoped `uv sync --package <service>` (or the Docker build itself) is the real
test.

### Root Dev Dependencies and Docker

A root `[dependency-groups] dev = [...]` group is installed **by default even
with `--package`** — confirmed: `uv sync --package api` alone still pulled in
a root-level dev dependency. Always pass `--no-dev` (or `--only-group
<name>` for a narrower selection) alongside `--package` when building anything
that ships, or the "lean image" goal quietly fails:

```bash
uv sync --frozen --no-dev --package api
```

## Lean Per-Service Docker Images

Build each service's image from the **workspace root** as the build context —
not from inside `services/api/` — because resolving `api`'s dependencies
still requires the root `pyproject.toml`, the shared `uv.lock`, and the source
of every workspace member `api` imports (at minimum `libs/company_observability/`).
Scoping the build context to just `services/api/` is a common mistake that
breaks the build the moment a service depends on a shared library. Full
production Dockerfile, `.dockerignore`, version-alignment checks, and build
commands: read `references/docker-builds.md` before creating or editing a
workspace member's image.

Use `assets/workspace-template/` as the canonical runnable scaffold. Copy and
adapt the asset instead of recreating these files from memory. It contains a
FastAPI service, an internal library, centralized tooling, tests, exact
toolchain pins, and the workspace-aware multi-stage Dockerfile.

## Setup And Verification

After adapting the template, run all of these from the repository root:

```bash
uv python install
uv lock --check
uv sync --frozen
uv run --locked pre-commit install
uv run --locked pre-commit run --all-files --hook-stage pre-commit
uv run ruff check .
uv run ruff format --check .
uv run mypy services libs
uv run pytest
uv run --locked pre-commit run --all-files --hook-stage pre-push
uv sync --frozen --no-dev --package <service>
docker build --pull -f services/<service>/Dockerfile .
```

Also verify the version contract explicitly:

```bash
test "$(uv run python -c 'import platform; print(platform.python_version())')" = "$(tr -d '\r\n' < .python-version)"
uv --version
```

The final expected ownership is:

| Environment | Python | uv |
| --- | --- | --- |
| Local project | exact `.python-version` | exact root `required-version` |
| CI | exact `.python-version` | exact root `required-version` |
| Docker builder | exact `PYTHON_VERSION` | exact `UV_VERSION` |
| Docker runtime | exact `PYTHON_VERSION` | absent |

## Adding a Service or Library

1. For a proposed library, apply [Before Creating A Shared Library](#before-creating-a-shared-library)
   and keep the code service-local if it does not earn the boundary.
2. Create `services/<name>/` (or `libs/<name>/` — see
   [Naming The Top-Level Directory](#naming-the-top-level-directory-services-vs-libspackages)
   above) with `src/<package>/` and a `pyproject.toml` declaring only that
   member's own dependencies.
3. If it consumes a shared library, add the library by name to `dependencies`
   and add `<library> = { workspace = true }` under `[tool.uv.sources]`.
4. Confirm it's picked up: `services/*` and `libs/*` globs cover it
   automatically; an explicit `members` list needs a new line.
5. Inspect `.pre-commit-config.yaml` and CI for explicit paths or filters; update
   them for the new member/root without broadening unrelated hooks.
6. Run `uv lock` at the root to fold it into the shared lockfile, then `uv sync
   --package <name>` for the new member and each consumer to verify the expected
   dependency closures without sibling-service leakage.
7. Run the library's own tests independently, then the focused contract and
   startup/lifecycle tests of each migrated consumer.
8. Add a Dockerfile only for a deployable. A `libs/*` member is included through
   each consumer's workspace-root build context and never has its own image.

## When Not To Split

Two services that always deploy together as one release unit, or candidate
library code with one consumer and no independent stable contract, do not need
the separation. Similar code that carries different business semantics should
also remain duplicated until a real common contract emerges. Keeping it inside
its owning service is a legitimate simplification—the workspace is not a
mandate to maximize package count.

## Related Skills

This skill covers the Python package/dependency structure inside the
repository. It does not cover how each service's image gets built and shipped
in CI, or whether Terraform and application source share a repository — those
decisions belong to the `terraform-aws`, `deploy-scripts`, and
`split-repo-app-releases` skills. For a Lambda function's `handler.py`/`src/`
boundary and packaging (ZIP vs. container), see `terraform-aws`'s
`references/python-lambda.md`; a Lambda that shares code with other functions
through a uv workspace follows this skill for the workspace layout and that
reference for the AWS-specific packaging step.

Use `python-backend-structure` for the internal modularization of services and
shared libraries. Use `observability` for the API, lifecycle, logging policy,
and migration of a shared observability package; this skill owns only whether
it earns a workspace member and how consumers install it.
