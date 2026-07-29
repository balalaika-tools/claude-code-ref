# Build Scripts and Pre-Deploy Uploads

`build-<service>.sh` produces a deployable artifact — a Lambda zip/layer or a
Docker image in ECR — and hands its version to Terraform through a generated
`.tfvars` file. Some stacks also need files in S3 before Terraform runs at all.

Every listing here follows the standard script spine in `SKILL.md`: `set -euo
pipefail`, `${BASH_SOURCE[0]}` path resolution, the four `print_*` helpers
pasted verbatim, and a pre-flight tool check.

## Contents

- [Lambda Artifact Build](#lambda-artifact-build)
- [Docker ECR Build](#docker-ecr-build)
- [Pre-Deploy Asset Uploads](#pre-deploy-asset-uploads)

## Lambda Artifact Build

Build a zip package and Lambda layer, then write a `.tfvars` file for the deploy
script. The `base64sha256` here is unrelated to the container image tagging
decision below — it's the content hash the AWS Lambda API itself requires via
`source_code_hash` to detect that a redeploy is actually needed, not a version
tag a human or another stack reads.

```bash
#!/usr/bin/env bash
# Build the <service> Lambda zip and layer
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_DIR="$REPO_ROOT/apps/<service>"
BUILD_DIR="$REPO_ROOT/build/<service>"
FUNCTION_ZIP="$BUILD_DIR/<service>.zip"
LAYER_ZIP="$BUILD_DIR/<service>-layer.zip"
ARTIFACT_VARS="$BUILD_DIR/<service>-artifacts.tfvars"

# Paste the four print_* helpers verbatim (SKILL.md -> Helper Functions).

for cmd in pip3 zip openssl; do
  if ! command -v "$cmd" &>/dev/null; then
    print_error "$cmd is not installed"; exit 1
  fi
done

base64_sha256() { openssl dgst -sha256 -binary "$1" | openssl base64 | tr -d '\n'; }

mkdir -p "$BUILD_DIR"

# Build function zip
(cd "$APP_DIR/src" && zip -qr "$FUNCTION_ZIP" .)

# Build layer
mkdir -p "$BUILD_DIR/layer/python"
pip3 install -r "$APP_DIR/requirements.txt" \
  -t "$BUILD_DIR/layer/python" --quiet --upgrade \
  --platform manylinux2014_x86_64 --python-version 3.12 --only-binary=:all:
(cd "$BUILD_DIR/layer" && zip -qr "$LAYER_ZIP" python)

cat >"$ARTIFACT_VARS" <<EOF
lambda_package_path              = "$FUNCTION_ZIP"
lambda_package_base64sha256      = "$(base64_sha256 "$FUNCTION_ZIP")"
lambda_layer_package_path        = "$LAYER_ZIP"
lambda_layer_package_base64sha256 = "$(base64_sha256 "$LAYER_ZIP")"
EOF

print_success "<Service> Lambda artifacts built"
```

Pin `--platform` and `--python-version` to the function's runtime and
architecture. A layer built from the host's native wheels fails at invocation
time, not build time.

The deploy script calls the build script before `terraform init`, then passes
the artifact vars as a second `-var-file`:

```bash
"$SCRIPT_DIR/build-<service>.sh"
# ...
terraform plan -input=false -lock-timeout=5m \
  -var-file="$VAR_FILE" -var-file="$ARTIFACT_VARS" -out="$PLAN_FILE"
```

## Docker ECR Build

Tag with the Git SHA — never `latest` or a branch name — and configure the ECR
repository as immutable. Read `references/docker-image-tagging.md` from the
sibling `terraform-aws` skill for the tag-versus-digest decision.

```bash
#!/usr/bin/env bash
# Build the <service> Docker image and push to ECR
# Usage: ./scripts/build-<service>.sh [ECR_REPO_URL]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV="${ENV:?Set ENV before building or selecting an environment repository}"
APP_DIR="$REPO_ROOT/apps/<service>"
BUILD_DIR="$REPO_ROOT/build/<service>"
ARTIFACT_VARS="$BUILD_DIR/<service>-image.tfvars"

# Paste the four print_* helpers verbatim (SKILL.md -> Helper Functions).

for cmd in aws docker git; do
  if ! command -v "$cmd" &>/dev/null; then
    print_error "$cmd is not installed"; exit 1
  fi
done

GIT_SHA="$(git -C "$REPO_ROOT" rev-parse --short=12 HEAD)"
IMAGE_TAG="${IMAGE_TAG:-$GIT_SHA}"
[[ "$IMAGE_TAG" == "latest" ]] && { print_error "'latest' is not valid; ECR uses immutable tags."; exit 1; }

if [[ -n "$(git -C "$REPO_ROOT" status --porcelain -- "$APP_DIR")" ]]; then
  print_warning "Uncommitted changes in $APP_DIR — tag $IMAGE_TAG won't reproduce this exact build. Commit first for a real deploy."
fi

# Accept repo URL as argument or fall back to terraform output
if [[ -n "${1:-}" ]]; then
  ECR_REPO_URL="$1"
else
  ECR_REPO_URL="$(
    TF_DATA_DIR="$REPO_ROOT/.terraform-data/$ENV/ecr/ecr" \
      terraform -chdir="$REPO_ROOT/Terraform/stacks/ecr" \
      output -raw <service>_ecr_repository_url
  )"
fi

AWS_ACCOUNT_ID="$(echo "$ECR_REPO_URL" | cut -d'.' -f1)"
AWS_REGION="${AWS_REGION:-$(echo "$ECR_REPO_URL" | cut -d'.' -f4)}"
ECR_REPO_NAME="$(echo "$ECR_REPO_URL" | cut -d'/' -f2)"

write_artifact_vars() {
  mkdir -p "$BUILD_DIR"
  cat >"$ARTIFACT_VARS" <<EOF
<service>_image_tag = "$IMAGE_TAG"
EOF
}

# Skip build if this commit's tag already exists in ECR — immutable tags + a
# git-SHA tag make this safe: same commit always produces the same tag.
if aws ecr describe-images --repository-name "$ECR_REPO_NAME" \
    --image-ids imageTag="$IMAGE_TAG" --region "$AWS_REGION" >/dev/null 2>&1; then
  write_artifact_vars
  print_success "Image tag already exists in ECR; skipping build"
  exit 0
fi

aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin \
  "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

docker build --platform linux/arm64 -t "${ECR_REPO_URL}:${IMAGE_TAG}" "$APP_DIR"
docker push "${ECR_REPO_URL}:${IMAGE_TAG}"

write_artifact_vars
print_success "<Service> image pushed: ${ECR_REPO_URL}:${IMAGE_TAG}"
```

`write_artifact_vars` is a function, not an inline heredoc, because the
early-exit path needs it too: when the tag already exists in ECR the script must
still hand the deploy script a tfvars file, or the following `terraform plan`
fails on a missing variable.

Set `--platform` to the task/function architecture, not the builder's. Building
`linux/arm64` on an x86 runner requires `docker buildx` with QEMU configured, or
a native arm64 runner.

`AWS_REGION` prefers an explicit env var (CI always sets one) and only falls
back to parsing the ECR URL locally; `cut`-ing the URL on dots assumes the
standard `<account>.dkr.ecr.<region>.amazonaws.com` shape and breaks on
FIPS/dualstack/`.cn` endpoints, so don't rely on it as the only source of truth
in CI.

## Pre-Deploy Asset Uploads

Some stacks require files in S3 before Terraform runs — for example EC2
`user_data` that fetches the app on first boot. Upload before `terraform init`:

```bash
S3_BUCKET="${S3_BUCKET:-$(awk -F'"' '/^[[:space:]]*s3_app_bucket[[:space:]]*=/ {print $2; exit}' "$VAR_FILE")}"
if [[ -n "$S3_BUCKET" ]]; then
  print_info "Syncing app files to s3://$S3_BUCKET/..."
  aws s3 sync "$APP_DIR/" "s3://$S3_BUCKET/$S3_PREFIX/" \
    --exclude "*.pyc" --exclude "__pycache__/*" --delete
fi
```

The `awk` parse only handles the simple `key = "value"` line format this repo's
tfvars use — no interpolation, no same-line comments. It's a convenience
fallback for local runs; CI should set `S3_BUCKET` as an explicit env var so the
deploy never depends on scraping HCL with a regex.
