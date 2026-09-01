# Pre-commit and pre-push in a uv workspace

Use this reference when creating, reviewing, or changing the repository-root
`.pre-commit-config.yaml`; aligning hooks with uv/Ruff/CI versions; adding or
moving workspace members; or debugging local/CI hook differences.

## Ownership and discovery

`.pre-commit-config.yaml` is repo-wide development tooling. Keep one at the
workspace root beside `pyproject.toml` and `uv.lock`. Do not put independent
configs inside services or libraries unless they are separate repositories.

Before editing it, inspect:

- the root `pyproject.toml`, `uv.lock`, and `.python-version`;
- existing hook stages, exclusions, file filters, and local hook commands;
- actual deployable and internal-library roots from `[tool.uv.workspace]` and
  the repository tree—`services/` and `libs/` are examples, not hard names;
- CI quality jobs and their Python/uv versions;
- Docker pins when a tool version is shared with image builds;
- domain-specific checks already owned by another skill, such as ShellCheck or
  Terraform validation from `deploy-scripts`/`terraform-aws`.

Preserve useful repository hooks and policies. Adding Python workspace support
does not authorize replacing security, shell, Terraform, generated-file, or
organisation-specific checks.

## Stage policy

Use hook stages to keep ordinary commits responsive without weakening the
quality gate:

| Stage | Suitable work |
| --- | --- |
| `pre-commit` | trailing whitespace, syntax/config validation, Ruff lint/format, lockfile freshness, secret scanning, other fast filename-based checks |
| `pre-push` | workspace-wide mypy, non-live pytest, build/contract checks, or tools that ignore filenames and scan large trees |
| CI | the complete required gate, including the fast pre-commit stage plus explicit type, test, integration, build, and deployment checks selected by the repository |

Do not put the full test suite or a workspace-wide type check on every commit by
default. Do not make a required check local-only: developers can bypass hooks,
and CI must enforce the equivalent outcome.

When `default_install_hook_types` includes both stages, an ordinary
`pre-commit install` installs both hook scripts. Otherwise document or run the
explicit installation commands appropriate to the repository.

## Hook execution environments

Use upstream hooks for tools designed to receive changed filenames. They run in
their own pre-commit-managed environment:

- `pre-commit/pre-commit-hooks` for format and config sanity checks;
- `astral-sh/ruff-pre-commit` for Ruff lint and formatting;
- `astral-sh/uv-pre-commit` for `uv-lock`.

Use `repo: local`, `language: system`, and `uv run --locked ...` for hooks that
need the workspace environment, internal packages, or root dev dependencies.
Set `pass_filenames: false` only when the command intentionally selects its own
complete scope. Use `always_run: true` for a required workspace-wide gate whose
scope cannot be inferred safely from changed paths.

`--locked` is load-bearing: a hook must fail when declared dependencies and
`uv.lock` disagree, not rewrite the lock opportunistically. The dedicated
`uv-lock` hook owns lockfile updates/checks. Do not run `uv sync` inside a hook;
it mutates the environment and makes commit latency/network behavior
unpredictable.

## Version alignment

Keep one selected version per tool across every place that executes it:

| Tool | Align |
| --- | --- |
| uv | root `[tool.uv].required-version`, `uv-pre-commit` revision, CI setup, and Docker `UV_VERSION` |
| Ruff | root dev dependency/lock, `ruff-pre-commit` revision, and any CI invocation |
| Python | `.python-version`, member `requires-python`, CI, and Docker |
| pre-commit | root dev dependency/lock and CI invocation environment |

For a ranged root dependency, compare the hook revision with the version
actually resolved in `uv.lock`, not merely the lower bound. Update all owners in
one deliberate toolchain upgrade. Do not run `pre-commit autoupdate` and accept
unrelated revisions without checking compatibility and corresponding pins.

## Canonical shape

Adapt roots, versions, exclusions, and domain-specific hooks to the repository:

```yaml
default_install_hook_types: [pre-commit, pre-push]

repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-json
      - id: check-added-large-files
      - id: check-case-conflict
      - id: check-merge-conflict
      - id: debug-statements
      - id: mixed-line-ending

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.16.3
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/astral-sh/uv-pre-commit
    rev: 0.12.4
    hooks:
      - id: uv-lock

  - repo: local
    hooks:
      - id: mypy
        name: mypy (workspace)
        entry: uv run --locked mypy services libs
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-push]

      - id: pytest
        name: pytest (non-live)
        entry: uv run --locked pytest -m "not live" --no-cov
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-push]
```

The example roots are placeholders. If the repository uses `apps/`,
`components/`, `packages/`, Lambda roots, top-level contract tests, or other
owned Python trees, derive the mypy/pytest scope from the real configuration and
CI. Do not rename the repository or introduce parallel roots to fit this
example.

`ruff-check --fix` intentionally modifies files locally. In CI the same hook
runs against a clean checkout and fails when it would make a change. If the
project prohibits modifying hooks, remove `--fix` deliberately in both local
and documented behavior rather than relying on context-dependent arguments.

## CI parity

At minimum, CI runs the fast stage against the complete checkout:

```bash
uv run --locked pre-commit run --all-files --hook-stage pre-commit
```

CI may run pre-push hooks directly:

```bash
uv run --locked pre-commit run --all-files --hook-stage pre-push
```

or run equivalent explicit mypy/pytest commands in dedicated jobs. Avoid doing
both unless the duplication is intentional. Compare command arguments, markers,
paths, Python/uv versions, and environment prerequisites—not just tool names.

Integration, E2E, live-provider, Docker, Terraform, and deployment checks
normally stay in dedicated CI jobs with their required infrastructure. Do not
force them into ordinary pre-push merely to make one file list every check.

## Adding or moving members

When a service, library, Lambda, or repository-owned test root is added, moved,
or renamed:

1. update workspace membership and package metadata first;
2. search pre-commit local-hook entries, `files`/`exclude` expressions, mypy
   paths, pytest collection, coverage sources, and CI commands for explicit old
   roots;
3. update only affected scopes—do not broaden unrelated domain hooks;
4. run the fast stage against all files and the relevant pre-push/CI-equivalent
   checks;
5. verify a package-scoped install still exposes dependency leakage that the
   shared developer environment might hide.

Do not exclude a new member from lint/type/test hooks simply to make the hook
pass. Fix its configuration, give it an explicit justified profile, or report
the incompatible boundary.

## Verification

Run from the workspace root:

```bash
uv lock --check
uv run --locked pre-commit validate-config
uv run --locked pre-commit run --all-files --hook-stage pre-commit
uv run --locked pre-commit run --all-files --hook-stage pre-push
```

Then run the repository's CI-equivalent commands that are not owned by those
stages. Confirm:

- repeated runs are clean and do not keep modifying files;
- hook revisions match the selected uv/Ruff versions;
- local hooks resolve through the locked workspace environment;
- every current Python root is covered by the intended lint/type/test scope;
- skipped integration/live/deployment checks have a separate enforced CI owner;
- a fresh checkout can run the hooks without undeclared developer-global tools,
  except explicitly documented `language: system` prerequisites.
