# AWS Environment Values and Topology Variants

Use one stack root across environments when the resource graph is the same.
Use separate roots when the implementation or lifecycle is materially
different. Do not copy an entire root into `dev`, `staging`, and `prod` merely
to change capacity.

The separate-roots rule applies mainly **within the platform tier**, where a
database or cache can legitimately be a different product per environment.
Application stacks should not fork by environment: a service that runs on ECS in
staging and something else in production is two services, and the difference
belongs behind the platform contract in
[`platform-application-split.md`](platform-application-split.md) rather than in
two app roots. Capacity, concurrency, and retention differences stay typed input
values.

## Contents

- [Value Differences: One Root](#value-differences-one-root)
- [Bounded Variants: Use Judgment](#bounded-variants-use-judgment)
- [Different Topology: Separate Roots](#different-topology-separate-roots)
- [Decision Rule](#decision-rule)

## Value Differences: One Root

Keep the root under `Terraform/stacks/{stack}/` and define typed configuration:

```hcl
variable "database" {
  description = "Environment-specific database capacity and availability"
  type = object({
    instance_class            = string
    allocated_storage_gib     = number
    max_allocated_storage_gib = number
    multi_az                  = bool
    backup_retention_days     = number
    deletion_protection       = bool
  })

  validation {
    condition = (
      var.database.allocated_storage_gib > 0 &&
      var.database.max_allocated_storage_gib >= var.database.allocated_storage_gib
    )
    error_message = "Database storage values are inconsistent."
  }
}
```

Use cheaper staging values:

```hcl
# Terraform/environments/staging/platform-data.tfvars
database = {
  instance_class            = "db.t4g.medium"
  allocated_storage_gib     = 50
  max_allocated_storage_gib = 200
  multi_az                  = false
  backup_retention_days     = 7
  deletion_protection       = false
}
```

Use resilient production values:

```hcl
# Terraform/environments/prod/platform-data.tfvars
database = {
  instance_class            = "db.r7g.large"
  allocated_storage_gib     = 200
  max_allocated_storage_gib = 1000
  multi_az                  = true
  backup_retention_days     = 35
  deletion_protection       = true
}
```

Apply the same pattern to ECS desired/min/max capacity, Lambda memory and
concurrency, log retention, NAT gateway count, alarm thresholds, and similar
operational differences.

Before changing an input, inspect the provider schema and plan. A value that
looks like sizing can still force replacement. Treat database engine changes,
identifier changes, subnet-group changes, and encryption-key changes as
migrations rather than routine environment tuning.

## Bounded Variants: Use Judgment

A single root may support a small explicit variant when:

- Both variants have the same ownership and state lifecycle.
- Both are intentionally tested and maintained.
- The conditional resources remain easy to understand.
- Consumers receive one stable output contract.

Avoid a forest of booleans such as `create_rds`, `create_aurora`,
`create_replica`, and `create_proxy`. Prefer one validated discriminator and
clear module boundaries if the variant remains bounded.

## Different Topology: Separate Roots

Use separate roots when environments use different products or graphs, for
example:

```text
Terraform/stacks/platform-data-rds/
Terraform/stacks/platform-data-aurora/
```

Keep their externally consumed outputs compatible:

```hcl
output "database_endpoint_parameter_name" {
  description = "SSM parameter through which applications discover the database endpoint"
  value       = aws_ssm_parameter.database_endpoint.name
}
```

Prefer publishing a stable discovery value to SSM or DNS so application stacks
do not care which database implementation produced it.

Make the environment-to-root mapping explicit in each standalone deployment
wrapper:

```text
staging: logical stack "platform-data" -> root "platform-data-rds"
prod:    logical stack "platform-data" -> root "platform-data-aurora"
```

Give both roots distinct backend keys. Never point two different roots at the
same state object.

If an environment later changes implementations, create the replacement in its
own state and plan an explicit consumer cutover. The old and new roots must not
manage the same SSM parameter, DNS record, or other discovery object
concurrently. Transfer ownership with a reviewed `removed`/`import` sequence,
or publish to a temporary name and switch consumers before retiring the old
object. Treat this as a migration, not as a routine root-selection change.

## Decision Rule

1. If only values differ, use one root and environment tfvars.
2. If a small, maintained option differs but the lifecycle is shared, consider
   one validated variant.
3. If resource kinds, ownership, migration path, or lifecycle differ, use
   separate roots with a stable consumer contract.
4. If the repository already uses thin environment wrappers successfully,
   preserve them unless the user requests this migration.
