---
name: deploy-scripts
description: Conventions and patterns for writing shell scripts that wrap Terraform stacks (deploy-*.sh, destroy-*.sh, build-*.sh, and the top-level deploy.sh / destroy.sh orchestrators). Use whenever creating a new per-stack script, adding scripts for a newly added Terraform stack, modifying or reviewing any script in `scripts/`, wiring up CI-aware Terraform workflows, or debugging confirmation prompts / idempotent destroys. Apply even when the user just says things like "add a script for the new stack", "the destroy script is broken", or "how should I structure this deploy?".
---

# Deploy & Destroy Script Conventions

Each logical Terraform stack gets two dedicated scripts:
`deploy-<stack>.sh` and `destroy-<stack>.sh`. A pair of orchestration scripts —
`deploy.sh` and `destroy.sh` — run stacks in dependency order. Stacks with
container images also get a `build-<service>.sh`.

Every script supports two callers with one code path: a human running it locally, and CI (GitHub Actions) running it unattended. `${CI:-}` is the only branch between them — see [Deploy Workflow](#deploy-workflow) and [CI Integration](#ci-integration-github-actions). Locally you see the plan and approve it; in CI the plan is generated and applied without a prompt, gated instead by whatever branch/environment protection rules the workflow itself enforces.

These scripts wrap the conventions in the sibling `terraform-aws` skill — this doc
covers the shell layer (environment/root selection, local metadata isolation,
workflow, confirmation gates, and CI branching). Read both together when adding
a stack. The `terraform-aws` skill normally creates one shared root plus environment
values and backend files; this skill creates the scripts that select it safely.
For a genuine topology difference, the logical stack maps to one of a small,
reviewed set of compatible roots.

Read the focused references when applicable:

- Lambda/Docker artifact builds and pre-deploy S3 uploads:
  [`references/build-scripts.md`](references/build-scripts.md)
- Full `deploy.sh` / `destroy.sh` / `_stacks.sh` listings:
  [`references/orchestrators.md`](references/orchestrators.md)
- ECS drain and stuck-ENI destroy diagnostics:
  [`references/destroy-troubleshooting.md`](references/destroy-troubleshooting.md)
- The local-backend state-bucket stack:
  [`references/bootstrap-stack.md`](references/bootstrap-stack.md)

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

A stack that owns both an ECR repo and the service that pushes to it (ECS, Lambda) splits into two stacks: `ecr` and the service. ECR repos are created once and almost never destroyed; the service stack churns on every deploy. Giving them separate lifecycles means a normal deploy never needs `-target` — see [ECR as its own Stack](#ecr-as-its-own-stack).

---

## Script Structure

### Header

```bash
#!/usr/bin/env bash
# One-line description
set -euo pipefail
```

`#!/usr/bin/env bash` picks up whatever `bash` is on `PATH` — macOS ships an ancient `/bin/bash` (3.2). `set -euo pipefail` fails fast on errors, unset vars, and broken pipes.

### Path Resolution

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV="${ENV:?Set ENV to a supported environment, for example dev, staging, or prod}"
LOGICAL_STACK="<stack>"
ROOT_STACK="<stack>" # May differ by environment for an explicit topology variant.
TF_DIR="$REPO_ROOT/Terraform/stacks/$ROOT_STACK"
VAR_FILE="$REPO_ROOT/Terraform/environments/$ENV/$LOGICAL_STACK.tfvars"
BACKEND_CONFIG="$REPO_ROOT/Terraform/backend-config/$ENV/$LOGICAL_STACK.backend.hcl"
export TF_DATA_DIR="$REPO_ROOT/.terraform-data/$ENV/$LOGICAL_STACK/$ROOT_STACK"
PLAN_FILE="$TF_DATA_DIR/tfplan"
```

Always resolve paths from `${BASH_SOURCE[0]}` — not `$PWD`. CI runners,
orchestrators, and humans invoke scripts from different working directories.
Use absolute paths for environment values and backend configuration.

Require `ENV` for every mutating workflow. Never default to production. Validate
it against the environments the repository actually supports:

```bash
case "$ENV" in dev|staging|prod) ;; *) print_error "ENV must be dev, staging, or prod"; exit 1 ;; esac
```

`TF_DATA_DIR` is load-bearing when environments share one stack root. It keeps
backend metadata separate so a prior staging initialization cannot silently
select staging state during a production command. Including `ROOT_STACK` also
prevents different topology implementations from sharing provider/module
metadata. Gitignore `.terraform-data/`.

When an environment uses a genuinely different root implementation, each
standalone deploy and destroy wrapper maps it explicitly without changing the
logical stack/output contract:

```bash
case "$ENV" in
  staging) ROOT_STACK="database-rds" ;;
  prod)    ROOT_STACK="database-aurora" ;;
  *) print_error "No database root is configured for ENV=$ENV"; exit 1 ;;
esac
```

Do not accept an unrestricted `ROOT_STACK` or `DATABASE_ROOT_STACK` override:
the mapping is part of the reviewed deployment policy. Keep backend and tfvars
names under the logical `database` stack, but ensure the selected roots never
share a backend state object. If an environment changes implementations later,
perform an explicit state/consumer cutover; never let both roots manage the same
SSM parameter, DNS record, or other discovery object concurrently.

### Helper Functions

Paste these four verbatim in every script — do not source them from a shared lib:

```bash
print_info()    { printf "\033[0;34m[INFO]\033[0m    %s\n" "$1"; }
print_success() { printf "\033[0;32m[SUCCESS]\033[0m %s\n" "$1"; }
print_warning() { printf "\033[0;33m[WARNING]\033[0m %s\n" "$1"; }
print_error()   { printf "\033[0;31m[ERROR]\033[0m   %s\n" "$1"; }
```

Every listing in the references marks where these go with a comment rather than
repeating them, so there is exactly one copy to keep correct. Paste all four even
if a given script calls only two — a later edit that adds a `print_warning` call
to a script missing the definition fails under `set -u`.

Each script must be runnable standalone. Sourcing a sibling file adds a failure mode (file not found, wrong path) for a handful of printf lines. The duplication buys portability and auditability.

This standalone rule is about per-stack `deploy-*.sh` / `destroy-*.sh` scripts, which are meant to run in isolation. The orchestrators (`deploy.sh`, `destroy.sh`) are a narrow exception: they never run standalone by definition — they call the per-stack scripts — so they share one file for stack order. See [Orchestrators](#orchestrators).

### Pre-flight Checks

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

### Deploy Workflow

```bash
cd "$TF_DIR"

# Fires on every exit path — success, cancellation, or a failed apply — so a
# stale tfplan never survives a crash. (Cleaning up per-branch instead of with
# trap looks clearer but misses the failure path: `terraform apply` can exit
# non-zero before any explicit `rm -f` runs.)
trap 'rm -f "$PLAN_FILE"' EXIT

print_info "Initializing Terraform ($ENV/<stack>)..."
terraform init -reconfigure -backend-config="$BACKEND_CONFIG" -input=false

print_info "Validating..."
terraform validate

print_info "Formatting check..."
if ! terraform fmt -check -recursive "$REPO_ROOT/Terraform" >/dev/null 2>&1; then
  print_error "Terraform formatting issues found; run terraform fmt -recursive Terraform"
  exit 1
fi

print_info "Planning..."
terraform plan -input=false -lock-timeout=5m \
  -var-file="$VAR_FILE" -out="$PLAN_FILE"
# Add -var-file="$ARTIFACT_VARS" if the stack consumes build artifacts

if [[ "${CI:-}" == "true" ]]; then
  print_info "CI detected — auto-approving..."
  terraform apply -input=false "$PLAN_FILE"
else
  print_info "Review the plan above."
  read -p "Apply? (yes/no): " -r
  if [[ "$REPLY" == "yes" ]]; then
    terraform apply -input=false "$PLAN_FILE"
  else
    print_info "Cancelled"
    exit 0
  fi
fi
```

Use `-input=false` on every `init`/`plan`/`apply` call so a missing value fails
loudly instead of hanging in CI. Use a bounded lock timeout. Apply the exact
saved plan; do not run a second implicit plan. `CI=true` may skip the terminal
prompt only when the workflow has an external approval policy. For stronger
production controls, separate plan and apply jobs and protect the plan artifact
as sensitive data.

### ECR as its own Stack

`-target` is Terraform's documented escape hatch for exceptional recovery, and it prints a warning every time it's used — it is not a pattern to build a routine deploy path around. Instead of targeting the ECR resources inside a combined stack, give ECR its own stack with its own lifecycle. `deploy-ecr.sh` is then an ordinary stack script — no targeting, no partial applies, every stack applies its whole plan.

The service stack reads the repository through `data "aws_ecr_repository"` or
another intentional published value rather than owning it. Avoid
`terraform_remote_state` unless the service deployment role may read the entire
ECR state snapshot.

The ordering — `ecr`, then the build script, then the service — is wired in
`deploy.sh`; see [`references/orchestrators.md`](references/orchestrators.md).

### Summary Banner (deploy scripts)

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

Init first, then show the *real* destroy plan — not just a hand-maintained bullet list — before the confirmation gate:

```bash
if [[ ! -d "$TF_DIR" ]]; then
  print_warning "Directory $TF_DIR does not exist, skipping"
  exit 0
fi

cd "$TF_DIR"

print_info "Initializing Terraform ($ENV/<stack>)..."
terraform init -reconfigure -backend-config="$BACKEND_CONFIG" -input=false >/dev/null

if ! terraform state list >/dev/null 2>&1 || [[ -z "$(terraform state list 2>/dev/null)" ]]; then
  print_info "No resources in <stack> state, skipping"
  exit 0
fi

DESTROY_PLAN_FILE="$TF_DATA_DIR/tfplan-destroy"
trap 'rm -f "$DESTROY_PLAN_FILE"' EXIT
print_warning "This will destroy the <STACK> stack ($ENV). Plan:"
terraform plan -destroy -input=false -lock-timeout=5m \
  -var-file="$VAR_FILE" -out="$DESTROY_PLAN_FILE"

if [[ "${CI:-}" != "true" && "${SKIP_CONFIRM:-}" != "true" ]]; then
  echo ""
  read -p "Type 'DESTROY' to confirm: " -r
  echo ""
  if [[ "$REPLY" != "DESTROY" ]]; then
    print_info "Cancelled"
    exit 0
  fi
fi

print_info "Destroying <stack> stack..."
terraform apply -input=false "$DESTROY_PLAN_FILE"
print_success "<Stack> stack destroyed"
```

A hardcoded "this will destroy: Resource A, Resource B" list drifts from the
stack. Generate and save the real destroy plan, then apply that exact plan after
confirmation. Use `DESTROY` for standard stacks and a specific token for
irreversible data loss.

Destroy scripts are always idempotent: missing directory or empty state → exit 0. The `destroy.sh` orchestrator runs stacks in sequence — a previously-torn-down stack must not halt the rest.

**Stacks that run workloads in a VPC need more than this.** ECS services must be
drained to zero before their security groups can go, and Lambda/ECS ENIs are the
usual cause of a destroy that hangs then fails. Both patterns — the drain loop
and the ENI diagnostic that replaces the final bare `terraform apply` — are in
[`references/destroy-troubleshooting.md`](references/destroy-troubleshooting.md).

---

## Orchestrators

`deploy.sh` and `destroy.sh` are the one place scripts share state: a single
ordered stack list in `scripts/_stacks.sh`, so destroy order is always the exact
reverse of deploy order — not two hand-maintained lists that can silently drift
apart. Adding a stack is one edit, in one place.

The rules that matter from outside those two files:

- `export ENV` before invoking child scripts; a variable created inside the
  orchestrator is not exported automatically.
- `destroy.sh` owns the single top-level `DESTROY` gate and passes
  `SKIP_CONFIRM=true` to children as an inline prefix, never an export.
- The orchestrator's pre-flight checks the **union** of tools every child needs,
  so a run fails at the top rather than three stacks deep.
- Build scripts are called inline between stacks — they are not stacks and have
  no destroy counterpart, so they do not belong in the stack list.
- Anything a teardown intentionally leaves behind must be restated in the
  closing summary, naming the concrete resource. That is when the operator
  decides what to delete by hand; the upfront warning scrolled past several
  confirmations ago.

Full listings, the `<name>:<deploy>:<destroy>` list format, `SKIP_STACKS`, and
the `FAILED_STACK` trap: [`references/orchestrators.md`](references/orchestrators.md).

---

## Build Scripts

`build-<service>.sh` produces an artifact and hands its version to Terraform
through a generated `.tfvars` file that the deploy script passes as a second
`-var-file`. Two rules regardless of artifact type:

- **Version explicitly.** Docker images are tagged with the Git SHA against an
  immutable ECR repository — never `latest` or a branch name. Lambda zips carry
  a `base64sha256` because the AWS API needs it to detect a real change.
- **The build runs before `terraform init`,** and its tfvars file must exist on
  every exit path, including the "artifact already published, nothing to do"
  short-circuit.

Full Lambda zip/layer and Docker/ECR listings, plus pre-deploy S3 asset uploads:
[`references/build-scripts.md`](references/build-scripts.md). For the
tag-versus-digest decision, read `references/docker-image-tagging.md` in the
sibling `terraform-aws` skill.

---

## The Bootstrap Exception

The state-bucket stack cannot use the standard workflow — the remote backend it
would use is the thing it creates. It runs on a local backend, imports
pre-existing buckets idempotently at runtime, and is the single place where the
imperative `terraform import` CLI is correct rather than a declarative `import`
block. Name it `create-<stack>.sh` so the exception is visible in the filename.

Set it up once per project: [`references/bootstrap-stack.md`](references/bootstrap-stack.md).

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

`CI=true` is what makes `deploy.sh`/`deploy-<stack>.sh` skip the interactive `read -p "Apply?"` and apply the plan unattended ([Deploy Workflow](#deploy-workflow)) — the approval gate moves from a terminal prompt to whatever branch protection / required-reviewers rule guards the workflow run itself (e.g. a GitHub Environment with required reviewers on `prod`). Locally, with `CI` unset, every script stops and shows the plan before applying. Same scripts, same code path — only the environment decides which gate applies.

---

## CI / Environment Variables

| Variable | Used by | Effect |
|---|---|---|
| `ENV` | all | Required target environment; validate against the environments the repository supports |
| `CI=true` | all | Auto-approve deploys, skip interactive prompts |
| `SKIP_CONFIRM=true` | destroy scripts | Skip `DESTROY` confirmation (set by `destroy.sh` orchestrator) |
| `SKIP_STACKS` | `deploy.sh` | Comma-separated stack names to skip |
| `IMAGE_TAG` | build scripts | Docker image tag; defaults to the current git SHA |
| `<SERVICE>_IMAGE_TAG` | build scripts | Per-service override when multiple images are deployed |
| `AWS_REGION` | build/destroy scripts | Explicit region; falls back to parsing tfvars/ECR URL locally only |
| `TF_VAR_*` | deploy scripts | Inject values without a tfvars file; secrets still enter state unless every consumer is ephemeral/write-only |

---

## Quality Gates

Every script declares `set -euo pipefail`, so latent quoting and unset-variable
bugs surface as hard failures at the worst possible time — mid-deploy. Lint
before committing:

- Run `shellcheck scripts/*.sh` and resolve findings (or annotate intentional
  ones with `# shellcheck disable=SCxxxx` plus a reason). It catches unquoted
  expansions, masked exit codes in pipelines, and `read` misuse that
  `pipefail` would otherwise only reveal at runtime.
- Run `chmod +x` on new scripts — a non-executable script invoked by an
  orchestrator fails with a confusing permission error.
- Optionally wire both into a pre-commit hook so they run automatically.

---

## Adding a New Stack

1. Copy the nearest similar deploy script → `deploy-<stack>.sh`; update
   `LOGICAL_STACK`, `ROOT_STACK`, `VAR_FILE`, `BACKEND_CONFIG`, and summary
   outputs.
2. Copy the nearest similar destroy script → `destroy-<stack>.sh`; update paths.
   **If the stack runs in a VPC, read
   [`references/destroy-troubleshooting.md`](references/destroy-troubleshooting.md)**
   and add the ECS drain loop and ENI diagnostics.
3. If the stack manages container images or Lambda artifacts: create an `ecr`
   stack (once, if the project doesn't have one yet) plus `build-<service>.sh`
   — **read [`references/build-scripts.md`](references/build-scripts.md)**. The
   service stack reads the repo URL from the `ecr` stack rather than owning it.
4. Add the stack to `_stacks.sh` in the correct position — **format and
   surrounding code in
   [`references/orchestrators.md`](references/orchestrators.md)**. If an
   environment selects a different root implementation, add an explicit
   `case "$ENV"` mapping in the per-stack wrappers and keep the logical output
   contract stable.
5. `chmod +x scripts/deploy-<stack>.sh scripts/destroy-<stack>.sh`
6. `shellcheck scripts/deploy-<stack>.sh scripts/destroy-<stack>.sh`
