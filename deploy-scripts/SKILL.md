---
name: deploy-scripts
description: Conventions and patterns for writing shell scripts that wrap Terraform stacks (deploy-*.sh, destroy-*.sh, build-*.sh, and the top-level deploy.sh / destroy.sh orchestrators). Use whenever creating a new per-stack script, adding scripts for a newly added Terraform stack, modifying or reviewing any script in `scripts/`, wiring up CI-aware Terraform workflows, or debugging confirmation prompts / idempotent destroys. Apply even when the user just says things like "add a script for the new stack", "the destroy script is broken", or "how should I structure this deploy?".
---

# Deploy & Destroy Script Conventions

Each Terraform stack gets two dedicated scripts: `deploy-<stack>.sh` and `destroy-<stack>.sh`. A pair of orchestration scripts — `deploy.sh` and `destroy.sh` — run all stacks in dependency order. Stacks with container images also get a `build-<service>.sh`.

All scripts follow a consistent structure so they work identically locally and in CI.

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
TF_DIR="$REPO_ROOT/Terraform/environments/prod/<stack>"
BACKEND_CONFIG="$REPO_ROOT/Terraform/backend-config/prod/<stack>.backend.hcl"
```

Always resolve paths from `${BASH_SOURCE[0]}` — not `$PWD`. CI runners, orchestrators, and humans invoke scripts from different working directories. After `cd "$TF_DIR"`, reference tfvars as the relative `prod.tfvars`.

### 3. Helper Functions

Paste verbatim in every script — do not source from a shared lib:

```bash
print_info()    { printf "\033[0;34m[INFO]\033[0m    %s\n" "$1"; }
print_success() { printf "\033[0;32m[SUCCESS]\033[0m %s\n" "$1"; }
print_warning() { printf "\033[0;33m[WARNING]\033[0m %s\n" "$1"; }
print_error()   { printf "\033[0;31m[ERROR]\033[0m   %s\n" "$1"; }
```

Each script must be runnable standalone. Sourcing a sibling file adds a failure mode (file not found, wrong path) for a handful of printf lines. The duplication buys portability and auditability.

### 4. Pre-flight Checks

```bash
for cmd in terraform aws; do   # add docker if the script builds images
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

print_info "Initializing Terraform (<stack>)..."
terraform init -backend-config="$BACKEND_CONFIG"

print_info "Validating..."
terraform validate

print_info "Formatting check..."
if ! terraform fmt -check -recursive "$REPO_ROOT/Terraform/modules/<stack>" >/dev/null 2>&1; then
  print_warning "Formatting issues found, auto-fixing..."
  terraform fmt -recursive "$REPO_ROOT/Terraform/modules/<stack>"
fi

print_info "Planning..."
terraform plan -var-file=prod.tfvars -out=tfplan
# Add -var-file="$ARTIFACT_VARS" if the stack consumes build artifacts

if [[ "${CI:-}" == "true" ]]; then
  print_info "CI detected — auto-approving..."
  terraform apply tfplan
else
  print_info "Review the plan above."
  read -p "Apply? (yes/no): " -r
  if [[ "$REPLY" == "yes" ]]; then
    terraform apply tfplan
  else
    print_info "Cancelled"
    rm -f tfplan
    exit 0
  fi
fi

rm -f tfplan
```

Clean up `tfplan` explicitly after apply or cancellation. Never use `trap` for this — explicit cleanup per branch is clearer. Never hard-code `-auto-approve` in deploy scripts.

### 6. ECR-First Targeting Pattern

When a stack manages both ECR repos and ECS services, ECR repos must exist before images can be pushed. Apply just the ECR resources first, then build, then do the full plan:

```bash
ECR_TARGETS=(
  "-target=module.<stack>.module.<service>.aws_ecr_repository.<service>"
  "-target=module.<stack>.module.<service>.aws_ecr_lifecycle_policy.<service>"
)
print_info "Ensuring ECR repositories exist..."
terraform apply -var-file=prod.tfvars -auto-approve "${ECR_TARGETS[@]}"

ECR_REPO_URL="$(terraform output -raw <service>_ecr_repository_url)"

"$SCRIPT_DIR/build-<service>.sh" "$ECR_REPO_URL"

# Full plan after images are pushed
terraform plan \
  -var-file=prod.tfvars \
  -var-file="$REPO_ROOT/build/<service>/<service>-image.tfvars" \
  -out=tfplan
```

`-auto-approve` on the ECR-only apply is intentional — only inert repos are created. The full apply still goes through the interactive gate.

### 7. Pre-Deploy Asset Uploads

Some stacks require files in S3 before Terraform runs (e.g. EC2 `user_data` fetches the app on first boot). Upload before `terraform init`:

```bash
S3_BUCKET=$(awk -F'"' '/^[[:space:]]*s3_app_bucket[[:space:]]*=/ {print $2}' "$TF_DIR/prod.tfvars")
if [[ -n "$S3_BUCKET" ]]; then
  print_info "Syncing app files to s3://$S3_BUCKET/..."
  aws s3 sync "$APP_DIR/" "s3://$S3_BUCKET/$S3_PREFIX/" \
    --exclude "*.pyc" --exclude "__pycache__/*" --delete
fi
```

### 8. Summary Banner (deploy scripts)

```bash
echo ""
print_success "════════════════════════════════════════"
print_success "  <Stack> deployed!"
print_success "════════════════════════════════════════"

SOME_OUTPUT=$(terraform output -raw some_key 2>/dev/null || echo "N/A")
echo ""
print_info "Some output: $SOME_OUTPUT"
```

For simple stacks with no notable outputs, call `terraform output` (no args) to print everything.

---

## Destroy Scripts

### Confirmation Gate

```bash
if [[ "${CI:-}" != "true" && "${SKIP_CONFIRM:-}" != "true" ]]; then
  echo ""
  print_warning "This will destroy the <STACK> stack:"
  print_warning "  - Resource A"
  print_warning "  - Resource B"
  echo ""
  read -p "Type 'DESTROY' to confirm: " -r
  echo ""
  if [[ "$REPLY" != "DESTROY" ]]; then
    print_info "Cancelled"
    exit 0
  fi
fi
```

Use `DESTROY` for standard stacks. Use a more specific token for irreversible data loss (e.g. `DESTROY-DATA` for a data bucket, `DESTROY-BACKEND` for the state bucket). All-caps defeats muscle memory — typing `yes` by reflex won't pass.

### Destroy Workflow

```bash
if [[ ! -d "$TF_DIR" ]]; then
  print_warning "Directory $TF_DIR does not exist, skipping"
  exit 0
fi

cd "$TF_DIR"

print_info "Initializing Terraform (<stack>)..."
terraform init -backend-config="$BACKEND_CONFIG" >/dev/null

if ! terraform state list >/dev/null 2>&1 || [[ -z "$(terraform state list 2>/dev/null)" ]]; then
  print_info "No resources in <stack> state, skipping"
  exit 0
fi

print_info "Destroying <stack> stack..."
terraform destroy -auto-approve -var-file="prod.tfvars"
print_success "<Stack> stack destroyed"
```

Destroy scripts are always idempotent: missing directory or empty state → exit 0. The `destroy.sh` orchestrator runs stacks in sequence — a previously-torn-down stack must not halt the rest.

### ECS Drain-Before-Destroy

ECS stacks stall Terraform destroy if tasks are still running. Scale to 0 and wait first:

```bash
AWS_REGION="$(grep -E '^aws_region' "prod.tfvars" | awk -F'"' '{print $2}')"
AWS_REGION="${AWS_REGION:-us-east-1}"
CLUSTER_NAME="$(terraform output -raw ecs_cluster_name 2>/dev/null || echo "")"

for SERVICE_NAME in "$(terraform output -raw <service>_service_name 2>/dev/null || echo "")"; do
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

Read service names from `terraform output` — never hardcode values that can drift.

### ENI Diagnostic Pattern

Lambda and ECS resources in a VPC hold ENIs that block Terraform destroy. Surface them on failure:

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

if terraform destroy -auto-approve -var-file="prod.tfvars"; then
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

Build a zip package and Lambda layer, then write a `.tfvars` file for the deploy script:

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
terraform plan -var-file=prod.tfvars -var-file="$ARTIFACT_VARS" -out=tfplan
```

### Docker ECR Build

Key patterns: source-hash tags, skip-if-tag-exists, ECR login, and an optional `$1` argument for the repo URL.

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
print_error()   { printf "\033[0;31m[ERROR]\033[0m   %s\n" "$1"; }

for cmd in aws docker shasum; do
  if ! command -v "$cmd" &>/dev/null; then
    print_error "$cmd is not installed"; exit 1
  fi
done

# Source-hash tag: deterministic, content-based, immutable
calculate_source_hash() {
  (
    cd "$APP_DIR"
    find . -type f \
      ! -path './.venv/*' ! -path './__pycache__/*' ! -name '*.pyc' \
      -print | LC_ALL=C sort | while IFS= read -r file; do
        shasum -a 256 "$file"
      done
  ) | shasum -a 256 | awk '{print substr($1,1,12)}'
}

IMAGE_TAG="${IMAGE_TAG:-sha-$(calculate_source_hash)}"
[[ "$IMAGE_TAG" == "latest" ]] && { print_error "'latest' is not valid; ECR uses immutable tags."; exit 1; }

# Accept repo URL as argument or fall back to terraform output
if [[ -n "${1:-}" ]]; then
  ECR_REPO_URL="$1"
else
  ECR_REPO_URL="$(cd "$REPO_ROOT/Terraform/environments/prod/<stack>" && terraform output -raw <service>_ecr_repository_url)"
fi

AWS_ACCOUNT_ID="$(echo "$ECR_REPO_URL" | cut -d'.' -f1)"
AWS_REGION="$(echo "$ECR_REPO_URL" | cut -d'.' -f4)"
ECR_REPO_NAME="$(echo "$ECR_REPO_URL" | cut -d'/' -f2)"

write_artifact_vars() {
  mkdir -p "$BUILD_DIR"
  cat >"$ARTIFACT_VARS" <<EOF
<service>_image_tag = "$IMAGE_TAG"
EOF
}

# Skip build if tag already exists in ECR (immutable tags make this safe)
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

---

## Orchestrators

### deploy.sh

Uses `SKIP_STACKS` for partial re-runs and a `FAILED_STACK` trap for clear failure context:

```bash
#!/usr/bin/env bash
# Deploy all stacks in dependency order
#
# Environment variables:
#   CI=true         — auto-approve all applies
#   IMAGE_TAG=<tag> — Docker image tag for ECS services
#   SKIP_STACKS     — comma-separated stacks to skip (e.g. "s3,network")
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
# needs — include docker/git here when any stack it runs builds images, so the
# run fails fast at the top instead of three stacks deep.
for cmd in terraform aws docker git; do
  if ! command -v "$cmd" &>/dev/null; then print_error "$cmd is not installed"; exit 1; fi
done
if ! aws sts get-caller-identity &>/dev/null; then
  print_error "AWS credentials are not configured"; exit 1
fi

echo ""
print_info "Deploy order: <stack-1> → <stack-2> → ..."
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

run_stack "s3"       1 N "create-s3.sh"
run_stack "network"  2 N "deploy-network.sh"
# ...

echo ""
print_success "════════════════════════════════════════"
print_success "  All stacks deployed successfully!"
print_success "════════════════════════════════════════"
echo ""
print_info "To skip already-deployed stacks on re-run:"
print_info "  SKIP_STACKS=s3,network ./scripts/deploy.sh"
```

### destroy.sh

Passes `SKIP_CONFIRM=true` as an inline env prefix (not `export`) — the orchestrator owns the single top-level confirmation gate:

```bash
#!/usr/bin/env bash
# Destroy all infrastructure in reverse dependency order
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
print_warning "This will destroy all infrastructure:"
print_warning "  1. <stack-N>"
print_warning "  ..."
print_warning "  N. s3 (data bucket)"
echo ""
print_warning "NOT destroyed: state bucket s3://$STATE_BUCKET (prevent_destroy = true)"
echo ""

if [[ "${CI:-}" != "true" ]]; then
  read -p "Type 'DESTROY' to confirm: " -r
  echo ""
  [[ "$REPLY" != "DESTROY" ]] && { print_info "Cancelled"; exit 0; }
fi

# Reverse dependency order
# Add `sleep 30` between stacks where ENI/task cleanup needs time to settle
SKIP_CONFIRM=true "$SCRIPT_DIR/destroy-<stack-N>.sh"
# ...
SKIP_CONFIRM=true "$SCRIPT_DIR/destroy-<stack-1>.sh"
SKIP_CONFIRM=true "$SCRIPT_DIR/destroy-s3.sh"

echo ""
print_success "════════════════════════════════════════"
print_success "  All stacks destroyed."
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

---

## CI / Environment Variables

| Variable | Used by | Effect |
|---|---|---|
| `CI=true` | all | Auto-approve deploys, skip interactive prompts |
| `SKIP_CONFIRM=true` | destroy scripts | Skip `DESTROY` confirmation (set by `destroy.sh` orchestrator) |
| `SKIP_STACKS` | `deploy.sh` | Comma-separated stack names to skip |
| `IMAGE_TAG` | build scripts | Docker image tag; defaults to short content hash |
| `<SERVICE>_IMAGE_TAG` | build scripts | Per-service override when multiple images are deployed |
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
2. Copy the nearest similar destroy script → `destroy-<stack>.sh`; update paths, warning bullet list, and add ENI diagnostics if the stack runs in a VPC.
3. If the stack uses Docker images: create `build-<service>.sh`; add the ECR-first targeting section to the deploy script.
4. Add to `deploy.sh` in the correct position with a progress banner. Add to `destroy.sh` in reverse order.
5. `chmod +x scripts/deploy-<stack>.sh scripts/destroy-<stack>.sh`
