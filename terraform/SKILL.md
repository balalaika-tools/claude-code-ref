---
name: terraform
description: Terraform + AWS conventions for multi-environment infrastructure using stacks, reusable modules, and remote S3 state. Use whenever writing, modifying, or reviewing Terraform configuration: modules, environments, backend configs, etc.

user-invocable: false
---

This skill defines the conventions for a project's `Terraform/` tree. Follow it when generating new configuration, extending existing stacks, or reviewing diffs — the goal is that any stack written by an agent looks and behaves like the ones already in the target repo.

The companion **`deploy-scripts`** skill covers the shell scripts (`deploy-*.sh`, `destroy-*.sh`, `build-*.sh`) that wrap these stacks for local and CI use. The two are meant to be read together — see [`references/deploy-scripts-pattern.md`](references/deploy-scripts-pattern.md) for the interface contract between them (what each side assumes about the other), and the `deploy-scripts` skill itself for the scripts.

# Terraform Structure

```
Terraform/
├── backend-config/{env}/        # Partial backend configs per stack
├── environments/{env}/{stack}/  # Stack entry points (variables, outputs, remote state refs)
└── modules/{stack}/             # Reusable resource definitions
```

A **stack** is one logical grouping of resources (networking, compute, storage, …). Modules hold the resource definitions; environment folders wire them together with environment-specific values. Keeping this split consistent is what lets a single `terraform apply` target one concern in one environment without dragging in unrelated state.

**Do not use `terraform workspace` for environment separation.** Workspaces share a single backend and a single `.tf` tree, which makes cross-environment IAM isolation and blast-radius control much harder — an accidental `apply` in the wrong workspace hits prod. Directory-per-environment under `environments/{env}/{stack}/` is the intentional alternative. Workspaces are fine for ephemeral per-developer sandboxes within the *same* environment, but `dev`/`staging`/`prod` must stay in their own directories with their own backend configs.

## Conventions

### Versioning

For **root modules** (environment stack entry points), constrain Terraform and provider versions deliberately and commit `.terraform.lock.hcl` so CI and teammates use the same provider builds. Use a pessimistic constraint (`~>`) for root providers unless the existing stack has a documented reason to be looser. The exact behavior depends on specificity: `~> 1.15.0` allows only patch upgrades (1.15.x), while `~> 6.0` allows all minor upgrades within major version 6. Both prevent accidental major upgrades.

For new stacks, prefer the current stable Terraform minor and current AWS provider major after checking release notes. As of May 2026, Terraform v1.15.x is the current stable release line (latest 1.15.3); v1.14.x is still within HashiCorp's two-year active-support window, so existing 1.14 stacks need not rush to upgrade. The AWS provider is on v6.x (latest 6.47.x) — there is no v7 yet, so `~> 6.0` remains the right root constraint. Older stacks can stay pinned to their current minor until a planned upgrade.

```hcl
terraform {
  required_version = "~> 1.15.0" # allow any 1.15.x
  required_providers {
    aws    = { source = "hashicorp/aws",    version = "~> 6.0" }
    random = { source = "hashicorp/random", version = "~> 3.7" }
  }
}
```

For **reusable child modules**, declare only the minimum provider version needed for the features used (for example `>= 6.0`) and let the root module choose the final provider version. Pin external modules to immutable version tags (e.g. `module "vpc" { source = "terraform-aws-modules/vpc/aws", version = "6.0.1" }`), not branches or floating refs. Maintain an upgrade plan to test and roll out version changes across environments.

### Naming

All AWS resource names follow `{project_name}-{environment_name}-{resource}`. Avoid including the resource type in the name; the resource address already includes it. Use underscores for Terraform identifiers as a team convention — the language permits hyphens too, but underscores are the standard style (e.g. `aws_s3_bucket.tfstate_bucket`).

Two cases where the pattern needs adjustment:

- **Globally unique or length-limited names (S3 buckets, CloudFront distributions, ECR repos).** The base pattern can collide across AWS accounts or blow past the 63-char S3 limit. Append an account ID or short suffix: `"${var.project_name}-${var.environment_name}-artifacts-${data.aws_caller_identity.current.account_id}"`.
- **Special-syntax names (KMS aliases, IAM paths).** These require literal prefixes. Use `alias/{project}-{env}-{resource}` for KMS aliases, `/{project}/{env}/…` for IAM paths, etc. — do not force them into the hyphen-only shape.

### Core Variables

Each environment stack defines at least the following variables:

- `project_name` – short project identifier.
- `environment_name` – environment (e.g. `dev`, `staging`, `prod`). Use a validation block or an enum to restrict allowed values.
- `aws_region` – AWS region. Validate using a regular list of approved regions.
- `tfstate_bucket`, `tfstate_region` – include only when the stack reads cross-stack remote state.

Define a `type` and `description` for every variable; specify a `default` only when appropriate; use `sensitive` on secrets.

### Provider

Create a `providers.tf` file in each environment stack. At minimum:

```hcl
provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment_name
      ManagedBy   = "terraform"
    }
  }
}
```

`default_tags` applies these keys to every taggable AWS resource the provider manages. Do not repeat `Project`, `Environment`, or `ManagedBy` on individual resources — Terraform merges duplicates and surfaces confusing diffs on first apply. On each resource, set only resource-specific identifiers such as `Name` and (for Lambda) `Function`. Omit the `tags` block entirely on resource types that do not support tagging (policy attachments, route associations, security group rules, etc.). See the Tagging section below for the full convention.

**Multi-region or multi-account deployments** use provider aliases. Declare one provider per target and pass the alias explicitly to each resource or module that needs it:

```hcl
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment_name
      ManagedBy   = "terraform"
    }
  }
}

resource "aws_acm_certificate" "cloudfront" {
  provider = aws.us_east_1
  # ...
}
```

Each aliased provider needs its own `default_tags` — tags do not inherit across providers. Modules that use a non-default provider must declare `configuration_aliases` in their `required_providers` block so callers can pass the correct one in.

**AWS provider v6 alternative:** since v6, most resources and data sources accept a top-level `region` argument, letting a single provider block manage resources across regions without a second provider or alias:

```hcl
resource "aws_acm_certificate" "cloudfront" {
  region = "us-east-1" # overrides the provider's configured region for this resource only
  # ...
}
```

Changing `region` on an existing resource forces replacement, so treat it as fixed at creation time, not something toggled later. Provider aliases remain valid and are not deprecated — prefer aliases when most resources in a module share one non-default region (clearer intent, one `default_tags` block covers all of them); prefer the inline `region` argument for one-off cross-region resources (e.g. a single ACM cert for CloudFront) where a whole extra provider block would be overkill.

### Backend

Use a remote S3 backend for state storage. Store partial backend configuration in `backend-config/{env}/{stack}.backend.hcl` and initialize from inside the stack directory (`environments/{env}/{stack}/`, three levels below the `Terraform/` root) with:

```
terraform init -backend-config=../../../backend-config/{env}/{stack}.backend.hcl
```

An example backend config:

```hcl
bucket       = "<project>-tfstate"
key          = "terraform-state-{env}/{stack}/terraform.tfstate"
region       = "<region>"
encrypt      = true
use_lockfile = true  # enable native S3 state locking
```

The S3 backend supports native state locking; set `use_lockfile = true` to create a `.tflock` file alongside the state. DynamoDB-based locking is deprecated. Enable versioning on the state bucket to recover accidental deletions. Note that the backend bucket cannot be created by the configuration that uses it; bootstrap the bucket and its IAM permissions outside of Terraform.

When using S3 lockfiles, the Terraform role needs `s3:GetObject`, `s3:PutObject`, and `s3:DeleteObject` on the `.tflock` object in addition to the usual state object permissions. Missing `DeleteObject` on the lockfile leaves applies stuck behind stale locks.

### Cross-Stack Dependencies

Prefer provider-native data sources or explicit outputs for sharing data between stacks. The `terraform_remote_state` data source reads outputs from another stack's state, but it requires access to the entire state snapshot and can expose sensitive information. When possible, publish shared data to a managed service (e.g. AWS SSM Parameter Store, Route 53 DNS) and consume it via data sources. If you must use `terraform_remote_state`, limit it to stable, intentional outputs and avoid circular dependencies. Example:

```hcl
data "terraform_remote_state" "network" {
  backend = "s3"
  config = {
    bucket = var.tfstate_bucket
    key    = "terraform-state-${var.environment_name}/network/terraform.tfstate"
    region = var.tfstate_region
  }
}
```

### Input Validation

Use `validation` blocks on variables to enforce acceptable values and improve error messages. Examples:

```hcl
variable "environment_name" {
  type        = string
  description = "Deployment environment"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment_name)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "aws_region" {
  type        = string
  description = "AWS region"
  validation {
    condition     = contains(["us-east-1", "us-west-2"], var.aws_region)
    error_message = "Region must be one of the approved deployment regions."
  }
}
```

Also consider validating CIDR blocks, port ranges, counts, and booleans to prevent unsafe defaults. Only expose variables that will differ across environments; overuse of variables makes code harder to understand.

### Outputs

Every output is a coupling surface — once a human or another stack (via `terraform_remote_state`) depends on it, renaming or removing it becomes a coordinated change. Keep the surface small:

- Give every output a `description`.
- Mark outputs that expose secrets, tokens, or connection strings `sensitive = true` so they redact from CLI output.
- Export only *stable* values (ARNs, resource names, endpoint URLs) — not intermediate IDs that change on recreate.
- If a value is only consumed within the same stack, use a `local` instead of an output.

### Resource Patterns

Prefer `for_each` over `count` for collections of resources. With `count`, removing an item in the middle of the list shifts every subsequent index, which Terraform interprets as "destroy and recreate all of them" — catastrophic for stateful resources (RDS, EBS volumes, anything with data). `for_each` keys each instance by a stable string, so adds and removes only affect the one that changed.

```hcl
# Prefer this:
resource "aws_sqs_queue" "events" {
  for_each = toset(["orders", "shipments", "returns"])
  name     = "${var.project_name}-${var.environment_name}-${each.key}"
}

# Over this:
resource "aws_sqs_queue" "events" {
  count = length(var.queue_names)
  name  = "${var.project_name}-${var.environment_name}-${var.queue_names[count.index]}"
}
```

Reserve `count` for a simple 0-or-1 toggle (`count = var.enabled ? 1 : 0`) — never for collections.

`for_each` keys must be known at plan time — `for_each` over a computed attribute (an ARN, an ID from another resource not yet created) fails with "Invalid for_each argument." Key on something stable and known up front (a name from a variable, not a value AWS assigns), since changing a key changes the resource's address and forces replacement, same as an index shift would with `count`.

### AWS Security Groups and Managed ENIs

When writing or reviewing AWS Terraform, treat security groups attached to managed ENI producers as lifecycle-sensitive. AWS cannot delete a security group while any ENI still references it, so destroys can appear to hang with `aws_security_group.<name>: Still destroying...`.

Common ENI producers include VPC Lambda functions, ECS/Fargate tasks, load balancers, VPC interface endpoints, EC2 instances, RDS, EFS mount targets, and ElastiCache. Use these guardrails:

- Add `timeouts { delete = "30m" }` to security groups used by managed ENIs.
- Manage inter-SG references as standalone `aws_vpc_security_group_ingress_rule` / `aws_vpc_security_group_egress_rule` resources (one rule per resource) so Terraform can remove rules before deleting groups. These superseded `aws_security_group_rule` and inline `ingress`/`egress` blocks on `aws_security_group` — the old resource couldn't hold stable IDs, tags, or descriptions, and struggled with multi-CIDR rules. Each new resource takes exactly one CIDR/prefix-list/referenced-SG per rule, so a rule that previously listed several CIDRs becomes a `for_each` over them.
- For VPC Lambda, set `replace_security_groups_on_destroy = true` on `aws_lambda_function`.
- For VPC Lambda, keep `AWSLambdaVPCAccessExecutionRole` attached until the Lambda security group is deleted; Lambda may need that permission to clean up Hyperplane ENIs after function deletion.
- For ECS/Fargate, scale services to zero and wait for tasks to stop before deleting task security groups.
- For shared network stacks, remember that Terraform cannot infer dependencies from other state files; destroy all SG consumers before the stack that owns shared security groups.

When debugging a stuck security group destroy, inspect the blocking ENIs before changing state:

```sh
aws ec2 describe-network-interfaces \
  --region <region> \
  --filters "Name=group-id,Values=<sg-id>" \
  --query 'NetworkInterfaces[].{Id:NetworkInterfaceId,Status:Status,Type:InterfaceType,Attachment:Attachment.Status,Description:Description}' \
  --output table
```

### Tagging

Tagging happens at two levels, and the split matters because it drives cost allocation, IAM tag-based policies, and audit tooling:

- **Provider default tags** — `Project`, `Environment`, `ManagedBy` (set once in `providers.tf` via `default_tags`). Never restate these on a resource; Terraform will merge duplicates but the plan churn makes reviews harder.
- **Resource-specific tags** — identifiers that only make sense per-resource, e.g. `Name` and, for Lambda, `Function`:

```hcl
resource "aws_lambda_function" "handler" {
  # ...
  tags = {
    Name     = "${var.project_name}-${var.environment_name}-handler"
    Function = "handler"
  }
}
```

Omit `tags` entirely on resources that do not support it (policy attachments, route associations, security group rules, etc.) — adding an empty block produces a noisy no-op diff on some provider versions.

### Container Image Tags

Always use git SHA tags for ECR images. Never use `latest` or branch names — mutable tags silently change what gets deployed on the next task launch. Declare `image_tag` variables with no default so CI is forced to supply an explicit value. For environments with strict supply-chain requirements, pin by image digest (`@sha256:…`) instead. See [`references/docker-image-tagging.md`](references/docker-image-tagging.md) for the full pattern and the digest pinning alternative.

### Sensitive Values

Never hard-code secrets in configuration. Terraform stores secret values in state and plan files regardless of `sensitive = true` — that flag only redacts values from CLI output. Treat state as sensitive data: exclude it from version control and restrict IAM access.

For secrets that must not persist in state at all, use an `ephemeral` variable (Terraform 1.10+), which is never written to state or plan files:

```hcl
variable "db_password" {
  type        = string
  description = "Database password"
  sensitive   = true
  ephemeral   = true
}
```

Otherwise, pass secrets via environment variables (e.g. `TF_VAR_db_password`) or uncommitted `.tfvars` files, and retrieve them at runtime from an external secret manager (e.g. AWS Secrets Manager, SSM Parameter Store) using a data source.

Prefer ephemeral variables, ephemeral resources, and provider write-only arguments only where the receiving resource/provider explicitly supports them. If a value is passed into a normal resource argument, Terraform can still persist it in state.

**SSM Parameter Store secrets:** Terraform must not create or manage the secret values. Instead, accept an `ssm_parameter_prefix` variable (e.g. `/ai-exception/prod`), inject it as `SSM_PARAMETER_PREFIX` into the ECS task or Lambda environment, and grant IAM `ssm:GetParameter` scoped to `{prefix}/*`. The application fetches the actual values at runtime. See [`references/ssm-secrets-pattern.md`](references/ssm-secrets-pattern.md) for the full pattern including IAM policy, app-side provider selection, and the naming convention for parameters.

### Quality Gates and Validation

Automate basic quality gates before committing changes:

- Run `terraform fmt -check -recursive` to enforce canonical formatting. The Terraform style guide recommends running `terraform fmt` before each commit.
- Run `terraform validate` to ensure configuration is syntactically valid and internally consistent.
- Run `terraform test` (Terraform 1.6+) to execute native `*.tftest.hcl` tests for modules. Prefer it over third-party frameworks like Terratest for new test coverage — it runs in-process, requires no extra toolchain, and lives alongside the module it tests.
- Optionally run `tflint` and security scanners such as `tfsec` or `checkov` to catch provider-specific issues and insecure patterns. Use pre-commit hooks to automate these steps.

### File Organization

Organize your configuration into logical files for clarity. The Terraform style guide recommends the following conventions:

- `backend.tf` – backend configuration.
- `main.tf` – resource and data source definitions.
- `providers.tf` – provider blocks and configuration.
- `versions.tf` – global terraform block (`required_version` + `required_providers`). This repo uses `versions.tf`; match it for consistency. (The current HashiCorp style guide names this file `terraform.tf` — either is acceptable, but do not mix both in one tree.)
- `variables.tf` – all variable declarations (alphabetical order).
- `outputs.tf` – all outputs (alphabetical order).
- `locals.tf` – local values.

As configurations grow, split resources into separate files by logical group (e.g. `network.tf`, `compute.tf`, `storage.tf`). Keep a consistent order of parameters and blocks for readability.

### Module Design

Modules are small, single-purpose, and composed in the environment's `main.tf` — that is what makes them reusable across stacks and environments. A few concrete rules:

- **One module, one job.** A module named `vpc` should not also provision DNS. Compose small modules in the environment entry point rather than building a god-module that couples unrelated concerns.
- **`README.md` is required, not optional.** Document inputs, outputs, and at least one usage example. Generate it with [`terraform-docs`](https://terraform-docs.io/) so the docs stay in sync with the code — hand-written docs always rot.
- **Explicit interfaces.** Every input has a `type`, `description`, and (where non-trivial) a `validation` block. Every output has a `description`. Mark secret-bearing outputs `sensitive = true`.
- **No `provider` blocks in child modules.** Provider configurations belong in the root module and are passed down implicitly or explicitly via the module call. Child modules should declare provider requirements, not configure credentials, regions, or aliases internally.
- **No caller-context lookups inside the module.** Don't call `data "aws_caller_identity"` or `data "aws_region"` inside a shared module — take those as inputs instead, so the module is self-contained and unit-testable with `terraform test`.
- **Pin external modules to a tag, never a branch.** `version = "4.0.2"` is safe; `ref = "main"` turns `terraform init` into a surprise upgrade the next time someone re-inits.

## Adding a New Stack

1. **Create a module:** Add `Terraform/modules/{stack}/` with `main.tf`, `variables.tf`, `outputs.tf`, `versions.tf` (a `terraform` block declaring only the minimum `required_providers` versions — no `provider` blocks) and `README.md`. Pin external module versions to immutable tags.
2. **Create an environment entry:** Add `Terraform/environments/{env}/{stack}/` with `main.tf`, `backend.tf`, `providers.tf`, `versions.tf`, `variables.tf`, `outputs.tf` and `{env}.tfvars`. The `backend.tf` holds the backend type block only; pass environment-specific backend values with `terraform init -backend-config=...`.
3. **Add backend config:** Add `Terraform/backend-config/{env}/{stack}.backend.hcl` with bucket name, key and region. Ensure state bucket and IAM roles exist before initialization.
4. **Follow naming, variable and provider conventions:** Use default tags, input validation, version pinning and quality gates described above.

## Refactoring & Lifecycle Blocks

Modern Terraform provides declarative blocks for refactoring and for managing resource lifecycles. Use these instead of `terraform state mv`, `terraform import`, or manual state surgery — they live in code, survive rebases and PR reviews, and make the intent visible to everyone who reads the diff.

- **`moved` blocks (1.1+)** — rename a resource or move it between modules without destroying and recreating it. Required any time you rename an existing resource.

  ```hcl
  moved {
    from = aws_s3_bucket.logs
    to   = aws_s3_bucket.access_logs
  }
  ```

- **`import` blocks (1.5+)** — bring an existing resource under Terraform management declaratively. Preferred over the `terraform import` CLI command, which is imperative and leaves no trace in code.

  ```hcl
  import {
    to = aws_s3_bucket.tfstate
    id = "my-project-tfstate"
  }
  ```

  This assumes you already know the resource exists and needs importing. A bootstrap script that must decide *at runtime* whether the resource is already there (e.g. re-running stack creation idempotently against a bucket that may or may not exist yet) can't express that with a static block — the imperative `terraform import` CLI, guarded by a `head-bucket`-style existence check in the script, is the correct tool there. See the `deploy-scripts` skill's S3 Bootstrap Exception for the concrete pattern.

- **`removed` blocks (1.7+)** — drop a resource from state without destroying the real-world object (useful when handing a resource off to another stack or tool).

  ```hcl
  removed {
    from = aws_s3_bucket.legacy
    lifecycle { destroy = false }
  }
  ```

- **`check` blocks (1.5+)** — post-apply assertions that surface as warnings (not failures) when invariants break. Good for "this endpoint should be reachable" style checks that are not safe to fail the whole apply on.

Delete `import` and `removed` blocks after a full dev → staging → prod promotion cycle. Keep `moved` blocks longer in reusable modules or shared stacks where consumers may upgrade across multiple releases; they are cheap compatibility breadcrumbs for anyone who did not apply every intermediate version.

### The `lifecycle` Argument Block

Distinct from the meta-blocks above, `lifecycle { ... }` is a nested block on the resource itself, controlling how *that instance* is created, updated, and destroyed:

- **`prevent_destroy = true`** — hard-stop any plan that would destroy this resource, including via `terraform destroy`. Required on the tfstate bucket and any other resource an accidental destroy must never touch (the `deploy-scripts` skill's destroy orchestrator depends on this for the state bucket). Removing it requires deleting the line from source, not a flag on the CLI call — that friction is the point.
- **`create_before_destroy = true`** — build the replacement before tearing down the old one, instead of the default destroy-then-create. Use for anything that must not have a gap: an SG a live ENI still references (the direct fix for the stuck-destroy scenario in the ENI section above), a launch template mid-rollout, an ACM cert a listener depends on.
- **`ignore_changes = [...]`** — stop a specific attribute from producing a diff when something outside Terraform legitimately changes it: an ECS task definition's `desired_count` under autoscaling, tags applied by AWS Backup or a cost-allocation tool, an AMI ID a separate image pipeline rotates. Scope it to the exact attributes that drift, not `ignore_changes = all` — that hides real drift along with the expected kind.
- **`replace_triggered_by = [...]`** (1.2+) — force replacement of this resource when a referenced attribute elsewhere changes, for cases where Terraform wouldn't otherwise infer the dependency (e.g. recreate an EC2 instance when a `null_resource`/`terraform_data` trigger value changes).
- **`precondition` / `postcondition`** (1.2+) — assertions on this resource specifically that fail the apply immediately with a custom message, unlike `check` blocks (post-apply, warning-only, doc'd above). Use for invariants that must hold before Terraform proceeds (e.g. a variable-derived CIDR actually falls inside the VPC range).

```hcl
resource "aws_ecs_service" "worker" {
  # ...
  lifecycle {
    ignore_changes = [desired_count] # autoscaling owns this after initial apply
  }
}
```

## Bootstrapping Remote State

Because the backend bucket stores state outside Terraform's control, you must create it manually (or using a separate bootstrap script) before running `terraform init`. Enable S3 bucket versioning and encryption. Assign appropriate IAM permissions so that Terraform can read, write and lock state files.

## Module and Provider Upgrades

Upgrade Terraform core and providers separately — they have independent release cycles, and bundling the two makes it harder to attribute a regression. Follow this workflow:

1. **Check current versions.** Run `terraform version` (core) and `terraform providers` (providers in the current stack).
2. **Read the changelogs** for every version you are skipping over, not just the latest — breaking changes often land mid-series.
3. **Bump in dev first.** Update `required_version` or `required_providers` in a non-production environment, run `terraform init -upgrade`, then `terraform plan`. Resolve every warning or deprecation before promoting — they tend to become hard errors in the next major.
4. **Promote dev → staging → prod.** Never skip an environment; the staged rollout exists so each environment is a cheaper rehearsal for the next.
5. **Commit the lockfile.** `.terraform.lock.hcl` records exact provider checksums — always commit it for root modules (environment entry points) so teammates and CI resolve to the same binaries. Reusable child modules under `modules/` do not need their own committed lockfile unless they are also used as standalone roots.

For external modules, pin to a specific version tag (not a branch) and upgrade deliberately using the same dev → staging → prod flow.
