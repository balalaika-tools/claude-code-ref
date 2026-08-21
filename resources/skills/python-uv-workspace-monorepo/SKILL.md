---
name: python-uv-workspace-monorepo
description: >-
  Structure or review a multi-service Python monorepo with a virtual uv
  workspace root, one `pyproject.toml` per deployable under `services/`, one
  per internal library under `libs/` or `packages/`, and workspace sources for
  internal dependencies. Standardize centralized Ruff, pytest, coverage, and
  mypy tooling; exact Python and uv versions across local development, CI, and
  Docker; one shared lockfile; scoped per-service installs; and lean
  multi-stage production images. Use when deciding whether each service needs
  its own `pyproject.toml`, splitting root dependencies, scaffolding or
  reviewing uv workspaces and Dockerfiles, sharing internal packages, or
  preventing sibling-service dependencies and dev tools from entering an
  image.
---

# Python Monorepo: uv Workspaces Across Services

Apply this rule first; everything else in this skill follows from it:

> **Independently deployable = its own `pyproject.toml`. Shared internal code =
> its own `pyproject.toml`. The root `pyproject.toml` declares the workspace and
> repo-wide development tooling, but no runtime dependencies any service
> ships.**

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
- **`libs/`** or **`packages/`** — reusable internal code with no deployable
  of its own: consumed by other members via `{ workspace = true }`, never has
  its own `Dockerfile`. Pick one of the two names and use it consistently.

The rest of this skill illustrates the setup with `services/api` and
`services/worker` because that's the common case for a Python workspace.

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
                └── logging.py
```

Use plural glob members (`services/*`, `libs/*`) rather than an explicit list.
An explicit list silently excludes a new service that forgets to update it; a
glob has no such failure mode.

### Non-Python Deployables Under `services/`

The glob claims every directory under `services/` as a workspace member,
Python or not. A deployable that ships without its own `pyproject.toml` — a
prebuilt image plus YAML configs, a static asset bundle, a Terraform-only
module — breaks every `uv` command in the repository the moment it lands
under `services/`, because uv expects a `pyproject.toml` at that path and
fails the whole workspace resolution when it's missing. Add that directory to
`exclude` under `[tool.uv.workspace]` in the root `pyproject.toml`, with a
comment stating why it has no `pyproject.toml`:

```toml
[tool.uv.workspace]
members = [
    "services/*",
    "libs/*",
]
# services/otel-collector ships a pinned Collector image and YAML configs
# only — it is a deployable, not a Python distribution, and has no
# pyproject.toml. Without this exclusion the services/* glob claims it as a
# workspace member and every `uv` command in the repository fails.
exclude = [
    "services/otel-collector",
]
```

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
    "pytest>=9.1.1,<10",
    "pytest-cov>=7.1.0,<8",
    "ruff>=0.16.3,<0.17",
]

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I", "UP", "B"]

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

uv supports a root with no `[project]` table at all — this is a "virtual"
workspace root: nothing is built or installed for the root itself, it only
groups members, anchors the single `uv.lock`, pins uv, and configures shared
development tools. Keep repo-wide lint, test, coverage, and type-check tools in
the root `dev` group. Keep framework-specific test plugins or type stubs used
by only one member in that member's own dependency group.

Do not add root `[project]`, root `[project.dependencies]`, or a root
`[build-system]` merely to express Python compatibility. Put
`requires-python` on every installable workspace member instead.

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
    "structlog",
]

[build-system]
requires = ["hatchling>=1.32.0,<2"]
build-backend = "hatchling.build"
```

A shared library is a workspace member exactly like a service — it gets its
own `pyproject.toml`, its own dependencies, and is consumed by
`{ workspace = true }` from whichever services import it. It does not need to
know which services depend on it.

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
uv run ruff check .
uv run ruff format --check .
uv run mypy services libs
uv run pytest
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

1. Create `services/<name>/` (or `libs/<name>/` — see
   [Naming The Top-Level Directory](#naming-the-top-level-directory-services-vs-libspackages)
   above) with `src/<package>/` and a `pyproject.toml` declaring only that
   member's own dependencies.
2. If it consumes a shared library, add the library by name to `dependencies`
   and add `<library> = { workspace = true }` under `[tool.uv.sources]`.
3. Confirm it's picked up: `services/*` and `libs/*` globs cover it
   automatically; an explicit `members` list needs a new line.
4. Run `uv lock` at the root to fold it into the shared lockfile, then `uv sync
   --package <name>` to verify it installs on its own with the dependencies
   you expect and nothing from a sibling service.
5. Add its `Dockerfile` following `references/docker-builds.md`.

## When Not To Split

Two services that always deploy together as one release unit, or a library so
small and single-consumer it will never be reused, don't need the separation.
Merging them into one `pyproject.toml` is a legitimate simplification — the
workspace is a tool for isolating independent release units, not a mandate to
maximize the package count. If a "shared" library only ever has one consumer,
consider whether it's actually shared or just misplaced service code.

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
