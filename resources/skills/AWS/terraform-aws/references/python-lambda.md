# Python Lambda Source and Packaging

Keep Python Lambda source separate from Terraform configuration. Terraform owns
the function, IAM, triggers, configuration, and immutable artifact coordinates;
the Lambda directory owns executable code, dependencies, and tests.

## Contents

- [Repository layout](#repository-layout)
- [Code ownership boundary](#code-ownership-boundary)
- [Dependency policy](#dependency-policy)
- [ZIP packages](#zip-packages)
- [Container images](#container-images)
- [Terraform contract](#terraform-contract)
- [Validation](#validation)

## Repository layout

Put independently deployable functions under `lambdas/` at the root of the
repository that owns the source. Never put handler source, dependency manifests,
virtual environments, or generated packages under `Terraform/` or a Terraform
module.

```text
<source-repo-root>/
├── Terraform/               # monorepo only; absent in a split application repo
├── lambdas/
│   ├── process_event/
│   │   ├── handler.py
│   │   ├── pyproject.toml
│   │   ├── uv.lock
│   │   ├── src/
│   │   │   └── process_event/
│   │   │       ├── __init__.py
│   │   │       ├── service.py
│   │   │       ├── models.py
│   │   │       └── clients/
│   │   └── tests/
│   └── send_notification/
│       └── ...
├── scripts/
└── build/                  # generated and gitignored
```

In a split application/infrastructure layout the same tree lives in the
application repository with no `Terraform/` beside it, and `scripts/` there holds
the build script rather than deploy scripts. The Terraform side is unchanged: it
still declares the function and consumes artifact coordinates as required inputs
with no default — see the `deploy-scripts` skill's
`references/split-repo-releases.md`.

Use this layout for every new Lambda. Keep `handler.py` as the thin AWS entry
point and place implementation code in `src/<package>/`, even when the first
version is small. Use `handler.lambda_handler` as the Terraform handler. The
build copies the contents of `src/` to the artifact root, so `handler.py` imports
`process_event`, not `src.process_event`:

```python
from process_event.service import process_event
```

Use `__init__.py` with two leading and two trailing underscores. Existing
dependency-free, single-file functions may retain their established layout
unless the user requests a migration; apply the full layout to new functions and
when intentionally modularizing an existing one.

Use a valid Python identifier for `src/<package>/`: replace hyphens with
underscores, so a function directory such as `process-event/` still uses the
import package `process_event/`.

Give each independently released Lambda its own `pyproject.toml` and `uv.lock`.
Use a shared uv workspace only when the functions intentionally share a release
unit or local package; do not couple unrelated function upgrades through one
lockfile merely to reduce file count.

## Code ownership boundary

Treat event decoding, AWS SDK calls, environment/configuration lookup, logging,
and translation to a domain call as Lambda/AWS adapter code. It is reasonable
for an infrastructure task to implement a small, complete adapter.

Treat domain rules, custom or external API clients, multi-step workflows,
substantial transformations, persistence logic, and reusable application modules
as application code. For that case:

1. Keep `handler.py` thin and move the implementation into `src/<package>/`.
2. Follow the repository's Python conventions and load the applicable
   application/Python skill when one exists.
3. Define the infrastructure-to-code contract explicitly: handler symbol, event
   and response shape, environment variables, secret names or ARNs, IAM actions,
   timeout, retries, idempotency behavior, and failure destinations.
4. If the requested work is infrastructure-only, stop at that contract and hand
   the application implementation to its owner. Do not invent business behavior.
5. Never deploy a placeholder that returns success, swallows an unimplemented
   branch, or makes a real trigger acknowledge work that did not happen.

Do not generate Python source through HCL heredocs, `local_file`, provisioners,
or Terraform templates. Do not use Terraform to run `uv`, install packages, or
construct the release artifact.

## Dependency policy

Use `uv`, `pyproject.toml`, and `uv.lock` for every function with third-party
dependencies. A typical non-package project is:

```toml
[project]
name = "process-event"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
    "boto3>=1.40",
    "pydantic>=2.8",
]

[dependency-groups]
dev = [
    "pytest>=8",
    "ruff>=0.12",
]

[tool.uv]
package = false

[tool.pytest.ini_options]
pythonpath = [".", "src"]
```

Match `requires-python` to the Lambda runtime. Change dependencies with `uv add`
or `uv remove`, run `uv lock`, and commit both manifest and lockfile. In CI,
`uv lock --check` must pass before packaging. With the pytest path above,
`uv run pytest` imports the thin root handler and the application package the
same way the flattened ZIP does.

`pyproject.toml` is optional only when `handler.py` has no packaged dependencies.
Prefer declaring and packaging all imported dependencies, including `boto3`,
rather than depending on runtime-bundled versions. Never maintain a committed
`requirements.txt` beside `uv.lock`. An exported requirements file is a
transient, gitignored build artifact.

## ZIP packages

AWS Lambda does not install from `pyproject.toml` at invocation time. Put the
handler, application modules, and installed runtime dependencies at the root of
the ZIP. The build/release workflow, not Terraform, performs these steps:

```bash
(
  cd "$LAMBDA_DIR"
  uv lock --check
  uv export \
    --frozen \
    --no-dev \
    --no-editable \
    --no-emit-project \
    --format requirements.txt \
    --output-file "$REQUIREMENTS_FILE"
)

uv pip install \
  --requirements "$REQUIREMENTS_FILE" \
  --target "$PACKAGE_DIR" \
  --python-version "$PYTHON_VERSION" \
  --python-platform "$UV_PLATFORM" \
  --only-binary=:all:

cp "$LAMBDA_DIR/handler.py" "$PACKAGE_DIR/"
cp -R "$LAMBDA_DIR/src/." "$PACKAGE_DIR/"
(cd "$PACKAGE_DIR" && zip -q -X -r "$FUNCTION_ZIP" .)
```

Set the target explicitly from the Terraform runtime and architecture:

| Lambda architecture | `UV_PLATFORM` |
|---|---|
| `x86_64` | `x86_64-manylinux2014` |
| `arm64` | `aarch64-manylinux2014` |

Fail when a dependency has no compatible wheel instead of silently compiling a
host-native extension. If a source build is required, build inside a container
matching the Lambda OS, Python runtime, and architecture.

For a dependency-free function, skip `uv export` and `uv pip install`, but still
package `handler.py` plus the contents of `src/` at the ZIP root. Prefer one ZIP
containing code and dependencies. Introduce a Lambda layer only for an
intentional, independently versioned shared dependency with measured operational
benefit; a layer adds another artifact and release contract.

The full shell-script pattern belongs to the sibling `deploy-scripts` skill in
`references/build-scripts.md`.

## Container images

Use a multi-stage build based on the AWS Lambda Python image. Copy only the
resolved environment and source into the final image; do not ship `uv` or its
cache. Pin the uv image to a reviewed version or digest rather than `latest`.

```dockerfile
FROM ghcr.io/astral-sh/uv:<pinned-version> AS uv

FROM public.ecr.aws/lambda/python:3.12 AS builder
COPY --from=uv /uv /bin/uv
COPY pyproject.toml uv.lock ./
RUN uv lock --check \
    && uv export \
         --frozen \
         --no-dev \
         --no-editable \
         --no-emit-project \
         --format requirements.txt \
         --output-file /tmp/requirements.txt \
    && uv pip install \
         --requirements /tmp/requirements.txt \
         --target "${LAMBDA_TASK_ROOT}"
COPY handler.py "${LAMBDA_TASK_ROOT}/"
COPY src/ "${LAMBDA_TASK_ROOT}/"

FROM public.ecr.aws/lambda/python:3.12
COPY --from=builder "${LAMBDA_TASK_ROOT}/" "${LAMBDA_TASK_ROOT}/"
CMD ["handler.lambda_handler"]
```

Copy `pyproject.toml` and `uv.lock` before source to preserve dependency-layer
caching. Build for `linux/amd64` or `linux/arm64` to match the function. Push to
the platform-owned immutable ECR repository and give Terraform an image URI
pinned by digest.

## Terraform contract

For ZIP functions, publish the ZIP to a versioned artifact bucket in the
function's AWS Region and pass `s3_key`, `s3_object_version`, and the ZIP's
base64 SHA-256 to the application stack. For image functions, pass the image
digest. Artifact inputs have no default; a plan must fail when the build/publish
step did not produce a version.

Terraform may validate that the configured handler, runtime, architecture, and
artifact metadata agree, but it must not inspect a developer virtual environment
or depend on a local build directory for a clean-checkout plan. Publish an
immutable Lambda version and point triggers and integrations at an alias, as
described in
[`workload-deploy-patterns.md`](workload-deploy-patterns.md#lambda-functions).

## Validation

Before publishing:

- Run `uv lock --check` and the function's tests and lint checks.
- Build for the declared runtime and architecture, including native-wheel checks.
- Inspect the ZIP to confirm `handler.py` and dependencies are at its root and
  that tests, `.venv`, caches, lockfiles, and build metadata are absent.
- Import the handler from the packaged directory in a matching Lambda container
  or equivalent CI environment.
- Exercise representative success, retry, duplicate-event, and malformed-event
  cases. Mock external APIs at the application boundary.
- Scan the resolved dependencies and artifact, then publish and record the
  immutable S3 object version or image digest.

Primary references:

- [Astral: Using uv with AWS Lambda](https://docs.astral.sh/uv/guides/integration/aws-lambda/)
- [AWS: Working with Python ZIP archives](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html)
- [AWS: Deploy Python Lambda container images](https://docs.aws.amazon.com/lambda/latest/dg/python-image.html)
