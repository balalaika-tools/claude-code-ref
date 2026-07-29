# Orchestrators: `deploy.sh`, `destroy.sh`, `_stacks.sh`

`deploy.sh` and `destroy.sh` are the one place scripts share state: a single
ordered stack list, so destroy order is always the exact reverse of deploy order
— not two hand-maintained lists that can silently drift apart.

This is the narrow exception to the standalone rule in `SKILL.md`. The
orchestrators never run standalone by definition — they call the per-stack
scripts — so they may source one shared file for stack order. Per-stack scripts
still source nothing.

## Contents

- [The Shared Stack List](#the-shared-stack-list)
- [deploy.sh](#deploysh)
- [destroy.sh](#destroysh)
- [Restate Surviving Resources](#restate-surviving-resources)

## The Shared Stack List

```bash
# scripts/_stacks.sh — single source of truth for stack order.
# deploy.sh iterates it forwards; destroy.sh iterates it backwards.
# Sourced only by the two orchestrators — per-stack scripts stay standalone.
STACKS=(
  "s3:create-s3.sh:destroy-s3.sh"
  "ecr:deploy-ecr.sh:destroy-ecr.sh"
  "network:deploy-network.sh:destroy-network.sh"
  # "<stack>:deploy-<stack>.sh:destroy-<stack>.sh"
)
```

The `<name>:<deploy>:<destroy>` triple keeps a stack's name and both of its
scripts on one line, so adding a stack is one edit in one place and the reverse
order cannot fall out of sync.

Where a build script must run between two stacks — ECR before the build, the
service after it — call it inline in `deploy.sh` rather than adding it to
`STACKS`; it is not a stack and has no destroy counterpart:

```bash
run_stack "ecr"        1 N "deploy-ecr.sh"
"$SCRIPT_DIR/build-<service>.sh"
run_stack "<service>"  2 N "deploy-<service>.sh"
```

## deploy.sh

Uses `SKIP_STACKS` for partial re-runs and a `FAILED_STACK` trap for clear
failure context:

```bash
#!/usr/bin/env bash
# Deploy all stacks in dependency order
#
# Environment variables:
#   ENV=<dev|staging|prod> — target environment (required everywhere)
#   CI=true                — auto-approve all applies
#   IMAGE_TAG=<tag>         — Docker image tag for ECS services
#   SKIP_STACKS             — comma-separated stacks to skip (e.g. "s3,network")
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ENV="${ENV:?Set ENV before deployment}"
source "$SCRIPT_DIR/_stacks.sh"

# Paste the four print_* helpers verbatim (SKILL.md -> Helper Functions).

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

`FAILED_STACK` is set before each child script and cleared after it, so the
`EXIT` trap prints a name only when a stack actually failed. A trap that fired
unconditionally would print "Deployment failed" on a clean run and on a
deliberate cancellation.

Export `ENV` explicitly before invoking child scripts. A shell variable created
inside the orchestrator is not exported automatically, and every per-stack script
requires `ENV`.

## destroy.sh

Iterates `_stacks.sh` in reverse — no second hand-maintained list to keep in sync
with `deploy.sh`. Passes `SKIP_CONFIRM=true` as an inline env prefix (not
`export`) — the orchestrator owns the single top-level confirmation gate:

```bash
#!/usr/bin/env bash
# Destroy all infrastructure in reverse dependency order
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ENV="${ENV:?Set ENV before destruction}"
source "$SCRIPT_DIR/_stacks.sh"

STATE_BUCKET="${STATE_BUCKET:-<project>-tfstate-<account-id>-<region>}"

# Paste the four print_* helpers verbatim (SKILL.md -> Helper Functions).

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

`SKIP_CONFIRM=true` is an inline prefix on the child invocation rather than an
exported variable, so it applies to exactly that call. Exporting it would leave
every later command in the shell — including anything a child script itself
invokes — silently unconfirmable.

Unlike `deploy.sh`, this loop has no skip mechanism and no failure trap: each
destroy script is already idempotent (missing directory or empty state → exit 0),
so a re-run after a partial teardown is safe without one.

## Restate Surviving Resources

**Always restate surviving resources in the closing summary, not just the upfront
gate.** Anything a destroy intentionally leaves behind — the Terraform state
bucket (`prevent_destroy`), retained data buckets, snapshots, log groups with
retention — must be echoed *after* teardown completes, naming the concrete
resource (e.g. the actual bucket name), because that is the moment the operator
decides what to remove by hand. A warning that scrolled past 10 minutes and
several `DESTROY` confirmations ago is not a reminder.
