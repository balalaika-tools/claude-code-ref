---
name: deploy-scripts
description: Conventions and patterns for writing shell scripts that wrap Terraform stacks (deploy-*.sh, destroy-*.sh, build-and-push.sh, and the top-level deploy.sh / destroy.sh orchestrators). Use whenever creating a new per-stack script, adding scripts for a newly added Terraform stack, modifying or reviewing any script in `scripts/`, wiring up CI-aware Terraform workflows, or debugging confirmation prompts / idempotent destroys. Apply even when the user just says things like "add a script for the new stack", "the destroy script is broken", or "how should I structure this deploy?".
---

# Deploy & Destroy Script Conventions

Each Terraform stack in `Terraform/environments/` gets **two dedicated scripts**: `deploy-<stack>.sh` and `destroy-<stack>.sh`. On top of those, a pair of orchestration scripts — `deploy.sh` and `destroy.sh` — run all stacks in the correct dependency order with a single command.

All scripts follow a strict, consistent structure so they work identically locally and in CI pipelines.

## File Naming

| Pattern | Purpose |
|---|---|
| `create-<stack>.sh` / `deploy-<stack>.sh` | Deploy or create a stack |
| `destroy-<stack>.sh` | Tear down a specific stack |
| `destroy.sh` | Nuclear option — destroys all stacks in reverse order |
| `build-and-push.sh` | Docker image build + push (called by deploy scripts, usable standalone) |

## Canonical Script Structure

### 1. Header

```bash
#!/usr/bin/env bash
# One-line description of what the script does
# (optional multi-line prerequisites list)
set -euo pipefail
```

Use `#!/usr/bin/env bash` (not `#!/bin/bash`) so the script picks up whatever `bash` is on `PATH` — macOS ships an ancient `/bin/bash` (3.2) that lacks features we rely on, and CI images vary. `set -euo pipefail` makes the script fail fast on errors, unset vars, and broken pipes — Terraform workflows are destructive enough that silently continuing past a failure is worse than exiting.

### 2. Path Resolution

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TF_DIR="$REPO_ROOT/Terraform/environments/prod/<stack>"
BACKEND_CONFIG="$REPO_ROOT/Terraform/backend-config/prod/<stack>.backend.hcl"
TFVARS="$TF_DIR/prod.tfvars"
TF_PLAN="$TF_DIR/tfplan"
```

Resolve paths relative to `${BASH_SOURCE[0]}` so the script works regardless of where the caller invokes it from — CI runners, other scripts, and humans all call these from different working directories. Relying on `$PWD` silently breaks in each of those cases.

### 3. Helper Functions

Paste these verbatim in every script — do not extract them to a shared `lib.sh`:

```bash
# ── Helpers ───────────────────────────────────────────────────────────────────
print_info()    { printf "\033[0;34m[INFO]\033[0m    %s\n" "$1"; }
print_success() { printf "\033[0;32m[SUCCESS]\033[0m %s\n" "$1"; }
print_warning() { printf "\033[0;33m[WARNING]\033[0m %s\n" "$1"; }
print_error()   { printf "\033[0;31m[ERROR]\033[0m   %s\n" "$1"; }
```

Why no shared sourcing: each script needs to be runnable standalone (a human grabbing one out of a repo, CI invoking just one stage, copy-pasted into a runbook). Sourcing a sibling file adds a failure mode (“file not found / wrong path”) for a handful of trivial printf lines. The duplication is intentional — it buys auditability and portability.

### 4. Pre-flight Checks

```bash
# ── Pre-flight ────────────────────────────────────────────────────────────────
for cmd in terraform aws; do          # add docker if the script builds images
  if ! command -v "$cmd" &>/dev/null; then
    print_error "$cmd is not installed"
    exit 1
  fi
done

if ! aws sts get-caller-identity &>/dev/null; then
  print_error "AWS credentials are not configured"
  exit 1
fi
```

Check every required binary. Check AWS credentials. Fail fast with a clear message.

### 5. Deploy Workflow (deploy scripts only)

```bash
cd "$TF_DIR"

# Step 1 — Init
print_info "Initializing Terraform (<stack>)..."
terraform init -input=false -backend-config="$BACKEND_CONFIG"

print_info "Validating..."
terraform validate

print_info "Formatting check..."
FMT_PATHS=("$TF_DIR" "$REPO_ROOT/Terraform/modules/<stack>")
if ! terraform fmt -check -recursive "${FMT_PATHS[@]}" >/dev/null 2>&1; then
  if [[ "${CI:-}" == "true" ]]; then
    print_error "Terraform formatting issues found; run terraform fmt locally"
    exit 1
  fi
  print_warning "Formatting issues found, auto-fixing..."
  terraform fmt -recursive "${FMT_PATHS[@]}"
fi

# Step 2 — Plan
trap 'rm -f "$TF_PLAN"' EXIT
terraform plan -input=false -var-file="$TFVARS" -out="$TF_PLAN"

# Step 3 — Apply (CI-aware)
if [[ "${CI:-}" == "true" ]]; then
  print_info "CI detected — auto-approving..."
  terraform apply -input=false "$TF_PLAN"
else
  print_info "Review the plan above."
  read -r -p "Apply? (yes/no): "
  if [[ "$REPLY" == "yes" ]]; then
    terraform apply -input=false "$TF_PLAN"
  else
    print_info "Cancelled"
    exit 0
  fi
fi
```

Use a trap so `tfplan` is cleaned up on success, cancellation, and failed applies. In CI, do not auto-format files; fail with a clear message so the pipeline does not mutate the working tree.

### 6. Confirmation Gate (destroy scripts only)

```bash
# ── Confirmation ──────────────────────────────────────────────────────────────
if [[ "${CI:-}" != "true" && "${SKIP_CONFIRM:-}" != "true" ]]; then
  echo ""
  print_warning "This will destroy the <STACK> stack:"
  print_warning "  - Resource A"
  print_warning "  - Resource B"
  echo ""
  read -r -p "Type 'DESTROY' to confirm: "
  echo ""
  if [[ "$REPLY" != "DESTROY" ]]; then
    print_info "Cancelled"
    exit 0
  fi
fi
```

Use `DESTROY` (all caps) as the confirmation token for standard stacks. Use `DESTROY-BACKEND` only for the S3/state bucket (extra friction because losing the state bucket is catastrophic — Terraform loses track of every resource it manages). The all-caps token also defeats muscle memory: typing `yes` by reflex won't pass.

### 7. Destroy Workflow (destroy scripts only)

```bash
# ── Destroy ───────────────────────────────────────────────────────────────────
if [[ ! -d "$TF_DIR" ]]; then
  print_warning "Directory $TF_DIR does not exist, skipping"
  exit 0
fi

cd "$TF_DIR"

print_info "Initializing Terraform (<stack>)..."
terraform init -input=false -backend-config="$BACKEND_CONFIG" >/dev/null

# Guard: skip if no state exists (idempotent destroy)
if ! terraform state list >/dev/null 2>&1 || [[ -z "$(terraform state list 2>/dev/null)" ]]; then
  print_info "No resources in <stack> state, skipping"
  exit 0
fi

print_info "Destroying <stack> stack..."
terraform destroy -auto-approve -input=false -var-file="$TFVARS"
print_success "<Stack> stack destroyed"
```

Destroy scripts are always idempotent: if the directory or state is missing, exit 0. Idempotency matters because `destroy.sh` orchestrates all stacks in sequence — if one has already been torn down, the orchestrator must continue cleanly instead of halting the rest of the teardown.

### 8. Summary Banner (deploy scripts)

End every deploy script with a visual summary and the most useful outputs:

```bash
echo ""
print_success "════════════════════════════════════════"
print_success "  <Stack> deployed!"
print_success "════════════════════════════════════════"

SOME_OUTPUT=$(terraform output -raw some_key 2>/dev/null || echo "N/A")
echo ""
print_info "Some output: $SOME_OUTPUT"
```

## CI / Automation Behaviour

| Variable | Effect |
|---|---|
| `CI=true` | Bypasses interactive `read` prompts; deploy scripts apply saved plans non-interactively, destroy scripts use `-auto-approve` |
| `SKIP_CONFIRM=true` | Bypasses the `DESTROY` confirmation in destroy scripts (for `destroy.sh` orchestration) |

Never hard-code `-auto-approve` in deploy scripts — always gate it on `$CI`.

## Environment Variables (common)

| Variable | Used by | Purpose |
|---|---|---|
| `CI` | all | Auto-approve / skip prompts |
| `SKIP_CONFIRM` | destroy scripts | Skip `DESTROY` prompt |
| `IMAGE_TAG` | build-and-push, deploy-app | Docker image tag; defaults to short git SHA |
| `ALLOW_DIRTY_DEPLOY` | build-and-push | Allow pushing from a dirty working tree |
| `TF_VAR_*` | deploy scripts | Pass sensitive Terraform variables without a tfvars file |

## Stack Dependency Order

**Deploy (in order):**
```
s3 → network → ec2 → app → orchestration → feeder
```

**Destroy (reverse):**
```
feeder → orchestration → app → ec2 → network → s3
```

`destroy.sh` always runs in the correct reverse order and includes a `sleep 30` between `app` and `ec2` to allow ENI cleanup.

## Script Set for a Project

Every project must have **one script per stack** plus the two orchestrators:

```
scripts/
├── deploy-<stack-1>.sh      # per-stack deploy
├── destroy-<stack-1>.sh     # per-stack destroy
├── deploy-<stack-2>.sh
├── destroy-<stack-2>.sh
├── ...
├── deploy.sh                # orchestrator: deploys all stacks in dependency order
└── destroy.sh               # orchestrator: destroys all stacks in reverse order
```

### deploy.sh (orchestrator)

Calls each per-stack deploy script in dependency order. Does **not** re-implement any logic — it just delegates:

```bash
#!/usr/bin/env bash
# Deploy all stacks in dependency order
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/deploy-<stack-1>.sh"
"$SCRIPT_DIR/deploy-<stack-2>.sh"
# ...
```

### destroy.sh (orchestrator)

Calls per-stack destroy scripts in **reverse** dependency order. Passes `SKIP_CONFIRM=true` so each script skips its individual prompt (the orchestrator shows a single top-level prompt instead):

```bash
#!/usr/bin/env bash
# Destroy all stacks in reverse dependency order
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_warning() { printf "\033[0;33m[WARNING]\033[0m %s\n" "$1"; }
print_info()    { printf "\033[0;34m[INFO]\033[0m    %s\n" "$1"; }

if [[ "${CI:-}" != "true" && "${SKIP_CONFIRM:-}" != "true" ]]; then
  echo ""
  print_warning "This will destroy ALL stacks."
  read -r -p "Type 'DESTROY' to confirm: "
  echo ""
  if [[ "$REPLY" != "DESTROY" ]]; then
    print_info "Cancelled"
    exit 0
  fi
fi

export SKIP_CONFIRM=true   # child scripts inherit this, so they skip their own prompts

# Reverse dependency order
"$SCRIPT_DIR/destroy-<stack-N>.sh"
# ... (add `sleep 30` between stacks if ENI/dependency cleanup is needed — e.g. between app and ec2)
"$SCRIPT_DIR/destroy-<stack-1>.sh"
```

The single top-level `DESTROY` prompt plus an `export`-based opt-out is cleaner than per-call `SKIP_CONFIRM=true` prefixes: one place to reason about confirmation, and child scripts remain unchanged whether invoked standalone or by the orchestrator.

## Adding a New Stack Script Pair

1. Copy `deploy-feeder.sh` → `deploy-<stack>.sh`, update `TF_DIR`, `BACKEND_CONFIG`, module path, and summary outputs.
2. Copy `destroy-feeder.sh` → `destroy-<stack>.sh`, update the same paths and the warning bullet list.
3. Add `deploy-<stack>.sh` to `deploy.sh` in the correct position in the dependency order.
4. Add `destroy-<stack>.sh` to `destroy.sh` in the correct position in the reverse-order sequence.
5. `chmod +x scripts/deploy-<stack>.sh scripts/destroy-<stack>.sh`
