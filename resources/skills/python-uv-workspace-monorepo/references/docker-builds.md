# Docker Builds For A Workspace Member

Build from the **workspace root** as the Docker build context. A service's
dependency resolution and its local path dependencies (shared libraries) both
require files outside `services/<name>/` — the root `pyproject.toml`, the
shared `uv.lock`, and the source of every workspace member it imports. Run
`docker build -f services/api/Dockerfile .` from the repository root, not
`docker build .` from inside the service directory.

## Two-Stage Sync For Layer Caching

Split the dependency install from the source copy so that changing service
code doesn't invalidate the third-party dependency layer:

```dockerfile
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:<pinned-version> /uv /bin/uv
WORKDIR /workspace

# 1. Resolve and install third-party dependencies only. uv needs the root
#    pyproject.toml, uv.lock, and every member's pyproject.toml to validate
#    the lock — but not yet any source — so this layer stays cached across
#    source-only changes.
COPY pyproject.toml uv.lock ./
COPY services/api/pyproject.toml services/api/pyproject.toml
COPY libs/company_observability/pyproject.toml libs/company_observability/pyproject.toml
RUN uv sync --frozen --no-dev --no-install-workspace

# 2. Copy the source for this service and the workspace members it depends
#    on, then install just this service's dependency closure.
COPY services/api/src services/api/src
COPY libs/company_observability/src libs/company_observability/src
RUN uv sync --frozen --no-dev --no-editable --package api

FROM python:3.12-slim
COPY --from=builder /workspace/.venv /workspace/.venv
COPY --from=builder /workspace/services/api/src /workspace/services/api/src
ENV PATH="/workspace/.venv/bin:$PATH"
WORKDIR /workspace
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0"]
```

Pin the `uv` image to a specific version or digest rather than `latest`.

## Flags, Verified

Each flag below was checked directly against a real three-member workspace
(two services, one shared library) before writing this reference — this is
observed `uv` behavior, not a paraphrase of documentation:

- **`--no-install-workspace`** on the first sync installs zero workspace
  members (no service, no library) while still resolving and installing every
  third-party dependency declared anywhere in the workspace. That's too broad
  for a single-service image on its own — it's a caching step, not the final
  install. Combine it with per-member `pyproject.toml` copies as shown above
  so it has enough to validate against, without needing full source yet.
- **`--package api`** on the second sync installs `api` and only the workspace
  members `api` actually depends on. Confirmed: in a workspace with `api`,
  `worker`, and `company-observability`, `uv sync --package api` installed
  `api` and `company-observability` and left `worker` completely out of the
  virtual environment.
- **`--no-dev` is required alongside `--package`, not optional.** A root-level
  `[dependency-groups] dev = [...]` is installed by default even when
  `--package` scopes everything else — confirmed directly. Omitting `--no-dev`
  here means every production image quietly carries the repo's lint/test
  tooling.
- **`--frozen` instead of `--locked`** on the first sync, because that stage
  only has the root lockfile plus per-member `pyproject.toml` files copied in
  piecemeal — uv cannot fully assert the lock is up to date without every
  member present, so `--locked` would fail there for a reason unrelated to
  whether the lock is actually stale. Use `--locked` (or repeat `--frozen`) on
  the second sync once full source is present, if the pipeline should fail
  hard on a stale lock.
- **`--no-editable`** on the final sync installs the service and its
  workspace dependencies as real, non-editable installs rather than the
  editable/`.pth`-based installs uv uses by default for workspace members —
  appropriate for a production image, where nothing will edit the source in
  place after the image is built.

## Verifying Isolation Before Shipping

The shared local dev `.venv` (plain `uv sync`, no `--package`) installs every
workspace member together and does not stop one member from importing
another's code — uv's own documentation states it cannot enforce that
isolation. That means a stray cross-service import can pass local testing and
only fail once something does a scoped install. Before trusting that a
service's image is actually lean:

```bash
uv sync --frozen --no-dev --package <service>
uv run --package <service> python -c "import <service>.main"
```

Run this in a clean environment (or the Docker build itself, which is
naturally scoped this way) rather than relying on the shared dev venv, which
will import successfully even when the boundary is already broken.
