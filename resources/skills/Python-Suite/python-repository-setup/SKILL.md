---
name: python-repository-setup
description: >-
  Structure or review a Python repository: a single src-layout project or a uv
  workspace with isolated deployables and reusable packages. Use for dependency
  ownership, lockfiles, toolchain pins, repository-wide quality tooling, Docker,
  Compose, and scoped production installs. Use `python-service-architecture` for
  modules inside a service or library.
---

# Python Repository Setup

Choose the repository mode before generating files:

- **Single deployable:** keep the installable project and repository tooling at
  the root. Do not create `services/`, `libs/`, or a uv workspace pre-emptively.
- **Multiple independently deployable artifacts:** use a virtual uv workspace.
  Every deployable owns a project under `services/`; genuinely reusable internal
  packages live under one consistent `libs/` or `packages/` root.

Workspace mode applies once a repository holds more than one independently built
artifact, such as multiple Dockerfiles, Lambdas, or deployed processes. Units
that always build and deploy together remain one project.

The shared standards below apply to both modes: exact toolchain pins, one root
lockfile, root-owned quality tooling, Docker, Compose, and CI alignment.
Workspace-only mechanics include a virtual root, member globs,
`{ workspace = true }`, and `--package`-scoped installs.

For the detailed layouts, directory naming, shared-library admission test, and
member-addition workflow, read
[references/repository-modes.md](references/repository-modes.md) whenever
choosing or changing repository boundaries.

## Core Ownership Rules

For a workspace:

> Independently deployable = its own `pyproject.toml`. Genuinely reusable
> internal code = its own `pyproject.toml`. The virtual root declares the
> workspace and repo-wide development tooling, but no shipped runtime
> dependencies.

Use plural member globs such as `services/*` and `libs/*`; do not rely on an
explicit member list that a new member can silently miss. Every installable
member uses `src/<import_package>/`, and the normalized import package matches
the project name.

Service dependency ownership and YAML configuration ownership are independent.
In a workspace, use one repository-root `config/` for committed YAML baselines
by default. Create service-local YAML directories only when the user explicitly
requests per-service configuration ownership. Use `python-settings-config` for
layout and merge precedence and `python-service-architecture` for package-local
Python settings modules.

For one deployable, the root `pyproject.toml` owns runtime dependencies and
repository-wide development tooling, with source at `src/<import_package>/` and
tests at `tests/`.

## Toolchain, Projects, and Dependency Isolation

Before scaffolding, verify the current stable patch release for the selected
Python minor and the current stable uv release from official sources. Propose
the defaults and ask one concise version question unless the user supplied both.
Treat Python, uv, member compatibility, Ruff, Docker, and CI pins as one version
contract.

Before creating or editing `pyproject.toml`, `.python-version`, `uv.lock`, uv
workspace membership, or package-scoped commands, read
[references/toolchain-and-dependencies.md](references/toolchain-and-dependencies.md).
It contains the canonical TOML shapes, current template pins, update rules,
workspace-source declarations, and the important `--no-dev`/`--package`
semantics.

Use `assets/workspace-template/` as the canonical runnable workspace scaffold.
Before copying it, update its single manifest and all derived pins with:

```bash
python scripts/update_toolchain.py --python X.Y.Z --uv A.B.C
```

Do not hand-edit only some derived pins. Do not add mise; uv reads the root
`.python-version` locally.

Keep exactly one `uv.lock` at the repository root. A workspace member never
owns a lockfile. The shared developer environment is not a dependency firewall;
verify deployables with a package-scoped, no-dev sync or production image.

## Repository-wide Quality Tooling

Keep Ruff, pytest, coverage, mypy, and pre-commit dependencies and configuration
at the repository root. Member-specific framework plugins or stubs may remain
with the member that needs them. Derive lint, type, test, and coverage paths from
the real repository roots rather than assuming example names.

Read [references/pre-commit.md](references/pre-commit.md) whenever creating or
reviewing `.pre-commit-config.yaml`, changing a repo-wide tool version, adding or
moving a member/root, aligning quality commands with CI, or diagnosing hooks
that differ between local and clean environments.

Keep fast filename-based checks in `pre-commit`; put workspace-wide types and
tests in `pre-push` or CI. Hooks that use the uv environment run through
`uv run --locked`. Preserve unrelated security, shell, Terraform, and
organisation-specific hooks.

## Production Docker Images

For a workspace, build each deployable from the repository root so uv can read
the root metadata, lockfile, target member, and transitive internal libraries.
For a single project, build the root Dockerfile from the root without workspace
metadata or `--package` flags.

Before creating or editing an image, read
[references/docker-builds.md](references/docker-builds.md). It defines the
canonical multi-stage build, metadata-copy rules, locked non-editable install,
non-root runtime, `.dockerignore`, secrets boundary, version checks, and worker
versus web-service variants. Adapt the bundled Dockerfile and `.dockerignore`
instead of recreating them from memory.

## Docker Compose and Environment Contracts

Read [references/docker-compose.md](references/docker-compose.md) whenever
creating or reviewing `compose.yaml`, root `.env.example`, service environment
mapping, or local container startup.

Compose uses one ignored root `.env` as local stack input. Map each service's
environment explicitly; do not attach the entire root file with
`env_file: .env`. In a workspace, each service-level `.env.example` remains the
complete runtime contract for that process, while the root `.env.example`
documents Compose and stack inputs.

## Verification

Run applicable checks from the repository root. For both modes:

```bash
uv python install
uv lock --check
uv sync --frozen
uv run --locked pre-commit install
uv run --locked pre-commit run --all-files --hook-stage pre-commit
uv run ruff check .
uv run ruff format --check .
uv run mypy <python-roots>
uv run pytest
uv run --locked pre-commit run --all-files --hook-stage pre-push
docker compose config --quiet
docker compose up --build
```

For workspace mode, additionally run:

```bash
uv sync --frozen --all-packages
uv sync --frozen --no-dev --package <service>
docker build --pull -f services/<service>/Dockerfile .
```

For a single project, instead use:

```bash
uv sync --frozen --no-dev
docker build --pull -f Dockerfile .
```

Verify the skill template's version contract before copying it:

```bash
python scripts/update_toolchain.py --check
```

After copying, confirm the selected Python and uv versions from the generated
repository root. Local, CI, and Docker must agree on the exact Python patch; uv
must be exact locally, in CI, and in the Docker builder, and absent from the
runtime image.

## Related Skills

This skill owns repository shape, Python dependency ownership, workspace
mechanics, and repo-wide tooling. Use:

- `python-service-architecture` for internal service/library modularization and
  detailed shared-library API ownership;
- a domain skill such as `observability` for a reusable package's internal API
  and lifecycle;
- `terraform-aws` for Lambda handler/source boundaries and ZIP versus container
  packaging;
- `terraform-aws`, `deploy-scripts`, and `split-repo-app-releases` for delivery
  pipelines, infrastructure layout, and repository-release boundaries.
