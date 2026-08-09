---
name: python-uv-workspace-monorepo
description: >-
  Structure a Python monorepo that holds multiple independently deployable
  services plus shared internal libraries, using a uv workspace: one
  workspace-only root `pyproject.toml`, one `pyproject.toml` per service under
  `services/`, one `pyproject.toml` per shared library under `libs/`, and
  `[tool.uv.sources]` with `workspace = true` to wire internal packages
  together. Use when deciding whether a service needs its own `pyproject.toml`,
  setting up or reviewing a `uv` workspace, splitting a single bloated root
  `pyproject.toml` into per-service dependency sets, keeping a service's Docker
  image free of dependencies only a sibling service needs, or answering "should
  each service have its own pyproject.toml" / "how do we share a library across
  services without duplicating dependencies".
---

# Python Monorepo: uv Workspaces Across Services

Apply this rule first; everything else in this skill follows from it:

> **Independently deployable = its own `pyproject.toml`. Shared internal code =
> its own `pyproject.toml`. The root `pyproject.toml` declares the workspace and
> nothing else — it must not hold runtime dependencies any service ships.**

This applies once a repository holds more than one independently built artifact
(more than one Dockerfile, more than one Lambda, more than one deployed
process). A single-service repository does not need a workspace; give it one
plain `pyproject.toml` at its root and stop reading here.

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
├── pyproject.toml              # workspace root — no [project] table, no dependencies
├── uv.lock                     # single lockfile for the entire workspace
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

## Root `pyproject.toml`: Workspace Only

```toml
[tool.uv.workspace]
members = [
    "services/*",
    "libs/*",
]
```

uv supports a root with no `[project]` table at all — this is a "virtual"
workspace root: nothing is built or installed for the root itself, it only
groups members and anchors the single `uv.lock`. Verified directly: `uv lock`,
`uv sync`, and `uv sync --package <member>` all work against a root that
contains only `[tool.uv.workspace]`.

The root is still the right place for repo-wide **tooling** configuration,
since none of it ships in an image: `[tool.ruff]`, `[tool.mypy]`,
`[tool.pytest.ini_options]`, and a root `[dependency-groups] dev = [...]` for
lint/test tools every service uses. That is a development-time concern, not a
runtime dependency — keep it separate from any service's `[project.dependencies]`.
See [Root Dev Dependencies and Docker](#root-dev-dependencies-and-docker) below
for the one gotcha this creates.

## Service `pyproject.toml`

```toml
[project]
name = "api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi",
    "uvicorn",
    "company-observability",
]

[tool.uv.sources]
company-observability = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

```toml
[project]
name = "worker"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "boto3",
    "company-observability",
]

[tool.uv.sources]
company-observability = { workspace = true }

[build-system]
requires = ["hatchling"]
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
requires-python = ">=3.12"
dependencies = [
    "structlog",
]

[build-system]
requires = ["hatchling"]
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
Dockerfile pattern, including the two-stage sync that keeps third-party
dependencies in their own cached layer: `references/docker-builds.md`.

## Adding a Service or Library

1. Create `services/<name>/` (or `libs/<name>/`) with `src/<package>/` and a
   `pyproject.toml` declaring only that member's own dependencies.
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
