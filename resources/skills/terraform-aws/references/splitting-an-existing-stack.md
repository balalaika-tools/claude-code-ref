# Splitting an Existing Stack into Platform and Application Tiers

Carve application resources out of a combined whole-environment stack without
destroying or recreating anything. The target model is in
[`platform-application-split.md`](platform-application-split.md).

This is a state migration, so it needs explicit authorization for every mutating
step and a review of each plan before it runs.

## Contents

- [Before Starting](#before-starting)
- [Step 1: Inventory and Classify](#step-1-inventory-and-classify)
- [Step 2: Publish the Platform Contract First](#step-2-publish-the-platform-contract-first)
- [Step 3: Build the App Root and Import](#step-3-build-the-app-root-and-import)
- [Step 4: Release Ownership in the Source Root](#step-4-release-ownership-in-the-source-root)
- [Step 5: Cut Over and Retire](#step-5-cut-over-and-retire)
- [Import Identifiers](#import-identifiers)

## Before Starting

- `moved` blocks work **only within one state**. Moving a resource to a
  different root means `import` in the destination plus `removed` in the source.
  There is no single-block equivalent across state boundaries.
- Confirm `required_version` allows both: `import` blocks need Terraform 1.5.0
  (1.7.0 for `for_each`), `removed` blocks need 1.7.0. Below that floor the only
  path is an explicitly authorized imperative `state rm`.
- Confirm the state bucket has versioning enabled, then take an out-of-band
  backup of the source state: `terraform state pull > /tmp/<stack>-<env>.json`,
  stored outside the repository.
- Freeze applies on the source root for the duration. Between the import and the
  removal, two states reference the same objects; a source apply during that
  window is the one thing that can destroy them.
- Do the whole sequence in the cheapest environment first, end to end, before
  touching production.

## Step 1: Inventory and Classify

```sh
terraform state list > /tmp/inventory.txt
```

Assign every address to the platform tier or to one app stack. Then look for the
edges that the inventory does not show:

- Security group rules in the source root that reference an app security group
  that is moving. Decide which side owns each rule; a rule and its security
  group can live in different states, but the referencing side then needs the
  other's ID from the contract.
- IAM policies attached to roles that are moving.
- Outputs of the source root that other stacks or scripts consume. Each one
  either stays (platform) or is republished by the app stack.
- Anything with a shared namespace — listener rule priorities, API paths, DNS
  records. Allocate these before writing the new root.

Resources that are cheap and safe to recreate do not need importing. An ECS task
definition is the clearest case: revisions are immutable, inactive revisions cost
nothing, and the app stack will register a fresh revision on its first apply
regardless. Import the **service**, not its task definition history.

## Step 2: Publish the Platform Contract First

Add the SSM parameters the app stacks will read, in the source root, and apply.
This is a pure addition — no app resource is touched — so it can ship as an
ordinary change well before the split:

```hcl
resource "aws_ssm_parameter" "private_subnet_ids" {
  name  = "/${var.project_name}/${var.environment_name}/platform/network/private_subnet_ids"
  type  = "StringList"
  value = join(",", module.vpc.private_subnet_ids)
}
```

Doing this first means the new app root can plan at all: its data sources resolve
at plan time and fail hard when a parameter is missing.

## Step 3: Build the App Root and Import

Create `stacks/app-<service>/` with a **new backend key**, its own tfvars and
backend file per environment, and configuration that reproduces the existing
resources exactly. Never point the new root at the source root's state object.

Copy the arguments from the live configuration rather than rewriting them.
Anything you "improve" during the move turns a zero-diff import into a real
change, and you lose the one signal that tells you the carve-out was faithful.

Add `import` blocks for each adopted resource:

```hcl
import {
  to = module.api.aws_ecs_service.this
  id = "my-project-prod-cluster/my-project-prod-api"
}

import {
  to = module.api.aws_lb_target_group.this
  id = "arn:aws:elasticloadbalancing:eu-west-1:123456789012:targetgroup/my-project-prod-api/0123456789abcdef"
}
```

Plan with the environment's backend and read the header:

```text
Plan: 4 to import, 0 to add, 0 to change, 0 to destroy.
```

**Anything other than `0 to add, 0 to change, 0 to destroy` means stop.** Fix the
configuration until the only line is the import count. A single `to destroy` here
is an outage.

One exception is expected and must be understood before applying: the imported
`aws_ecs_service` will show a `task_definition` change, because the new root
registers its own revision. Keep the same image digest so the new revision is
functionally identical, and treat that first apply as a real rolling deployment —
schedule it accordingly. If a zero-change apply is required, import the current
task definition revision too and switch to a Terraform-registered revision on the
next ordinary release.

Apply the import once the plan is clean. The remote objects are unchanged; only
the new state file grows.

## Step 4: Release Ownership in the Source Root

A `removed` block requires the resource or module block to be **absent** from
configuration, so the deletion and the block ship in the same change:

```hcl
removed {
  from = module.api

  lifecycle {
    destroy = false
  }
}
```

Review the resolved `from` addresses and the plan before applying. This mutates
state; `destroy = false` is what keeps the remote objects alive. Applying a
`removed` block without that nested `lifecycle` destroys the infrastructure you
just imported.

Then verify both sides are quiet:

```sh
terraform plan -detailed-exitcode -var-file=... # 0 = no changes, 2 = changes, 1 = error
```

Exit code 0 on the source root and on the new app root is the completion
criterion for the move. Compare `terraform state list | wc -l` on both roots
against the inventory so nothing was left behind or adopted twice.

**Never let both roots manage the same SSM parameter, DNS record, or other
discovery object concurrently.** Two owners of one parameter means each apply
overwrites the other. Hand these over with the same import-then-remove sequence,
or publish under a new name, cut consumers over, and retire the old name.

## Step 5: Cut Over and Retire

1. Add the app stack's deploy and destroy scripts and its entry in the
   deployment stack list, in the unordered app section.
2. Add its release workflow and its scoped deployment role, and narrow the
   existing broad role so it no longer needs the app resources.
3. Repeat steps 3 and 4 for each remaining service, one service at a time. Do
   not batch several services into one import.
4. Rename the drained source root to `stacks/platform-<name>/` once only
   platform resources remain. A directory rename changes the `TF_DATA_DIR` and
   the backend key, so treat it as its own reviewed backend migration or keep the
   existing name and accept the mismatch until a natural opportunity.
5. Delete the `import` blocks from the app roots and the `removed` blocks from
   the source root after every environment has crossed. Leaving them costs
   nothing functionally but misleads the next reader.

## Import Identifiers

The identifiers most often needed in this migration:

| Resource | Import ID |
|---|---|
| `aws_ecs_service` | `<cluster-name>/<service-name>` |
| `aws_ecs_task_definition` | full task definition ARN, including the revision |
| `aws_lb_target_group` | target group ARN |
| `aws_lb_listener_rule` | listener rule ARN |
| `aws_iam_role` | role name |
| `aws_iam_role_policy` | `<role-name>:<policy-name>` |
| `aws_iam_role_policy_attachment` | `<role-name>/<policy-arn>` |
| `aws_cloudwatch_log_group` | log group name |
| `aws_lambda_function` | function name |
| `aws_lambda_alias` | `<function-name>/<alias-name>` |
| `aws_appautoscaling_target` | `<service-namespace>/<resource-id>/<scalable-dimension>` |
| `aws_security_group` | security group ID |
| `aws_vpc_security_group_ingress_rule` | security group rule ID (`sgr-...`) |
| `aws_ssm_parameter` | parameter name, including the leading `/` |
| `aws_sfn_state_machine` | state machine ARN |

Confirm each one against the provider documentation for the version in the
lockfile before relying on it; import IDs occasionally change between major
provider releases.
