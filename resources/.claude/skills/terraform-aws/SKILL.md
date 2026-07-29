---
name: terraform-aws
description: >-
  Create, modify, review, and refactor Terraform configurations for AWS
  deployments that use reusable modules, a platform/application stack split with
  one root module per deployable stack, environment-specific values, and remote
  S3 state. Use for AWS Terraform modules, stack roots, backend configuration,
  provider upgrades, state-safe refactors, per-service release stacks, runtime
  secret-storage choices between SSM Parameter Store and AWS Secrets Manager,
  Python Lambda source and artifact boundaries, whether application source shares
  the Terraform repository or lives in its own, testing, and infrastructure reviews
  in repositories that adopt these conventions. Do not apply these conventions to
  non-AWS Terraform or replace an existing architecture unless asked to migrate.
---

# AWS Terraform Deployment Conventions

Use these conventions for repositories that keep Terraform under `Terraform/`.
Examples use that spelling, but first resolve the repository's actual
case-sensitive directory name and bind it to `TF_ROOT`; never create a second case
variant. Treat a **stack** as one independently initialized root module with one
state boundary — not the separate HashiCorp Terraform Stacks product.

Preserve established repository conventions unless the user explicitly requests
a migration. When this skill and repository-local instructions disagree, follow
the repository and call out the difference.

The sibling `deploy-scripts` skill defines wrappers that select an environment,
isolate local metadata, plan, apply, and destroy stacks. Read both skills when
changing Terraform/script interfaces. If the companion is unavailable, use
[`references/deploy-scripts-pattern.md`](references/deploy-scripts-pattern.md)
as the Terraform-side contract and do not invent wrapper behavior.

Split each environment into a **platform tier** changing weekly to monthly (VPC,
clusters, databases, load balancer, ECR) and an **application tier** with one
stack per independently releasable service (task/service, function/alias, target
group/listener rule). Apply only that small app stack for an application release.

Read the focused references when applicable:

- Stack tiers and contracts: [`references/platform-application-split.md`](references/platform-application-split.md)
- Per-workload deploys: [`references/workload-deploy-patterns.md`](references/workload-deploy-patterns.md)
- Python Lambda source and uv packaging: [`references/python-lambda.md`](references/python-lambda.md)
- EKS and GitOps: [`references/eks-gitops.md`](references/eks-gitops.md)
- Splitting a combined stack: [`references/splitting-an-existing-stack.md`](references/splitting-an-existing-stack.md)
- Environment variants: [`references/environment-variants.md`](references/environment-variants.md)
- Validation and tests: [`references/validation-and-tests.md`](references/validation-and-tests.md)
- Container images: [`references/docker-image-tagging.md`](references/docker-image-tagging.md)
- SSM secrets: [`references/ssm-secrets-pattern.md`](references/ssm-secrets-pattern.md)
- Secrets Manager: [`references/secrets-manager-pattern.md`](references/secrets-manager-pattern.md)
- Wrapper interface: [`references/deploy-scripts-pattern.md`](references/deploy-scripts-pattern.md)

## Required Workflow

1. Inspect `CLAUDE.md`, `AGENTS.md`, and other repository-local instructions when
   present. Resolve `TF_ROOT`, then inspect the Terraform tree, every affected
   root's `required_version`, lockfiles, provider constraints, state boundaries,
   and nearby modules before designing changes. Treat a missing `required_version`
   as unknown compatibility, not permission to use the current CLI's features.
   Also resolve the **repository topology**: application source may live in this
   repository (monorepo) or in a separate application repository whose pipeline
   publishes artifact versions into this one. It changes nothing about the
   Terraform tree, and two things about its edges — where workload source belongs,
   and where an artifact version comes from. Detection rules and the handoff:
   the `deploy-scripts` skill's `references/split-repo-releases.md`.
2. Resolve the target environment, AWS account, region, stack, and expected
   state path. Do not infer production as the default.
3. Classify the change as platform-tier or application-tier and confirm the
   target stack's tier before designing. A change that spans both tiers is two
   changes with a published contract between them, not one stack.
4. When the workload needs runtime secrets and the repository or user has not
   already selected a store, ask whether to use SSM Parameter Store or AWS
   Secrets Manager **for each target environment**. Offer an explicit mixed
   mapping such as `dev=ssm`, `staging=ssm`, and
   `prod=secrets-manager`; do not assume all environments must use the same
   service.
5. Decide whether the change is an environment value difference, a reusable
   module change, a state-safe refactor, or a genuinely different topology.
6. Preserve resource addresses where possible. Add `moved`, `import`, or
   `removed` blocks when state ownership or addresses change.
7. Run formatting, backendless initialization, validation for every changed root
   and every root consuming a changed module, appropriate tests, security/static
   checks, and a real plan for the target environment.
8. Do not run `apply`, `destroy`, imperative `import`, `state` mutations,
   `force-unlock`, or `-target` unless the user explicitly authorizes that
   operational action.

## Repository Layout

Keep one root module per deployable stack, exactly one directory level under
`stacks/`, and environment differences in data files:

```text
Terraform/
├── backend-config/{env}/{stack}.backend.hcl  # one per stack per environment
├── environments/{env}/{stack}.tfvars         # one per stack per environment
│   └── {stack}.artifacts.tfvars              # machine-written; split repo only
├── stacks/
│   ├── platform-network/  # VPC, subnets, NAT, shared SGs, ALB + default listener
│   ├── platform-data/     # RDS/Aurora, ElastiCache, shared KMS
│   ├── platform-ecr/      # one repository per service
│   ├── app-api/           # task definition, service, target group, listener rule
│   │   ├── {backend,main,outputs,providers,variables,versions}.tf  # every root
│   │   ├── tests/composition.tftest.hcl
│   │   └── .terraform.lock.hcl
│   ├── app-worker/        # task definition, service, no ingress
│   └── app-scheduler/     # Step Functions + Lambda
├── modules/{component}/   # ecs-service, lambda-function, alb-target-group
│   ├── {main,outputs,variables,versions}.tf
│   ├── tests/behavior.tftest.hcl
│   └── README.md
└── bootstrap/state/       # local backend; see Remote State Backend
    ├── {main,outputs,providers,variables,versions}.tf
    └── .terraform.lock.hcl
```

Keep Python Lambda source at `lambdas/<function>/`, at the root of whichever
repository owns the source and beside rather than inside `Terraform/`. Its
reference defines layout, uv packaging, and the AWS-adapter/application-logic
boundary. Under a split layout that root is the application repository's, and this
repository holds no workload source at all — do not create an empty `lambdas/`
tree here to match the diagram.

`{stack}.artifacts.tfvars` appears only under a split layout: it is the committed,
machine-written file an application repository's release publishes, holding that
stack's artifact coordinates and nothing else. Keep it strictly separate from the
hand-edited `{stack}.tfvars`, which no automation may rewrite.

Six stacks across three environments is 18 backend files and 18 tfvars files.
Thin roots over shared modules keep that affordable: `modules/ecs-service/` is
written once, and every ECS app root is a provider block, a backend block, a few
`data "aws_ssm_parameter"` lookups, one module call, and its outputs. The tier
rule, the floor below which one combined stack is correct, and shared-namespace
allocation:
[`references/platform-application-split.md`](references/platform-application-split.md).

One root per stack across all environments gives them the same tested resource
graph without copying root configuration or provider lockfiles. Express normal
environment differences — database instance class, Multi-AZ, storage, backup
retention, ECS capacity, log retention — as typed input values.

The `tests/` directories are optional until useful behavior exists to assert. Put
reusable-module contract tests beside that module. Put stack tests beside the
stack only when they validate root composition, outputs, policies, or
environment-independent invariants; do not duplicate module tests in every stack.

If production truly uses a different database product or resource graph, use a
separate root implementation with the same output contract instead of fragile
conditionals or a copy per environment — for example
`stacks/platform-data-aurora/` and `stacks/platform-data-rds/`, selected by the
deployment wrapper through an explicit, closed environment mapping. The
environment-variants reference has the decision and ownership-cutover rules.

Use stack boundaries for rate of change, independently owned or promoted
lifecycles, security boundaries, and blast-radius reduction. Do not create a
separate state merely because code can be factored into a module. ECR is a useful
platform-tier stack because repositories and images outlive the services that
push to them.

### Shared-Root Safety

Because all environments share one stack directory, isolate Terraform's local
backend metadata per environment, logical stack, and selected root:

```sh
export TF_DATA_DIR="$REPO_ROOT/.terraform-data/$ENV/$LOGICAL_STACK/$ROOT_STACK"
terraform -chdir="$TF_ROOT/stacks/$ROOT_STACK" init -reconfigure \
  -backend-config="$TF_ROOT/backend-config/$ENV/$LOGICAL_STACK.backend.hcl"
```

Gitignore `.terraform-data/`. `-reconfigure` selects the declared backend without
offering to migrate another environment's state. Use `-migrate-state` only during
an intentional, reviewed backend migration.

## Root Modules and Reusable Modules

Keep root modules thin: configure providers and backends, discover stable external
dependencies, compose child modules, and expose intentional outputs. Keep reusable
modules focused on a cohesive capability rather than mirroring stack names.

For reusable modules:

- Declare every provider source and the minimum compatible provider version, and
  do not define `provider` blocks or credentials inside child modules.
- Accept dependency IDs and ARNs explicitly instead of performing hidden,
  environment-wide discovery inside the module.
- Give every variable a type and description; validate non-trivial invariants.
- Give every output a description and mark secret-bearing outputs sensitive.
- Keep module trees relatively flat and prefer composition in the root.
- Generate interface documentation with `terraform-docs` for a reusable module.

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

If the constraint is below a feature's floor, use a compatible existing mechanism or
propose an explicit upgrade; never raise `required_version` as a side effect of an
unrelated change.

For root modules:

- Constrain Terraform and provider versions deliberately; use pessimistic
  constraints where the team wants controlled upgrades.
- Commit one `.terraform.lock.hcl` per independently initialized root, including
  every stack and the bootstrap root; reusable child modules do not control a
  caller's dependency selection.
- After dependency changes, run `terraform providers lock` in every changed root
  with each actual developer/CI `-platform` (for example,
  `-platform=darwin_arm64 -platform=linux_amd64`). This matters most with mirrors;
  signed origin providers often include portable `zh:` hashes, but explicit
  platform locking makes support deterministic.
- Use `terraform init -upgrade` only for a deliberate dependency upgrade, then
  re-lock all supported platforms and review the version and checksum diff.
- Upgrade core and providers separately in a non-production environment first.

For reusable child modules, declare minimum compatible provider versions and let
the root select the final version. Pin registry modules to an exact published
version; for Git sources use a full commit SHA when immutability matters, since a
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

Prefer short-lived credentials and environment-specific roles, such as CI OIDC role
assumption — one role per tier, and for the application tier one role per service
per environment. Do not put access keys or secrets in provider configuration. Repeat
`allowed_account_ids` and `default_tags` on aliased providers; configurations do not
inherit them from one another.

Use aliases for distinct accounts or when a module manages a coherent group in
another region. Pass aliases explicitly and declare `configuration_aliases` in
child modules. With AWS provider v6, use a resource's top-level `region` argument
for an isolated cross-region resource only after confirming that the resource
supports it; changing the region generally forces replacement.

Provider default tags apply to supported resources, with documented exceptions such
as Auto Scaling Groups. Set organization-wide tags once and add only
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

Terraform 1.10 recognizes `use_lockfile` but marks it experimental, and older
versions reject it. If a repository still supports Terraform below 1.11, preserve
its working lock mechanism and propose a reviewed core/backend migration instead of
emitting this argument. DynamoDB locking is deprecated as of Terraform 1.11; the
two may coexist only during an intentional migration for older clients.

Do not put credentials or secrets in backend configuration; Terraform copies backend
values into `.terraform/` and plan files. Use environment credentials or backend
role assumption.

Bootstrap the state bucket separately — a stack cannot create its own backend before
initialization. The default convention is a dedicated `bootstrap/state/` root with a
**local backend that remains local**; do not migrate its state into the bucket it
creates. Serialize bootstrap operations, gitignore `terraform.tfstate*`, and durably
back up the exact local state through an approved encrypted, access-controlled
mechanism before another machine runs the root. Preserve any existing remote
bootstrap backend instead; a later migration is a separately reviewed
`-migrate-state` operation.

Protect the backend with S3 versioning, server-side encryption, public-access
blocking, enforced object ownership with ACLs disabled, and a bucket policy that
denies non-TLS transport. Grant least-privilege object-prefix access per
environment and stack: `s3:ListBucket` scoped to the state prefix,
`s3:GetObject`/`s3:PutObject` on the state object, those plus `s3:DeleteObject` on
its `.tflock` object, and KMS permissions scoped to the backend key under SSE-KMS.
One prefix per environment and stack is what lets each tier — and each service's
release role — hold write access to its own state and nothing else.

`prevent_destroy = true` is useful on a bootstrap-managed state bucket, but it
only works while the resource block remains in configuration. Reinforce it with
code review, IAM/SCP controls, versioning, and recovery procedures.

## Cross-Stack Dependencies

The platform tier's published parameter set is its public API. Publish non-secret
discovery values under `/{project}/{env}/platform/{component}/{key}` and read them
from app stacks with `data "aws_ssm_parameter"`. Route 53 records and
provider-native discovery of a uniquely identifiable resource are equally valid
publication mechanisms. Use `terraform_remote_state` only when the consumer may
read the entire source state snapshot, because output access implies access to that
snapshot; an app role that may read all of platform state defeats the split.

Published names are a breaking-change surface: renaming or removing one is a
platform release with a consumer cutover, not a refactor. Data sources resolve at
plan time, so an app plan fails when a platform parameter is absent — correct
behavior, and the failure must name the unapplied platform stack and environment
rather than proceed. Keep the published set small, stable, and acyclic; a platform
stack never reads an app stack's values. Details and the typical published set:
[`references/platform-application-split.md`](references/platform-application-split.md).

## Inputs, Outputs, and Secrets

Define `project_name`, `environment_name`, `aws_account_id`, `aws_region`, and
`deployment_role_arn` in each root. Validate the supported environment names,
approved regions, IDs, CIDRs, ports, sizes, and mutually dependent settings.
Commit non-secret environment tfvars; never store credentials or secret values
in them.

A value allocated from a namespace shared between app stacks — an ALB listener rule
priority, a shared API path prefix — is a **required, validated input with no
default**, never computed from a data source: two stacks planning at once would
derive the same value and the second apply would fail. Artifact versions (image
digest or tag, AMI ID, Lambda S3 object version) are likewise required with no
default, so a release that skipped its build fails at plan instead of redeploying
the previous artifact. That rule tightens rather than relaxes when the build runs
in another repository: the value arrives from outside this repository's history, so
the plan-time failure is the only thing standing between a broken upstream pipeline
and a deploy that reports success having shipped nothing new.

Marking a value `sensitive` redacts CLI output but does not keep it out of state or
saved plans; `TF_VAR_*`, data sources, and uncommitted tfvars files can all still
persist it.

Before designing secret resources, runtime integration, or IAM, ask this question
unless the answer is already explicit:

> Which store should hold runtime secrets in each environment: SSM Parameter Store
> (`SecureString`) or AWS Secrets Manager? One service everywhere, or a mapping
> such as SSM for dev/staging and Secrets Manager for production.

Recommend SSM for lightweight encrypted configuration that does not need managed
rotation, cross-account access, cross-Region replication, or a secret-specific
lifecycle; recommend Secrets Manager when those capabilities justify its cost and
lifecycle machinery. Production is a reason to evaluate that choice, not an
automatic mandate. Record the resolved choice in each environment's committed,
non-secret tfvars as a validated discriminator — `runtime_secret_store`,
restricted to `ssm` or `secrets-manager` — not a boolean, or as a validated map
keyed by stable secret-group names when independently owned groups need different
stores. Keep a stable workload contract across stores: pass a non-secret store
identifier plus explicit names or ARNs, and grant only that store's read actions.

Support both stores in one root only while both paths stay intentionally tested
under one ownership lifecycle; otherwise use separate focused modules with the
same outputs. Never migrate an existing secret implicitly because an environment
mapping changed — populate and verify the destination, cut consumers over, then
retire the source through a reviewed migration.

Prefer keeping the secret value outside Terraform: pass only a parameter or secret
ARN/name/prefix, and let an approved workflow write it and the workload retrieve
it at runtime. Terraform may create or rotate a value without persisting it in
plan or state only when Terraform is at least 1.11.0, the provider resource
supports the exact write-only argument, and the whole input path is safe — an
`ephemeral = true`, `sensitive = true` variable from an approved secrets system,
with the companion non-secret `_wo_version` incremented for every intended write.
A write-only destination does not make a committed tfvars file, shell argument,
log, or ordinary downstream consumer safe, and none of this protects process
memory or malicious provider logging. Choose one rotation owner; Terraform cannot
compare a discarded write-only value with the remote value or detect its drift.
Each store's reference carries the provider floors, least-privilege IAM, runtime
retrieval, rotation, and recovery.

Export only stable coupling surfaces; use locals for values consumed within one
root, and keep wrapper-consumed outputs compatible with the deploy-scripts contract.

## Resource and AWS Patterns

- Prefer `for_each` with stable, plan-time keys for collections whose members
  can be added or removed independently. Use `count` when numeric identity is
  genuinely meaningful or for a simple zero-or-one toggle.
- Use standalone `aws_vpc_security_group_ingress_rule` and
  `aws_vpc_security_group_egress_rule` resources for independently managed rules.
  Give managed-ENI security groups suitable delete timeouts.
- Set `replace_security_groups_on_destroy = true` and
  `replacement_security_group_ids` for VPC Lambda functions when required by the
  destroy design. Drain ECS services before destroying their task security groups.
- Set ECR `image_tag_mutability = "IMMUTABLE"` and `force_delete = false`.
  Deploy Git SHA tags or, for stronger provenance, immutable image digests.
- Avoid `latest`, branch image tags, routine `-target`, broad `ignore_changes`,
  and provisioners when a provider-native mechanism exists.
- An app stack owns its task definition, so do not add
  `ignore_changes = [task_definition]` to a service this skill generates. Keep
  `ignore_changes = [desired_count]` only where autoscaling owns capacity.
- EC2 releases go through a new AMI, a new launch template version, and an ASG
  instance refresh — never an in-place code copy onto running instances;
  `user_data` takes effect only on replacement. Per-workload HCL:
  [`references/workload-deploy-patterns.md`](references/workload-deploy-patterns.md).

`ignore_changes = [task_definition]` on an existing `aws_ecs_service` means a
deployment pipeline — not Terraform — owns that service's task definitions. Do
not remove it, and do not add a Terraform-managed image tag alongside it; the two
designs are exclusive and blending them leaves a task definition Terraform cannot
update. Ask before changing that ownership.

AWS naming rules differ by service. Apply the project/environment convention where
supported, but validate each service's uniqueness, length, and syntax rules: S3
bucket names are globally unique within a partition and length limited, while ECR
repositories and CloudFront distributions are not.

## Refactoring and Lifecycle

Use declarative refactoring blocks:

- `moved` for address changes that must preserve an existing object, `import` for
  existing resources being adopted into configuration, and `removed` with
  `destroy = false` for deliberate ownership handoff.
- `check` for non-blocking assertions evaluated during plan or apply; resource
  preconditions/postconditions for invariants that must block.

For an ownership handoff that must leave the remote objects intact, put
`destroy = false` inside the `removed` block's nested `lifecycle` block, and
review the resolved `from` address and the plan first: applying it still mutates
state. Moving a resource to a **different root** is `import` in the destination
plus `removed` in the source, because `moved` works only within one state. Full
procedure, including the carve-out of an app stack from a combined stack:
[`references/splitting-an-existing-stack.md`](references/splitting-an-existing-stack.md).

Keep `moved` blocks long enough for all consumers to cross the migration, and
remove one-time `import` and `removed` blocks only after the rollout completes. Use
imperative import/state commands only for explicitly authorized exceptional
operations, including runtime-conditional bootstrap recovery.

Use lifecycle rules narrowly. `prevent_destroy` is not protection after a resource
block is deleted. `create_before_destroy` can require extra quota or unique naming.
`ignore_changes` must name only attributes that another declared controller owns.

## Validation and Tests

Run the bundled non-mutating checker for every change:

```sh
<skill-dir>/scripts/check.sh --repo-root "$REPO_ROOT" \
  --terraform-dir "$TF_ROOT" --platform darwin_arm64 --platform linux_amd64
```

It formats in check mode, validates every stack, bootstrap root, and standalone
module with backend access disabled, audits the requested lockfile platforms, and
fails on TFLint or Trivy findings — and on missing tools or configuration, unless an
explicit skip flag is passed. It omits `terraform test`: unmocked tests can create
billable infrastructure. Run those per module or stack that owns tests, in a
disposable account.

For a real environment plan, initialize its backend with the isolated
`TF_DATA_DIR`, save the plan, review every replacement and deletion plus the JSON
policy results, and apply that exact saved plan only after authorization. Treat
plan files as sensitive and never commit them.

Tool policy, test authoring and mocking floors, and the plan-review procedure:
[`references/validation-and-tests.md`](references/validation-and-tests.md).

## Adding a Stack

Both tiers: add or reuse focused modules under `Terraform/modules/{component}/`; add
one root under `Terraform/stacks/{stack}/` with the standard root files, one
`{stack}.tfvars` and one partial backend file per supported environment, stable
outputs for consumers and wrapper scripts, and a deploy/destroy script pair plus a
stack-list entry. Then validate and plan in the cheapest representative environment.

### Adding a Platform Stack

1. Confirm the resources change weekly-to-monthly and are shared by more than one
   service; a per-service resource belongs in that service's app stack.
2. Place it in the stack list in dependency order, ahead of every app stack.
3. Publish what consumers need as SSM parameters under
   `/{project}/{env}/platform/{component}/{key}` and treat those names as a
   contract. Own the shared namespaces — ALB listener and its default action,
   Route 53 zone, shared API and stage — and their committed allocation table.
4. Resolve and document the runtime secret store per environment when the stack
   owns secrets; follow that store's reference for any write-only path.
5. Add the environment-to-root mapping if this stack has a topology variant.

### Adding an Application Stack

1. **Merge or split?** A service that always ships with an existing service joins
   that app stack. Otherwise, one stack per releasable service.
2. Reuse the shared workload module — or write it once under `modules/` for the
   first service of its kind — keep the root thin, and read the platform contract
   with `data "aws_ssm_parameter"`, never `terraform_remote_state`.
3. Allocate any shared-namespace value in the platform tier's committed table,
   then take it as a required input with no default. Define the artifact input —
   image digest, AMI ID, Lambda S3 object version — validated, no default. Under a
   split layout that value arrives in a committed
   `environments/{env}/{stack}.artifacts.tfvars` written by the application
   repository's release; the variable declarations are identical either way.
4. Add the release workflow caller and a deployment role per environment, scoped
   to this stack's resources, its state prefix, and its ECR repository or Lambda
   artifact prefix. Under a split layout, split that role: the application
   repository gets publish-only rights to the artifact prefix, and this
   repository's deploy role only reads the artifact.
5. Append to the unordered app section of the stack list. App stacks are siblings;
   what one service needs from another is a published contract, not an ordering
   dependency.
