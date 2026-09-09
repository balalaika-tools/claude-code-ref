# Toolchain, Projects, and Dependency Isolation

Read this reference before creating or changing Python/uv pins, root or member
`pyproject.toml` files, workspace membership, lockfiles, or package-scoped
install commands.

## Version contract

Verify the current stable Python patch for the selected minor and the current
stable uv release from official sources. Unless both are already specified,
propose them and ask: “I will use Python X.Y.Z and uv A.B.C; do you want
different versions?”

The bundled template snapshot currently uses:

- Python `3.13.15`, with `.python-version` exactly `3.13.15`;
- uv `0.12.7`;
- member compatibility `requires-python = ">=3.13,<3.14"`;
- Ruff target `py313` and mypy `python_version = "3.13"`.

Before copying the asset, update all derived pins through
`scripts/update_toolchain.py`; never hand-edit only a subset.

If the Python minor changes, update member compatibility ranges, Ruff, mypy,
`.python-version`, Docker, and CI. If only the patch changes, update
`.python-version`, Docker, and CI. If uv changes, update root
`required-version`, Docker, pre-commit, and CI.

Run `uv python pin X.Y.Z` at the repository root. Let uv read the pin locally;
do not add mise. In CI, install the exact root `required-version`, then run
`uv python install` and use the root lockfile. `required-version` enforces the
running uv version but does not install it.

A Dockerfile cannot derive a pre-`FROM` argument from the build context. Repeat
the exact patch in `ARG PYTHON_VERSION` and fail early if it differs from
`.python-version`. See [docker-builds.md](docker-builds.md).

## Single-project `pyproject.toml`

For one deployable, the root is installable and owns runtime dependencies:

```toml
[project]
name = "my-service"
version = "0.1.0"
requires-python = ">=3.13,<3.14"
dependencies = ["fastapi", "uvicorn"]

[dependency-groups]
dev = [
    "mypy>=2.3.0,<3",
    "pre-commit>=4.6.1,<5",
    "pytest>=9.1.1,<10",
    "pytest-cov>=7.1.0,<8",
    "ruff>=0.16.3,<0.17",
]

[build-system]
requires = ["hatchling>=1.32.0,<2"]
build-backend = "hatchling.build"
```

Use the repository-wide tool configuration below with paths such as `src` and
`tests`. Do not add `[tool.uv.workspace]` or use `--package`.

## Workspace virtual root

The root has no `[project]`, root runtime dependencies, or build system. It
groups members, owns one lockfile, pins uv, and configures development tools:

```toml
[tool.uv]
required-version = "==0.12.7"

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

Adapt roots to the repository. `TID252` plus `ban-relative-imports = "all"`
requires absolute package imports. Keep repo-wide tools at the root; keep a
framework-specific plugin or stub used by one member with that member.

## Member projects

Each service or library owns only the dependencies its source imports:

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

`workspace = true` resolves that package from a workspace member rather than
PyPI. The library itself does not declare its consumers. Every member uses
`src/<package>/`; hyphens in the project name normalize to underscores in the
import package. Hatchling detects this layout. Add an explicit wheel `packages`
setting only when normalized-name autodetection fails.

## Lockfile and scoped installs

There is exactly one `uv.lock`, at the repository root. `uv lock` resolves the
whole workspace; member lockfiles are dead weight.

Use `uv sync --all-packages` when the intended local environment contains every
member. The shared environment improves development ergonomics but can hide an
undeclared cross-member import. A package-scoped install is the boundary test:

```bash
uv sync --frozen --no-dev --package api
```

`--package api` includes `api` and its transitive workspace dependencies, not
sibling services. Root development groups are installed by default even with
`--package`, so `--no-dev` is mandatory for shipped artifacts. Use
`uv run --package api ...` or `uv export --package api` for equivalent scoped
operations.

Do not put service runtime dependencies in the root development group. A local
success in the all-package environment does not prove dependency isolation;
verify each deployable with the scoped sync, its Docker build, or both.

## Version verification

From the generated repository root, verify the selected tools explicitly:

```bash
test "$(uv run python -c 'import platform; print(platform.python_version())')" = "$(tr -d '\r\n' < .python-version)"
uv --version
```

The expected ownership is:

| Environment | Python | uv |
| --- | --- | --- |
| Local project | exact `.python-version` | exact root `required-version` |
| CI | exact `.python-version` | exact root `required-version` |
| Docker builder | exact `PYTHON_VERSION` | exact `UV_VERSION` |
| Docker runtime | exact `PYTHON_VERSION` | absent |
