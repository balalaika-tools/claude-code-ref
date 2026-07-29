# Orchestrators: `deploy.sh`, `deploy-platform.sh`, `destroy.sh`, `_stacks.sh`

`deploy.sh` is **environment bring-up and disaster recovery, not the CD path.**
No release runs it. `deploy-platform.sh` applies the platform tier and is what
the infrastructure workflow runs on merge. A service release applies exactly one
app stack through its own script — see
[`ci-workflows.md`](ci-workflows.md).

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
- [deploy-platform.sh](#deploy-platformsh)
- [destroy.sh](#destroysh)
- [Restate Surviving Resources](#restate-surviving-resources)

## The Shared Stack List

The list has two sections. Platform stacks are **ordered** — each one depends on
the ones above it. App stacks are **unordered siblings**: they depend on the
platform tier and never on each other, so their relative position carries no
meaning.

```bash
# scripts/_stacks.sh — single source of truth for stack order.
# deploy.sh iterates it forwards; destroy.sh iterates it backwards.
# Sourced only by the orchestrators — per-stack scripts stay standalone.

# Platform tier — dependency order matters. Applied by deploy-platform.sh.
PLATFORM_STACKS=(
  "state:create-state.sh:destroy-state.sh"
  "platform-network:deploy-platform-network.sh:destroy-platform-network.sh"
  "platform-data:deploy-platform-data.sh:destroy-platform-data.sh"
  "platform-ecr:deploy-platform-ecr.sh:destroy-platform-ecr.sh"
)

# Application tier — order is arbitrary; one entry per releasable service.
APP_STACKS=(
  "app-api:deploy-app-api.sh:destroy-app-api.sh"
  "app-worker:deploy-app-worker.sh:destroy-app-worker.sh"
  # "app-<service>:deploy-app-<service>.sh:destroy-app-<service>.sh"
)

STACKS=("${PLATFORM_STACKS[@]}" "${APP_STACKS[@]}")
```

The `<name>:<deploy>:<destroy>` triple keeps a stack's name and both of its
scripts on one line, so adding a stack is one edit in one place and the reverse
order cannot fall out of sync. `STACKS` preserves the existing contract for
`deploy.sh` and `destroy.sh`; `deploy-platform.sh` iterates `PLATFORM_STACKS`
only.

If a repository sits below the split threshold and has one combined stack, keep a
single `STACKS` array and skip the two-section structure. Do not manufacture a
platform/app split in the stack list that does not exist in the Terraform tree.

Where a build script must run between two stacks during bring-up — ECR before the
build, the app stack after it — call it inline in `deploy.sh` rather than adding
it to an array; it is not a stack and has no destroy counterpart:

```bash
run_stack "platform-ecr" 1 N "deploy-platform-ecr.sh"
"$SCRIPT_DIR/build-<service>.sh"
run_stack "app-<service>" 2 N "deploy-app-<service>.sh"
```

In a release this sequencing does not arise: the build script and the single app
stack run in the same job, and ECR already exists.

**In a split repository this inline call has no equivalent — delete it.** This
repository has no application source to build. Bring-up becomes three steps:
apply the platform tier, release each service once from its own repository against
the new environment, then run `deploy.sh` with every artifact file present. Do not
replace the call with a cross-repository clone-and-build; that needs credentials
for every application repository and reassembles the blast radius the split
removed. Add the artifact-file pre-flight from
[`split-repo-releases.md`](split-repo-releases.md) so a missing release fails at
the top of `deploy.sh` with the service named, rather than as an opaque "no value
for required variable" several stacks in.

## deploy.sh

Uses `SKIP_STACKS` for partial re-runs and a `FAILED_STACK` trap for clear
failure context:

```bash
#!/usr/bin/env bash
# Bring up every stack in dependency order. Bring-up and DR only — not the CD path.
#
# Environment variables:
#   ENV=<dev|staging|prod> — target environment (required everywhere)
#   CI=true                — apply without an interactive prompt
#   IMAGE_TAG=<tag>        — Docker image tag for ECS services
#   SKIP_STACKS            — comma-separated stacks to skip on a partial re-run
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

`SKIP_STACKS` exists for **partial bring-up re-runs**, when an earlier attempt
failed halfway. It has no role in a release: a release applies one app stack, so
there is nothing to skip. Do not add it to a release workflow.

## deploy-platform.sh

The platform-tier orchestrator, and the one an infrastructure workflow actually
runs on merge. Same structure as `deploy.sh` with two differences: it iterates
`PLATFORM_STACKS`, and it refuses to touch an app stack.

```bash
#!/usr/bin/env bash
# Apply the platform tier in dependency order
#
# Environment variables:
#   ENV=<dev|staging|prod> — target environment (required)
#   CI=true                — apply without an interactive prompt
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ENV="${ENV:?Set ENV before deployment}"
source "$SCRIPT_DIR/_stacks.sh"

# Paste the four print_* helpers verbatim (SKILL.md -> Helper Functions).
# Reuse should_skip, run_stack, and the FAILED_STACK trap from deploy.sh.

TOTAL="${#PLATFORM_STACKS[@]}"
INDEX=0
for entry in "${PLATFORM_STACKS[@]}"; do
  INDEX=$((INDEX + 1))
  IFS=':' read -r name deploy_script _ <<<"$entry"
  run_stack "$name" "$INDEX" "$TOTAL" "$deploy_script"
done

print_success "Platform tier applied ($ENV)"
print_info "Application stacks release independently; this run did not touch them."
```

The closing line matters. An operator who just applied the platform tier needs to
know that nothing shipped for any service, so a release that was waiting on new
platform capacity still has to run.

Bootstrap is deliberately excluded from this script even though `create-state.sh`
appears in `PLATFORM_STACKS`: it runs on a local backend, once per project, by a
human. Either drop it from the loop with an explicit `should_skip` entry or keep
it first and accept that it exits early as a no-op once the bucket exists.

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
