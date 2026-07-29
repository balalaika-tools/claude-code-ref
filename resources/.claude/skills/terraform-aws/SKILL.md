---
name: terraform-aws
description: >-
  Create, modify, review, and refactor Terraform configurations for AWS
  deployments that use reusable modules, one root module per deployable stack,
  environment-specific values, and remote S3 state. Use for AWS Terraform
  modules, stack roots, backend configuration, provider upgrades, state-safe
  refactors, runtime secret-storage choices between SSM Parameter Store and AWS
  Secrets Manager, testing, and infrastructure reviews in repositories that
  adopt these conventions. Do not apply these AWS-specific conventions to
  non-AWS Terraform or replace an existing repository architecture unless the
  user asks for a migration.
---

# AWS Terraform Deployment Conventions

Use these conventions for repositories that keep Terraform under `Terraform/`.
Examples use that spelling, but first resolve the repository's actual
case-sensitive directory name (for example, `Terraform/` or `terraform/`) and
bind it to `TF_ROOT`; never create a second case variant. Treat a **stack** as
one independently initialized root module with one state boundary. This use of
"stack" does not mean the separate HashiCorp Terraform Stacks product.

Preserve established repository conventions unless the user explicitly requests
a migration. When this skill and repository-local instructions disagree, follow
the repository and call out the difference.

The companion `deploy-scripts` skill defines the shell wrappers that select an
environment, isolate Terraform's local metadata, plan, apply, and destroy these
stacks. In a normal installation both skills are siblings under
`.claude/skills/`. Read both skills when changing Terraform/script interfaces.
If the companion is unavailable, use
[`references/deploy-scripts-pattern.md`](references/deploy-scripts-pattern.md)
as the Terraform-side contract and do not invent wrapper behavior.

Read the focused references when applicable:

- Environment variants: [`references/environment-variants.md`](references/environment-variants.md)
- Container images: [`references/docker-image-tagging.md`](references/docker-image-tagging.md)
- SSM secrets: [`references/ssm-secrets-pattern.md`](references/ssm-secrets-pattern.md)
- Secrets Manager: [`references/secrets-manager-pattern.md`](references/secrets-manager-pattern.md)
- Wrapper interface: [`references/deploy-scripts-pattern.md`](references/deploy-scripts-pattern.md)

## Required Workflow

1. Inspect `CLAUDE.md`, `AGENTS.md`, and other repository-local instructions
   when present. Resolve `TF_ROOT`, then inspect the Terraform tree, every
   affected root's `required_version`, lockfiles, provider constraints, state
   boundaries, and nearby modules before designing changes. Treat a missing
   `required_version` as unknown compatibility, not permission to use the
   current CLI's features.
2. Resolve the target environment, AWS account, region, stack, and expected
   state path. Do not infer production as the default.
3. When the workload needs runtime secrets and the repository or user has not
   already selected a store, ask whether to use SSM Parameter Store or AWS
   Secrets Manager **for each target environment**. Offer an explicit mixed
   mapping such as `dev=ssm`, `staging=ssm`, and
   `prod=secrets-manager`; do not assume all environments must use the same
   service.
4. Decide whether the change is an environment value difference, a reusable
   module change, a state-safe refactor, or a genuinely different topology.
5. Preserve resource addresses where possible. Add `moved`, `import`, or
   `removed` blocks when state ownership or addresses change.
6. Run formatting, initialization without a backend, validation for every
   changed root and every root that consumes a changed module, appropriate
   tests, security/static checks, and a real plan for the target environment.
7. Do not run `apply`, `destroy`, imperative `import`, `state` mutations,
   `force-unlock`, or `-target` unless the user explicitly authorizes that
   operational action.

## Repository Layout

Prefer one root module per deployable stack and keep environment differences in
data files:

```text
Terraform/
├── backend-config/{env}/{stack}.backend.hcl
├── environments/{env}/{stack}.tfvars
├── stacks/{stack}/
│   ├── backend.tf
│   ├── main.tf
│   ├── outputs.tf
│   ├── providers.tf
│   ├── tests/
│   │   └── composition.tftest.hcl
│   ├── variables.tf
│   ├── versions.tf
│   └── .terraform.lock.hcl
├── modules/{component}/
│   ├── main.tf
│   ├── outputs.tf
│   ├── tests/
│   │   └── behavior.tftest.hcl
│   ├── variables.tf
│   ├── versions.tf
│   └── README.md
└── bootstrap/state/
    ├── {main,outputs,providers,variables,versions}.tf
    └── .terraform.lock.hcl
```

This layout gives supported environments the same tested resource graph without
copying root configuration or provider lockfiles. Express normal environment
differences such as database instance class, Multi-AZ, storage, backup
retention, ECS capacity, or log retention as typed input values.

The `tests/` directories are optional until useful behavior exists to assert.
Put reusable-module contract tests beside that module. Put stack tests beside
the stack only when they validate root composition, outputs, policies, or
environment-independent invariants; do not duplicate module tests in every
stack.

Keep environment differences explicit. If production truly uses a different
database product or resource graph, use a separate root implementation with the
same output contract instead of filling one root with fragile conditionals or
copying it per environment. For example, use `stacks/database-aurora/` and
`stacks/database-rds/`, selected by the deployment wrapper through an explicit,
closed environment mapping. See the environment-variants reference for the
decision rules, ownership-cutover rule, and examples.

Use stack boundaries for independently owned or promoted lifecycles, security
boundaries, and blast-radius reduction. Do not create a separate state merely
because code can be factored into a module. ECR is a useful separate stack
because repositories and images normally outlive frequently replaced services.

### Shared-Root Safety

Because all environments use the same stack directory, isolate Terraform's
local backend metadata:

```sh
export TF_DATA_DIR="$REPO_ROOT/.terraform-data/$ENV/$LOGICAL_STACK/$ROOT_STACK"
terraform -chdir="$TF_ROOT/stacks/$ROOT_STACK" init \
  -reconfigure \
  -backend-config="$TF_ROOT/backend-config/$ENV/$LOGICAL_STACK.backend.hcl"
```

Gitignore `.terraform-data/`. Use a distinct path per environment, logical
stack, and selected root. `-reconfigure` selects the declared backend without
offering to migrate another environment's state. Use `-migrate-state` only
during an intentional, reviewed backend migration.

## Root Modules and Reusable Modules

Keep root modules thin: configure providers and backends, discover stable
external dependencies, compose child modules, and expose intentional outputs.
Keep reusable modules focused on a cohesive capability rather than mirroring
stack names automatically.

For reusable modules:

- Declare every provider source and the minimum compatible provider version.
- Do not define `provider` blocks or credentials inside child modules.
- Accept dependency IDs and ARNs explicitly instead of performing hidden,
  environment-wide discovery inside the module.
- Give every variable a type and description; validate non-trivial invariants.
- Give every output a description and mark secret-bearing outputs sensitive.
- Keep module trees relatively flat and prefer composition in the root.
- Generate module interface documentation with `terraform-docs` when the
  module is intended for reuse.

Provider-native data sources are appropriate in roots when they select a stable,
uniquely identifiable external resource. Avoid broad tag queries that can match
multiple resources. Passing an account ID, region, or dependency ID into a
child module is an interface choice, not a requirement to ban all data sources.

## Versions and Dependencies

Choose the Terraform line and provider major after checking the repository,
release notes, and upgrade guides; never call a patch "latest" in long-lived
skill text. Read `required_version` before selecting a mechanism:

| Mechanism | Minimum Terraform | Compatibility note |
|---|---:|---|
| `moved` block | 1.1.0 | Use an authorized `state mv` only when an older root cannot be upgraded. |
| Preconditions and postconditions | 1.2.0 | These block on failure; `check` does not. |
| `check` and basic `import` blocks | 1.5.0 | `import` `for_each` requires 1.7.0. |
| Native `terraform test` | 1.6.0 | Tests can create real infrastructure. |
| `removed` and `mock_provider` | 1.7.0 | Mocking is available only through `terraform test`. |
| Ephemeral variables, child outputs, and resources | 1.10.0 | Root outputs cannot be ephemeral. |
| S3 `use_lockfile` | 1.10.0 | Experimental in 1.10; require 1.11.0 or later for new production backends. |
| Provider write-only arguments | 1.11.0 | The selected provider resource must also support the argument. |

If the current constraint is below a feature's floor, use a compatible existing
mechanism or propose an explicit Terraform upgrade. Do not silently raise
`required_version` as a side effect of an unrelated change.

For root modules:

- Constrain Terraform and provider versions deliberately.
- Use pessimistic constraints where the team wants controlled upgrades.
- Commit one `.terraform.lock.hcl` per independently initialized root, including
  each stack and the bootstrap root; reusable child modules do not control a
  caller's dependency selection.
- After dependency changes, run `terraform providers lock` in every changed
  root with each actual developer/CI `-platform` (for example,
  `-platform=darwin_arm64 -platform=linux_amd64`). This is especially important
  with mirrors; signed origin providers often include portable `zh:` hashes,
  but explicit platform locking makes support deterministic.
- Use `terraform init -upgrade` only for a deliberate dependency upgrade. Then
  rerun `terraform providers lock` for all supported platforms and review the
  version and checksum diff.
- Upgrade core and providers separately in a non-production environment first.

For reusable child modules, declare minimum compatible provider versions and let
the root select the final version. Pin registry modules to an exact published
version. For Git sources, use a full commit SHA when immutability matters; a Git
tag can be moved and `version` is valid only for registry module sources.

## Provider and Account Guardrails

Require the expected account ID and reject credentials for every other account:

```hcl
variable "aws_account_id" {
  description = "Twelve-digit AWS account that this environment may manage"
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must contain exactly 12 digits."
  }
}

provider "aws" {
  region              = var.aws_region
  allowed_account_ids = [var.aws_account_id]

  assume_role {
    role_arn = var.deployment_role_arn
  }

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment_name
      ManagedBy   = "terraform"
    }
  }
}
```

Prefer short-lived credentials and environment-specific roles, such as CI OIDC
role assumption. Do not put access keys or secrets in provider configuration.
Repeat `allowed_account_ids` and `default_tags` on aliased providers; provider
configurations do not inherit them from one another.

Use aliases for distinct accounts or when a module manages a coherent group in
another region. Pass aliases explicitly and declare `configuration_aliases` in
child modules. With AWS provider v6, use a resource's top-level `region`
argument for an isolated cross-region resource only after confirming that the
resource supports it; changing the region generally forces replacement.

Provider default tags apply to supported resources, with documented exceptions
such as Auto Scaling Groups. Set organization-wide tags once and add only
resource-specific tags locally.

## Remote State Backend

For a root constrained to Terraform 1.11.0 or later, use partial S3 backend
configuration with GA S3-native locking:

```hcl
bucket       = "<project>-tfstate-<account-id>-<region>"
key          = "<env>/<stack>/terraform.tfstate"
region       = "<region>"
encrypt      = true
use_lockfile = true
# kms_key_id = "<customer-managed-key-arn>" # when required
```

Terraform 1.10 recognizes `use_lockfile` but marks it experimental. Older
versions reject it. If a repository still supports Terraform below 1.11,
preserve its working lock mechanism and propose a reviewed core/backend
migration instead of emitting this argument. DynamoDB locking is deprecated as
of Terraform 1.11; S3 and DynamoDB locking may coexist only during an intentional
compatibility migration for older clients.

Do not put credentials or other secrets in backend configuration; Terraform can
copy backend values into `.terraform/` and plan files. Use environment
credentials or backend role assumption.

Bootstrap the state bucket with a separate configuration because a stack cannot
create its own backend before initialization. The default convention here is a
dedicated `bootstrap/state/` root with a **local backend that remains local**; do
not automatically migrate its state into the bucket it creates. Serialize
bootstrap operations, gitignore `terraform.tfstate*`, and store the exact local
state and backup through an approved durable, encrypted, access-controlled
mechanism before another machine runs the root. Preserve any existing remote
bootstrap backend instead. Any later backend migration requires a separately
reviewed `-migrate-state` operation.

Protect the backend with:

- S3 versioning, server-side encryption, public-access blocking, and disabled
  ACLs/object ownership enforcement.
- A bucket policy that denies non-TLS transport.
- Least-privilege object-prefix access for each environment/stack.
- `s3:ListBucket` scoped to the state prefix.
- `s3:GetObject` and `s3:PutObject` on the state object.
- `s3:GetObject`, `s3:PutObject`, and `s3:DeleteObject` on the `.tflock` object.
- KMS permissions scoped to the backend key when using SSE-KMS.

`prevent_destroy = true` is useful on a bootstrap-managed state bucket, but it
only works while the resource block remains in configuration. Reinforce it with
code review, IAM/SCP controls, versioning, and recovery procedures.

## Cross-Stack Dependencies

Prefer provider-native discovery or publish intentional values through a
managed service such as SSM Parameter Store or Route 53. Use
`terraform_remote_state` only when the consumer is allowed to read the entire
source state snapshot, because output access implies access to that snapshot.
Keep cross-stack output contracts small, stable, and acyclic.

## Inputs, Outputs, and Secrets

Define `project_name`, `environment_name`, `aws_account_id`, `aws_region`, and
`deployment_role_arn` in each root. Validate the supported environment names,
approved regions, IDs, CIDRs, ports, sizes, and mutually dependent settings.
Commit non-secret environment tfvars; never store credentials or secret values
in them.

Marking a value `sensitive` redacts CLI output but does not keep it out of state
or saved plans. Passing a secret with `TF_VAR_*`, a data source, or an
uncommitted tfvars file can still persist it.

Before designing secret resources, runtime integration, or IAM, ask this
question unless the answer is already explicit:

> Which store should hold runtime secrets in each environment: SSM Parameter
> Store (`SecureString`) or AWS Secrets Manager? You can choose one service for
> every environment or a mapping such as SSM for dev/staging and Secrets
> Manager for production.

Recommend SSM for lightweight encrypted configuration that does not need managed
rotation, cross-account access, cross-Region replication, or a secret-specific
lifecycle. Recommend Secrets Manager when those capabilities justify its cost
and lifecycle machinery. Production is a reason to evaluate that choice, not an
automatic mandate.

Record the resolved choice explicitly in environment configuration. For one
secret class, prefer a validated discriminator instead of a boolean:

```hcl
variable "runtime_secret_store" {
  description = "Runtime secret store used by this environment"
  type        = string

  validation {
    condition     = contains(["ssm", "secrets-manager"], var.runtime_secret_store)
    error_message = "runtime_secret_store must be ssm or secrets-manager."
  }
}
```

Set `runtime_secret_store = "ssm"` or `"secrets-manager"` in each environment's
committed, non-secret tfvars. When independently owned secret groups need
different stores, use a validated map keyed by stable secret-group names rather
than adding multiple `use_*` booleans. Keep a stable workload contract across
stores: pass a non-secret store identifier plus explicit names or ARNs, and
grant only the read actions required by the selected store.

Supporting both stores is a bounded environment variant only when both paths
remain intentionally tested and share one ownership lifecycle. Otherwise use
separate focused modules with the same outputs. Never migrate an existing
secret implicitly because an environment mapping changed; populate and verify
the destination, cut consumers over, and retire the source through a reviewed
migration.

Terraform may create or rotate a value without persisting it in plan or state
only when Terraform is at least 1.11.0, the provider resource supports the exact
write-only argument, and the entire input path is safe. Prefer an
`ephemeral = true`, `sensitive = true` variable supplied by an approved secrets
system; a write-only destination does not make a committed tfvars file, shell
argument, log, or ordinary downstream consumer safe. Increment the companion
non-secret `_wo_version` value for every intended write. Use trusted providers;
these controls do not protect process memory or malicious provider logging.

Otherwise, keep the secret value outside Terraform: pass only a parameter or
secret ARN/name/prefix and let an approved workflow write it and the workload
retrieve it at runtime. Choose one rotation owner; Terraform cannot compare a
discarded write-only value with the remote value or detect its drift. Follow the
selected store's reference for exact provider floors, least-privilege IAM,
runtime retrieval, rotation, and recovery.

Export only stable coupling surfaces. Use locals for values consumed only
within the same root. Keep wrapper-consumed outputs compatible with the
deploy-scripts contract.

## Resource and AWS Patterns

- Prefer `for_each` with stable, plan-time keys for collections whose members
  can be added or removed independently. Use `count` when numeric identity is
  genuinely meaningful or for a simple zero-or-one toggle.
- Use standalone `aws_vpc_security_group_ingress_rule` and
  `aws_vpc_security_group_egress_rule` resources for independently managed
  rules. Give managed-ENI security groups suitable delete timeouts.
- Set `replace_security_groups_on_destroy = true` and
  `replacement_security_group_ids` for VPC Lambda functions when required by
  the destroy design.
- Drain ECS services before destroying their task security groups.
- Set ECR `image_tag_mutability = "IMMUTABLE"` and `force_delete = false`.
  Deploy Git SHA tags or, for stronger provenance, immutable image digests.
- Avoid `latest`, branch image tags, routine `-target`, broad
  `ignore_changes`, and provisioners when a provider-native mechanism exists.

AWS naming rules differ by service. Apply the project/environment convention
where supported, but validate each service's uniqueness, length, and syntax
rules. S3 bucket names are globally unique within a partition and length
limited; ECR repositories and CloudFront distributions do not share that exact
namespace rule.

## Refactoring and Lifecycle

Use declarative refactoring blocks:

- `moved` for address changes that must preserve an existing object.
- `import` for known existing resources being adopted into configuration.
- `removed` with `destroy = false` for deliberate ownership handoff.
- `check` for non-blocking assertions evaluated during plan or apply.
- Resource preconditions/postconditions for invariants that must block.

For an ownership handoff that must leave the remote objects intact, put
`destroy = false` inside the `removed` block's nested `lifecycle` block:

```hcl
removed {
  from = module.legacy_worker

  lifecycle {
    destroy = false
  }
}
```

Review the resolved `from` address and plan carefully. Applying this block still
mutates state even though it does not destroy the remote objects.

Keep `moved` blocks long enough for all consumers to cross the migration.
Remove one-time `import` and `removed` blocks only after the rollout is complete.
Use imperative import/state commands only for explicitly authorized exceptional
operations, including runtime-conditional bootstrap recovery.

Use lifecycle rules narrowly. `prevent_destroy` is not protection after a
resource block is deleted. `create_before_destroy` can require extra quota or
unique naming. `ignore_changes` must name only attributes that another declared
controller owns.

## Validation and Tests

Use the bundled non-mutating checker:

```sh
<skill-dir>/scripts/check.sh \
  --repo-root "$REPO_ROOT" \
  --terraform-dir "$TF_ROOT" \
  --platform darwin_arm64 \
  --platform linux_amd64
```

It formats the source in check mode, validates every stack, bootstrap root, and
standalone module in a temporary copy with backend access disabled, audits the
requested lockfile platforms, runs a configured AWS TFLint ruleset, and makes
Trivy findings fail the gate. Missing TFLint/Trivy configuration or tools fails
unless an explicit skip flag is used. Without an enabled, exactly pinned AWS
plugin, do not describe TFLint as AWS linting. Use Checkov alongside or instead
of Trivy only when the repository standardizes on it; do not recommend tfsec for
new setups.

Run `terraform -chdir=<configuration> test` for each module or stack that owns
tests; Terraform discovers its `tests/*.tftest.hcl`. Mocking requires Terraform
1.7.0 and uses real schemas but synthetic computed values; use `.tfmock.hcl`
files or explicit defaults for ARN/ID-shape assertions. The checker omits tests
because unmocked tests can create billable infrastructure; run those only in a
dedicated disposable account with cleanup monitoring.

For a real environment plan, initialize its backend with the isolated
`TF_DATA_DIR`, save the plan, review replacements/deletions and JSON policy
results, and apply that exact saved plan only after authorization. Treat plan
files as sensitive and never commit them.

## Adding a Stack

1. Add or reuse focused modules under `Terraform/modules/{component}/`.
2. Add one root under `Terraform/stacks/{stack}/` with the standard root files.
3. Add `{stack}.tfvars` under every supported environment; do not require
   environments that the project does not deploy.
4. Add one partial backend file per supported environment.
5. Add stable outputs required by consumers and wrapper scripts.
6. Resolve and document the runtime secret store for each environment when the
   stack consumes secrets; keep ordinary values out of plan/state and follow the
   selected store reference for any write-only path.
7. Update the companion deploy scripts and environment-specific stack order if
   the topology differs.
8. Run the validation workflow and plan in the cheapest representative
   environment before promoting intentionally.
