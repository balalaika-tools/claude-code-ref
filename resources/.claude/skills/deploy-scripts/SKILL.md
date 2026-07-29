---
name: deploy-scripts
description: Conventions and patterns for writing shell scripts that wrap Terraform stacks (deploy-*.sh, destroy-*.sh, build-*.sh, and the top-level deploy.sh / destroy.sh orchestrators). Use whenever creating a new per-stack script, adding scripts for a newly added Terraform stack, modifying or reviewing any script in `scripts/`, wiring up CI-aware Terraform workflows, or debugging confirmation prompts / idempotent destroys. Apply even when the user just says things like "add a script for the new stack", "the destroy script is broken", or "how should I structure this deploy?".
---

# Deploy & Destroy Script Conventions

Each Terraform stack gets two dedicated scripts: `deploy-<stack>.sh` and `destroy-<stack>.sh`. A pair of orchestration scripts — `deploy.sh` and `destroy.sh` — run all stacks in dependency order. Stacks with container images also get a `build-<service>.sh`.

Every script supports two callers with one code path: a human running it locally, and CI (GitHub Actions) running it unattended. `${CI:-}` is the only branch between them — see [Script Structure §5](#5-deploy-workflow) and [CI Integration](#ci-integration-github-actions). Locally you see the plan and approve it; in CI the plan is generated and applied without a prompt, gated instead by whatever branch/environment protection rules the workflow itself enforces.

These scripts wrap the conventions in the companion `terraform` skill — this doc covers the shell layer (workflow, confirmation gates, CI branching); see that skill for the Terraform-side conventions (naming, state, tagging, lifecycle) the scripts assume. Read both together when adding a stack: the `terraform` skill's "Adding a New Stack" checklist creates the module and environment directories, this doc's "Adding a New Stack" section creates the scripts that drive them.

## File Naming

| Pattern | Purpose |
|---|---|
| `deploy-<stack>.sh` | Deploy a stack via Terraform |
| `create-<stack>.sh` | Bootstrap-only stack (local backend, import logic — e.g. S3 state bucket) |
| `destroy-<stack>.sh` | Tear down a specific stack |
| `build-<service>.sh` | Build a Lambda zip/layer or Docker image and push to ECR |
| `deploy.sh` | Orchestrator — all stacks in dependency order |
| `destroy.sh` | Orchestrator — all stacks in reverse order |

Use `deploy-` for standard remote-backend stacks. Reserve `create-` only for bootstrap stacks that use a local backend.

A stack that owns both an ECR repo and the service that pushes to it (ECS, Lambda) splits into two stacks: `ecr` and the service. ECR repos are created once and almost never destroyed; the service stack churns on every deploy. Giving them separate lifecycles means a normal deploy never needs `-target` — see [§6](#6-ecr-as-its-own-stack).

---

## Script Structure

### 1. Header

```bash
#!/usr/bin/env bash
# One-line description
set -euo pipefail
```

`#!/usr/bin/env bash` picks up whatever `bash` is on `PATH` — macOS ships an ancient `/bin/bash` (3.2). `set -euo pipefail` fails fast on errors, unset vars, and broken pipes.

### 2. Path Resolution

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV="${ENV:-prod}"
TF_DIR="$REPO_ROOT/Terraform/environments/$ENV/<stack>"
BACKEND_CONFIG="$REPO_ROOT/Terraform/backend-config/$ENV/<stack>.backend.hcl"
```

Always resolve paths from `${BASH_SOURCE[0]}` — not `$PWD`. CI runners, orchestrators, and humans invoke scripts from different working directories. After `cd "$TF_DIR"`, reference tfvars as the relative `$ENV.tfvars`.

`ENV` defaults to `prod` only for convenience running a single script by hand; the `terraform` skill's dev → staging → prod promotion flow means CI must always pass `ENV` explicitly (`ENV=staging ./scripts/deploy.sh`), never rely on the default. Validate it early if a script is destructive:

```bash
case "$ENV" in dev|staging|prod) ;; *) print_error "ENV must be dev, staging, or prod"; exit 1 ;; esac
```

### 3. Helper Functions

Paste verbatim in every script — do not source from a shared lib:

```bash
print_info()    { printf "\033[0;34m[INFO]\033[0m    %s\n" "$1"; }
print_success() { printf "\033[0;32m[SUCCESS]\033[0m %s\n" "$1"; }
print_warning() { printf "\033[0;33m[WARNING]\033[0m %s\n" "$1"; }
print_error()   { printf "\033[0;31m[ERROR]\033[0m   %s\n" "$1"; }
```

Each script must be runnable standalone. Sourcing a sibling file adds a failure mode (file not found, wrong path) for a handful of printf lines. The duplication buys portability and auditability.

This standalone rule is about per-stack `deploy-*.sh` / `destroy-*.sh` scripts, which are meant to run in isolation. The orchestrators (`deploy.sh`, `destroy.sh`) are a narrow exception: they never run standalone by definition — they call the per-stack scripts — so they share one file for stack order. See [Orchestrators](#orchestrators).

### 4. Pre-flight Checks

```bash
for cmd in terraform aws; do   # add docker/jq if the script needs them
  if ! command -v "$cmd" &>/dev/null; then
    print_error "$cmd is not installed"
    exit 1
  fi
done

if ! aws sts get-caller-identity &>/dev/null; then
  print_error "AWS credentials are not configured"
  exit 1
fi

# If Docker is required:
if ! docker info >/dev/null 2>&1; then
  print_error "Docker daemon is not running"
  exit 1
fi
```

### 5. Deploy Workflow

```bash
cd "$TF_DIR"

# Fires on every exit path — success, cancellation, or a failed apply — so a
# stale tfplan never survives a crash. (Cleaning up per-branch instead of with
# trap looks clearer but misses the failure path: `terraform apply` can exit
# non-zero before any explicit `rm -f` runs.)
trap 'rm -f tfplan' EXIT

print_info "Initializing Terraform ($ENV/<stack>)..."
terraform init -backend-config="$BACKEND_CONFIG" -input=false

print_info "Validating..."
terraform validate

print_info "Formatting check..."
if ! terraform fmt -check -recursive "$REPO_ROOT/Terraform/modules/<stack>" >/dev/null 2>&1; then
  print_warning "Formatting issues found, auto-fixing..."
  terraform fmt -recursive "$REPO_ROOT/Terraform/modules/<stack>"
fi

print_info "Planning..."
terraform plan -input=false -lock-timeout=5m -var-file="$ENV.tfvars" -out=tfplan
# Add -var-file="$ARTIFACT_VARS" if the stack consumes build artifacts

if [[ "${CI:-}" == "true" ]]; then
  print_info "CI detected — auto-approving..."
  terraform apply -input=false tfplan
else
  print_info "Review the plan above."
  read -p "Apply? (yes/no): " -r
  if [[ "$REPLY" == "yes" ]]; then
    terraform apply -input=false tfplan
  else
    print_info "Cancelled"
    exit 0
  fi
fi
```

`-input=false` on every `init`/`plan`/`apply` call so a missing var fails loudly instead of hanging on a stdin prompt in CI. `-lock-timeout=5m` on `plan` so a stale lock from a prior run fails with a clear message instead of blocking indefinitely. Never hard-code `-auto-approve` in deploy scripts — the `CI` branch is the only auto-approve path, and it applies a plan a human already reviewed in the diff, not a fresh unreviewed one.

### 6. ECR-as-its-own-Stack

`-target` is Terraform's documented escape hatch for exceptional recovery, and it prints a warning every time it's used — it is not a pattern to build a routine deploy path around. Instead of targeting the ECR resources inside a combined stack, give ECR its own stack with its own lifecycle:

```bash
# deploy.sh order: ecr deploys before the build script needs a repo to push to
run_stack "ecr"        1 N "deploy-ecr.sh"
"$SCRIPT_DIR/build-<service>.sh"
run_stack "<service>"  2 N "deploy-<service>.sh"
```

`deploy-ecr.sh` is an ordinary stack script (§5) — no targeting, no partial applies, every stack always applies its whole plan. The service stack's `main.tf` reads the repo URL via `data "aws_ecr_repository"` or a `terraform_remote_state` output rather than owning the resource itself.

### 7. Pre-Deploy Asset Uploads

Some stacks require files in S3 before Terraform runs (e.g. EC2 `user_data` fetches the app on first boot). Upload before `terraform init`:

```bash
S3_BUCKET="${S3_BUCKET:-$(awk -F'"' '/^[[:space:]]*s3_app_bucket[[:space:]]*=/ {print $2; exit}' "$ENV.tfvars")}"
if [[ -n "$S3_BUCKET" ]]; then
  print_info "Syncing app files to s3://$S3_BUCKET/..."
  aws s3 sync "$APP_DIR/" "s3://$S3_BUCKET/$S3_PREFIX/" \
    --exclude "*.pyc" --exclude "__pycache__/*" --delete
fi
```

The `awk` parse only handles the simple `key = "value"` line format this repo's tfvars use — no interpolation, no same-line comments. It's a convenience fallback for local runs; CI should set `S3_BUCKET` as an explicit env var so the deploy never depends on scraping HCL with a regex.

### 8. Summary Banner (deploy scripts)

```bash
echo ""
print_success "════════════════════════════════════════"
print_success "  <Stack> deployed ($ENV)!"
print_success "════════════════════════════════════════"

SOME_OUTPUT=$(terraform output -raw some_key 2>/dev/null || echo "N/A")
echo ""
print_info "Some output: $SOME_OUTPUT"
```

For simple stacks with no notable outputs, call `terraform output` (no args) to print everything.

---

## Destroy Scripts

### Destroy Workflow

Init first, then show the *real* destroy plan — not just a hand-maintained bullet list — before the confirmation gate:

```bash
if [[ ! -d "$TF_DIR" ]]; then
  print_warning "Directory $TF_DIR does not exist, skipping"
  exit 0
fi

cd "$TF_DIR"

print_info "Initializing Terraform ($ENV/<stack>)..."
terraform init -backend-config="$BACKEND_CONFIG" -input=false >/dev/null

if ! terraform state list >/dev/null 2>&1 || [[ -z "$(terraform state list 2>/dev/null)" ]]; then
  print_info "No resources in <stack> state, skipping"
  exit 0
fi

if [[ "${CI:-}" != "true" && "${SKIP_CONFIRM:-}" != "true" ]]; then
  echo ""
  print_warning "This will destroy the <STACK> stack ($ENV). Plan:"
  terraform plan -destroy -input=false -lock-timeout=5m -var-file="$ENV.tfvars"
  echo ""
  read -p "Type 'DESTROY' to confirm: " -r
  echo ""
  if [[ "$REPLY" != "DESTROY" ]]; then
    print_info "Cancelled"
    exit 0
  fi
fi

print_info "Destroying <stack> stack..."
terraform destroy -auto-approve -input=false -lock-timeout=5m -var-file="$ENV.tfvars"
print_success "<Stack> stack destroyed"
```

A hardcoded "this will destroy: Resource A, Resource B" list drifts from the stack the moment someone adds a resource without updating the script — `plan -destroy` can't drift, because it's reading the same state the `destroy` call is about to act on. Use `DESTROY` for standard stacks. Use a more specific token for irreversible data loss (e.g. `DESTROY-DATA` for a data bucket, `DESTROY-BACKEND` for the state bucket). All-caps defeats muscle memory — typing `yes` by reflex won't pass.

Destroy scripts are always idempotent: missing directory or empty state → exit 0. The `destroy.sh` orchestrator runs stacks in sequence — a previously-torn-down stack must not halt the rest.

### ECS Drain-Before-Destroy

ECS stacks stall Terraform destroy if tasks are still running. Scale to 0 and wait first. Read the service list as JSON, not `-raw` inside a loop — a `for x in "$(terraform output -raw ...)"` loop over a single quoted string always iterates exactly once, silently, regardless of how many services the stack actually has:

```bash
AWS_REGION="${AWS_REGION:-$(awk -F'"' '/^[[:space:]]*aws_region[[:space:]]*=/ {print $2; exit}' "$ENV.tfvars")}"
CLUSTER_NAME="$(terraform output -raw ecs_cluster_name 2>/dev/null || echo "")"

# Stack output: ecs_service_names = ["worker", "api"]  (a list, even for one service)
mapfile -t SERVICE_NAMES < <(terraform output -json ecs_service_names 2>/dev/null | jq -r '.[]')

for SERVICE_NAME in "${SERVICE_NAMES[@]}"; do
  [[ -z "$SERVICE_NAME" ]] && continue
  if aws ecs describe-services --cluster "$CLUSTER_NAME" --services "$SERVICE_NAME" \
      --region "$AWS_REGION" --query 'services[0].status' --output text 2>/dev/null | grep -q ACTIVE; then
    print_info "Draining ECS service $SERVICE_NAME..."
    aws ecs update-service --cluster "$CLUSTER_NAME" --service "$SERVICE_NAME" \
      --desired-count 0 --region "$AWS_REGION" >/dev/null || true
    aws ecs wait services-stable --cluster "$CLUSTER_NAME" --services "$SERVICE_NAME" \
      --region "$AWS_REGION" || true
  fi
done
```

Add `jq` to this script's pre-flight tool check. Read service names from `terraform output` — never hardcode values that can drift.

### ENI Diagnostic Pattern

Lambda and ECS resources in a VPC hold ENIs that block Terraform destroy. This is the reactive counterpart to the SG/ENI guardrails in the `terraform` skill (`timeouts { delete = "30m" }`, `replace_security_groups_on_destroy`) — those reduce how often a destroy gets stuck; this is what to run when it still does. Surface the blocking ENIs on failure:

```bash
get_state_resource_id() {
  terraform state show -no-color "$1" 2>/dev/null \
    | awk -F' = ' '/^[[:space:]]*id[[:space:]]*=/{gsub(/"/, "", $2); print $2; exit}'
}

describe_sg_enis() {
  local label="$1" sg_id="$2"
  [[ -z "$sg_id" ]] && return 0
  print_warning "ENIs referencing $label SG $sg_id:"
  aws ec2 describe-network-interfaces \
    --region "$AWS_REGION" \
    --filters "Name=group-id,Values=$sg_id" \
    --query 'NetworkInterfaces[].{Id:NetworkInterfaceId,Status:Status,Type:InterfaceType}' \
    --output table 2>/dev/null || true
}

if terraform destroy -auto-approve -input=false -lock-timeout=5m -var-file="$ENV.tfvars"; then
  print_success "<Stack> stack destroyed"
else
  print_error "Destroy failed. Checking security-group ENI attachments..."
  describe_sg_enis "<service>" "$(get_state_resource_id "module.<stack>.aws_security_group.<service>")"
  exit 1
fi
```

---

## Build Scripts

### Lambda Artifact Build

Build a zip package and Lambda layer, then write a `.tfvars` file for the deploy script. The `base64sha256` here is unrelated to the container image tagging debate below — it's the content hash the AWS Lambda API itself requires via `source_code_hash` to detect that a redeploy is actually needed, not a version tag a human or another stack reads.

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

print_info()    { printf "\033[0;34m[INFO]\033[0m    %s\n" "$1"; }
print_success() { printf "\033[0;32m[SUCCESS]\033[0m %s\n" "$1"; }
print_error()   { printf "\033[0;31m[ERROR]\033[0m   %s\n" "$1"; }

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

The deploy script calls the build script before `terraform init`, then passes the artifact vars:

```bash
"$SCRIPT_DIR/build-<service>.sh"
# ...
terraform plan -input=false -lock-timeout=5m -var-file="$ENV.tfvars" -var-file="$ARTIFACT_VARS" -out=tfplan
```

### Docker ECR Build

Tag with the git SHA — never `latest`, never a content hash of the built artifact. See [`references/docker-image-tagging.md`](../../../../terraform/references/docker-image-tagging.md) in the `terraform` skill for the full rationale; the short version: a git SHA is traceable to the exact commit that produced it, and it gets the same "skip rebuild" optimization a content hash would — the same commit always produces the same tag, so `describe-images` already tells you whether this exact source has been pushed.

```bash
#!/usr/bin/env bash
# Build the <service> Docker image and push to ECR
# Usage: ./scripts/build-<service>.sh [ECR_REPO_URL]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_DIR="$REPO_ROOT/apps/<service>"
BUILD_DIR="$REPO_ROOT/build/<service>"
ARTIFACT_VARS="$BUILD_DIR/<service>-image.tfvars"

print_info()    { printf "\033[0;34m[INFO]\033[0m    %s\n" "$1"; }
print_success() { printf "\033[0;32m[SUCCESS]\033[0m %s\n" "$1"; }
print_warning() { printf "\033[0;33m[WARNING]\033[0m %s\n" "$1"; }
print_error()   { printf "\033[0;31m[ERROR]\033[0m   %s\n" "$1"; }

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
  ECR_REPO_URL="$(cd "$REPO_ROOT/Terraform/environments/${ENV:-prod}/ecr" && terraform output -raw <service>_ecr_repository_url)"
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

`AWS_REGION` prefers an explicit env var (CI always sets one) and only falls back to parsing the ECR URL locally; `cut`-ing the URL on dots assumes the standard `<account>.dkr.ecr.<region>.amazonaws.com` shape and breaks on FIPS/dualstack/`.cn` endpoints, so don't rely on it as the only source of truth in CI.

---

## Orchestrators

`deploy.sh` and `destroy.sh` are the one place scripts share state: a single ordered stack list, so destroy order is always the exact reverse of deploy order — not two hand-maintained lists that can silently drift apart.

```bash
# scripts/_stacks.sh — single source of truth for stack order.
# deploy.sh iterates it forwards; destroy.sh iterates it backwards.
# Sourced only by the two orchestrators — per-stack scripts stay standalone (§3).
STACKS=(
  "s3:create-s3.sh:destroy-s3.sh"
  "ecr:deploy-ecr.sh:destroy-ecr.sh"
  "network:deploy-network.sh:destroy-network.sh"
  # "<stack>:deploy-<stack>.sh:destroy-<stack>.sh"
)
```

### deploy.sh

Uses `SKIP_STACKS` for partial re-runs and a `FAILED_STACK` trap for clear failure context:

```bash
#!/usr/bin/env bash
# Deploy all stacks in dependency order
#
# Environment variables:
#   ENV=<dev|staging|prod> — target environment (required in CI, defaults to prod locally)
#   CI=true                — auto-approve all applies
#   IMAGE_TAG=<tag>         — Docker image tag for ECS services
#   SKIP_STACKS             — comma-separated stacks to skip (e.g. "s3,network")
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV="${ENV:-prod}"
source "$SCRIPT_DIR/_stacks.sh"

print_info()    { printf "\033[0;34m[INFO]\033[0m    %s\n" "$1"; }
print_success() { printf "\033[0;32m[SUCCESS]\033[0m %s\n" "$1"; }
print_warning() { printf "\033[0;33m[WARNING]\033[0m %s\n" "$1"; }
print_error()   { printf "\033[0;31m[ERROR]\033[0m   %s\n" "$1"; }

should_skip() {
  local stack="$1" skip_list="${SKIP_STACKS:-}"
  [[ -z "$skip_list" ]] && return 1
  [[ ",$skip_list," == *",$stack,"* ]]
}

# The orchestrator's pre-flight checks the UNION of tools every child script
# needs — include docker/jq/git here when any stack it runs builds images, so
# the run fails fast at the top instead of three stacks deep.
for cmd in terraform aws docker jq git; do
  if ! command -v "$cmd" &>/dev/null; then print_error "$cmd is not installed"; exit 1; fi
done
if ! aws sts get-caller-identity &>/dev/null; then
  print_error "AWS credentials are not configured"; exit 1
fi

echo ""
print_info "Environment: $ENV"
print_info "Deploy order: $(printf '%s → ' "${STACKS[@]%%:*}" | sed 's/ → $//')"
[[ -n "${SKIP_STACKS:-}" ]] && print_warning "Skipping: ${SKIP_STACKS}"
echo ""

if [[ "${CI:-}" != "true" ]]; then
  read -p "Proceed with deployment? (yes/no): " -r
  echo ""
  [[ "$REPLY" != "yes" ]] && { print_info "Cancelled"; exit 0; }
fi

FAILED_STACK=""
trap 'if [[ -n "$FAILED_STACK" ]]; then
  echo ""; print_error "Deployment failed at: $FAILED_STACK"
  print_error "Fix the issue and re-run. Earlier stacks are safe."
fi' EXIT

run_stack() {
  local name="$1" index="$2" total="$3" script="$4"
  if should_skip "$name"; then
    print_info "Skipping $name (SKIP_STACKS)"
    return
  fi
  echo ""
  print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  print_info "  [$index/$total] $name"
  print_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  FAILED_STACK="$name"
  "$SCRIPT_DIR/$script"
  FAILED_STACK=""
}

total=${#STACKS[@]}
i=1
for entry in "${STACKS[@]}"; do
  IFS=':' read -r name deploy_script _ <<<"$entry"
  run_stack "$name" "$i" "$total" "$deploy_script"
  ((i++))
done

echo ""
print_success "════════════════════════════════════════"
print_success "  All stacks deployed successfully ($ENV)!"
print_success "════════════════════════════════════════"
echo ""
print_info "To skip already-deployed stacks on re-run:"
print_info "  SKIP_STACKS=s3,network ./scripts/deploy.sh"
```

`ENV` doesn't need explicit passing into child scripts — it's an exported-by-default env var, so every `deploy-<stack>.sh` this script invokes inherits it automatically.

### destroy.sh

Iterates `_stacks.sh` in reverse — no second hand-maintained list to keep in sync with `deploy.sh`. Passes `SKIP_CONFIRM=true` as an inline env prefix (not `export`) — the orchestrator owns the single top-level confirmation gate:

```bash
#!/usr/bin/env bash
# Destroy all infrastructure in reverse dependency order
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV="${ENV:-prod}"
source "$SCRIPT_DIR/_stacks.sh"

STATE_BUCKET="${STATE_BUCKET:-<project>-tfstate}"

print_info()    { printf "\033[0;34m[INFO]\033[0m    %s\n" "$1"; }
print_success() { printf "\033[0;32m[SUCCESS]\033[0m %s\n" "$1"; }
print_warning() { printf "\033[0;33m[WARNING]\033[0m %s\n" "$1"; }
print_error()   { printf "\033[0;31m[ERROR]\033[0m   %s\n" "$1"; }

for cmd in terraform aws; do
  if ! command -v "$cmd" &>/dev/null; then print_error "$cmd is not installed"; exit 1; fi
done
if ! aws sts get-caller-identity &>/dev/null; then
  print_error "AWS credentials are not configured"; exit 1
fi

echo ""
print_warning "This will destroy all infrastructure ($ENV):"
print_warning "  $(printf '%s, ' "${STACKS[@]%%:*}" | sed 's/, $//')"
echo ""
print_warning "NOT destroyed: state bucket s3://$STATE_BUCKET (prevent_destroy = true)"
echo ""

if [[ "${CI:-}" != "true" ]]; then
  read -p "Type 'DESTROY' to confirm: " -r
  echo ""
  [[ "$REPLY" != "DESTROY" ]] && { print_info "Cancelled"; exit 0; }
fi

# Add `sleep 30` between stacks where ENI/task cleanup needs time to settle
for (( idx=${#STACKS[@]}-1; idx>=0; idx-- )); do
  IFS=':' read -r name _ destroy_script <<<"${STACKS[$idx]}"
  SKIP_CONFIRM=true "$SCRIPT_DIR/$destroy_script"
done

echo ""
print_success "════════════════════════════════════════"
print_success "  All stacks destroyed ($ENV)."
print_success "════════════════════════════════════════"
echo ""
# Restate what survived teardown — now, when the user is deciding what to clean
# up by hand. The upfront gate warned it would be kept; the closing summary is
# the actionable reminder, with the concrete bucket name to delete manually.
print_warning "State bucket s3://$STATE_BUCKET still exists (delete manually if you want it gone)."
```

**Always restate surviving resources in the closing summary, not just the upfront gate.** Anything a destroy intentionally leaves behind — the Terraform state bucket (`prevent_destroy`), retained data buckets, snapshots, log groups with retention — must be echoed *after* teardown completes, naming the concrete resource (e.g. the actual bucket name), because that is the moment the operator decides what to remove by hand. A warning that scrolled past 10 minutes and several `DESTROY` confirmations ago is not a reminder.

---

## S3 Bootstrap Exception

The state-bucket stack is the bootstrap exception:
- Uses a **local backend** — the remote state bucket doesn't exist yet
- Is not per-environment — one bucket holds every environment's state, keyed by `terraform-state-{env}/{stack}/...` (see the `terraform` skill's Backend section), so `create-s3.sh` ignores `ENV` entirely
- Uses `import_if_exists` before apply to re-import buckets idempotently
- Skips the plan file + interactive gate; in CI uses `-auto-approve`, locally uses the default interactive prompt
- Destroy uses a stricter confirmation token (e.g. `DESTROY-DATA`) for the data bucket
- The state bucket carries `prevent_destroy = true`; removing it requires editing the source

```bash
import_if_exists() {
  local tf_addr="$1" resource_id="$2"
  if terraform state show "$tf_addr" &>/dev/null 2>&1; then
    print_info "Already in state: $tf_addr — skipping import"
    return
  fi
  if aws s3api head-bucket --bucket "$resource_id" 2>/dev/null; then
    print_info "Importing existing bucket '$resource_id' → $tf_addr"
    terraform import -var-file=prod.tfvars "$tf_addr" "$resource_id"
  fi
}
```

The `terraform` skill's general rule — prefer declarative `import` blocks over the imperative `terraform import` CLI — assumes you already know the resource is there to import. This bootstrap script doesn't: it has to check `head-bucket` against real AWS state *at runtime* to decide whether an import is even needed, which a static `import` block can't express. That's the one case where the CLI form is correct, not a violation of the rule.

---

## CI Integration (GitHub Actions)

The scripts don't change between local and CI use — only the env vars set around them do. A workflow calling the orchestrator:

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}   # dev / staging / prod — gates via GitHub environment protection rules
    env:
      CI: "true"
      ENV: ${{ inputs.environment }}
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ vars.DEPLOY_ROLE_ARN }}   # OIDC — no long-lived AWS keys in the repo
          aws-region: ${{ vars.AWS_REGION }}
      - run: ./scripts/deploy.sh
```

`CI=true` is what makes `deploy.sh`/`deploy-<stack>.sh` skip the interactive `read -p "Apply?"` and apply the plan unattended (§5) — the approval gate moves from a terminal prompt to whatever branch protection / required-reviewers rule guards the workflow run itself (e.g. a GitHub Environment with required reviewers on `prod`). Locally, with `CI` unset, every script stops and shows the plan before applying. Same scripts, same code path — only the environment decides which gate applies.

---

## CI / Environment Variables

| Variable | Used by | Effect |
|---|---|---|
| `ENV` | all | Target environment (`dev`, `staging`, `prod`) — defaults to `prod` locally; CI must always set it explicitly |
| `CI=true` | all | Auto-approve deploys, skip interactive prompts |
| `SKIP_CONFIRM=true` | destroy scripts | Skip `DESTROY` confirmation (set by `destroy.sh` orchestrator) |
| `SKIP_STACKS` | `deploy.sh` | Comma-separated stack names to skip |
| `IMAGE_TAG` | build scripts | Docker image tag; defaults to the current git SHA |
| `<SERVICE>_IMAGE_TAG` | build scripts | Per-service override when multiple images are deployed |
| `AWS_REGION` | build/destroy scripts | Explicit region; falls back to parsing tfvars/ECR URL locally only |
| `TF_VAR_*` | deploy scripts | Inject sensitive Terraform variables without a tfvars file |

---

## Quality Gates

Every script declares `set -euo pipefail`, so latent quoting and unset-variable
bugs surface as hard failures at the worst possible time — mid-deploy. Lint
before committing:

- Run `shellcheck scripts/*.sh` and resolve findings (or annotate intentional
  ones with `# shellcheck disable=SCxxxx` plus a reason). It catches unquoted
  expansions, masked exit codes in pipelines, and `read` misuse that
  `pipefail` would otherwise only reveal at runtime.
- Run `chmod +x` on new scripts (see step 5 below) — a non-executable script
  invoked by an orchestrator fails with a confusing permission error.
- Optionally wire both into a pre-commit hook so they run automatically.

---

## Adding a New Stack

1. Copy the nearest similar deploy script → `deploy-<stack>.sh`; update `TF_DIR`, `BACKEND_CONFIG`, module path in fmt check, and summary outputs.
2. Copy the nearest similar destroy script → `destroy-<stack>.sh`; update paths, and add ENS diagnostics if the stack runs in a VPC.
3. If the stack manages container images: create an `ecr` stack (once, if the project doesn't have one yet) plus `build-<service>.sh`; the service stack reads the repo URL from the `ecr` stack rather than owning it (§6).
4. Add the stack to `_stacks.sh` in the correct position — `deploy.sh` and `destroy.sh` both pick it up automatically, forwards and reversed.
5. `chmod +x scripts/deploy-<stack>.sh scripts/destroy-<stack>.sh`
