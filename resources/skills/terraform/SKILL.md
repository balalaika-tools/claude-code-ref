---
name: terraform
description: Terraform infrastructure patterns and conventions. Use when creating, modifying, or reviewing Terraform modules, environments, or backend configs.
user-invocable: false
---

# Terraform Structure

```
Terraform/
├── backend-config/{env}/        # Partial backend configs per stack
├── environments/{env}/{stack}/  # Stack entry points (variables, outputs, remote state refs)
└── modules/{stack}/             # Reusable resource definitions
```

Each logical grouping of resources is a **stack** (for example networking, compute, storage). Modules hold the resource definitions; environment folders wire them together with environment-specific values. The repository layout helps you locate stacks, modules and backend configuration quickly.

## Conventions

### Versioning

Pin Terraform and provider versions using a pessimistic constraint (`~>`). The exact behavior depends on the specificity of the constraint: `~> 1.6.0` allows only patch upgrades (1.6.x), while `~> 5.0` allows all minor upgrades within major version 5. Both prevent accidental major upgrades. For example:

```hcl
terraform {
  required_version = "~> 1.6.0" # allow any 1.6.x
  required_providers {
    aws    = { source = "hashicorp/aws",    version = "~> 5.0" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}
```

Update version constraints when upgrading Terraform or providers. Pin versions for external modules as well (e.g. `module "vpc" { source = "terraform-aws-modules/vpc/aws", version = "4.0.2" }`). Maintain an upgrade plan to test and roll out version changes across environments.

### Naming

All AWS resource names follow `{project_name}-{environment_name}-{resource}`. Avoid including the resource type in the name; the resource address already includes it. Use underscores for Terraform identifiers as a team convention — the language permits hyphens too, but underscores are the standard style (e.g. `aws_s3_bucket.tfstate_bucket`).

### Core Variables

Each stack defines at least the following variables:

- `project_name` – short project identifier.
- `environment_name` – environment (e.g. `dev`, `staging`, `prod`). Use a validation block or an enum to restrict allowed values.
- `aws_region` – AWS region. Validate using a regular list of approved regions.
- `tfstate_bucket`, `tfstate_region` – used for cross-stack remote state lookups.

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

The `default_tags` block applies tags to all taggable AWS resources managed by this provider. Avoid repeating `Project`, `Environment` or `ManagedBy` on individual resources; Terraform merges duplicate keys and may show diffs on first apply. Only include resource-specific identifiers (e.g. `Name`, `Function`). Omit the `tags` block entirely on resource types that do not support tagging.

### Backend

Use a remote S3 backend for state storage. Store partial backend configuration in `backend-config/{env}/{stack}.backend.hcl` and initialize with:

```
terraform init -backend-config=../../backend-config/{env}/{stack}.backend.hcl
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
    condition     = can(regex("^[a-z]{2}-[a-z]+-\\d+$", var.aws_region))
    error_message = "Region must be a valid AWS region code."
  }
}
```

Also consider validating CIDR blocks, port ranges, counts, and booleans to prevent unsafe defaults. Only expose variables that will differ across environments; overuse of variables makes code harder to understand.

### Tagging

Tags are applied at two levels:

- **Provider default tags:** The `default_tags` block in the provider injects common tags (`Project`, `Environment`, `ManagedBy`). This ensures consistent auditing, cost tracking and IAM policies. Do not repeat these keys on individual resources.
- **Resource-specific tags:** Define resource-specific identifiers such as `Name` and, for Lambda functions, `Function`. For example:

```hcl
resource "aws_lambda_function" "handler" {
  # ...
  tags = {
    Name     = "${var.project_name}-${var.environment_name}-handler"
    Function = "handler"
  }
}
```

Omit the `tags` block entirely on resource types that do not support tagging (policy attachments, route associations, security group rules, etc.).

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

### Quality Gates and Validation

Automate basic quality gates before committing changes:

- Run `terraform fmt -check -recursive` to enforce canonical formatting. The Terraform style guide recommends running `terraform fmt` before each commit.
- Run `terraform validate` to ensure configuration is syntactically valid and internally consistent.
- Optionally run `tflint` and security scanners such as `tfsec` or `checkov` to catch provider-specific issues and insecure patterns. Use pre-commit hooks to automate these steps.

### File Organization

Organize your configuration into logical files for clarity. The Terraform style guide recommends the following conventions:

- `backend.tf` – backend configuration.
- `main.tf` – resource and data source definitions.
- `providers.tf` – provider blocks and configuration.
- `terraform.tf` – global terraform block specifying required versions.
- `variables.tf` – all variable declarations (alphabetical order).
- `outputs.tf` – all outputs (alphabetical order).
- `locals.tf` – local values.

As configurations grow, split resources into separate files by logical group (e.g. `network.tf`, `compute.tf`, `storage.tf`). Keep a consistent order of parameters and blocks for readability.

## Adding a New Stack

1. **Create a module:** Add `Terraform/modules/{stack}/` with `main.tf`, `variables.tf`, `outputs.tf` and optional `README.md`. Pin module versions when sourcing external modules.
2. **Create an environment entry:** Add `Terraform/environments/{env}/{stack}/` with `main.tf`, `backend.tf`, `variables.tf`, `outputs.tf` and `{env}.tfvars`. The `backend.tf` should reference the partial config file as shown above.
3. **Add backend config:** Add `Terraform/backend-config/{env}/{stack}.backend.hcl` with bucket name, key and region. Ensure state bucket and IAM roles exist before initialization.
4. **Follow naming, variable and provider conventions:** Use default tags, input validation, version pinning and quality gates described above.

## Bootstrapping Remote State

Because the backend bucket stores state outside Terraform's control, you must create it manually (or using a separate bootstrap script) before running `terraform init`. Enable S3 bucket versioning and encryption. Assign appropriate IAM permissions so that Terraform can read, write and lock state files.

## Module and Provider Upgrades

Upgrade Terraform core and providers separately — they have independent release cycles. Follow this workflow:

1. **Check current versions:** Run `terraform version` (core) and `terraform providers` (providers in the current stack).
2. **Review changelogs** for breaking changes before bumping constraints.
3. **Bump in dev first:** Update `required_version` or `required_providers` in a non-production environment, run `terraform init -upgrade`, then `terraform plan`. Resolve any warnings or deprecations before promoting.
4. **Promote through environments:** Apply the version bump to staging, verify, then prod. Never skip an environment.
5. **Commit lockfile changes:** The `.terraform.lock.hcl` file records exact provider checksums — always commit it for root modules (environment entry points) so all team members and CI use the same provider binaries. Reusable child modules under `modules/` do not need their own committed lockfile unless they are also used as standalone roots.

For external modules, pin to a specific version tag (not a branch) and upgrade deliberately using the same dev → staging → prod flow.
