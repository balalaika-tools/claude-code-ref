# Platform and Application Stack Split

Split an environment's Terraform into two tiers instead of one stack that owns
everything. The dividing line is **rate of change**, not resource type.

## Contents

- [The Split Rule](#the-split-rule)
- [One App Stack per Releasable Service](#one-app-stack-per-releasable-service)
- [When Not to Split](#when-not-to-split)
- [Shared Namespace Allocation](#shared-namespace-allocation)
- [Platform to Application Contract](#platform-to-application-contract)

## The Split Rule

| Tier | Changes | Owns | Applied by |
|---|---|---|---|
| **Platform** | weekly to monthly | VPC, subnets, NAT, shared security groups, ECS/EKS cluster, ALB and its default listener, RDS/Aurora, ElastiCache, ECR repositories, shared KMS keys, Route 53 zones, state bucket | an infrastructure workflow, on a change under `stacks/platform-*/` or on manual dispatch |
| **Application** | daily to hourly | task definition and ECS service, Lambda function and alias, launch template and ASG, Step Functions state machine, per-service target group and listener rule, per-service task and execution roles, log group, autoscaling target | a per-service release workflow, on a change to that service's source or stack |

The reason is not tidiness. Under one whole-environment stack, every code push
runs `apply` with a role that can also modify databases and networking, and
every release plans hundreds of unrelated resources. The split bounds both the
IAM blast radius of a release and the size of its plan.

Name the roots `stacks/platform-<name>/` and `stacks/app-<service>/`. Keep
**exactly one directory level** under `stacks/`: the `TF_DATA_DIR` and
backend-key derivation used by this skill and by `deploy-scripts` assume
`stacks/<name>/`. Do not nest into `stacks/platform/<name>/`.

## One App Stack per Releasable Service

**Default mapping: one app stack per independently releasable service.** A
repository with four services has four app stacks and four state files. That is
the point of the model — each service releases on its own cadence, holds its own
state lock, uses its own deployment role, and cannot plan or touch another
service's resources.

A three-platform, three-application repository:

```text
Terraform/
├── backend-config/{dev,staging,prod}/
│   ├── platform-network.backend.hcl
│   ├── platform-data.backend.hcl
│   ├── platform-ecr.backend.hcl
│   ├── app-api.backend.hcl
│   ├── app-worker.backend.hcl
│   └── app-scheduler.backend.hcl
├── environments/{dev,staging,prod}/
│   └── <the same six>.tfvars
├── stacks/
│   ├── platform-network/     # VPC, subnets, NAT, shared SGs, ALB + default listener
│   ├── platform-data/        # RDS, ElastiCache, shared KMS
│   ├── platform-ecr/         # one repository per service
│   ├── app-api/              # task definition, service, target group, listener rule, task role
│   ├── app-worker/           # task definition, service, no ingress
│   └── app-scheduler/        # Step Functions + Lambda
└── modules/
    ├── ecs-service/          # written ONCE, called by app-api and app-worker
    ├── lambda-function/
    └── alb-target-group/
```

Six stacks across three environments is 18 backend files and 18 tfvars files.
That multiplication is the real cost of the model. Expect it up front rather
than discovering it at service four.

**What keeps it cheap: shared modules and thin roots.** `modules/ecs-service/`
is written once and consumed by every ECS app root. Each app root should be a
provider block, a backend block, a handful of `data "aws_ssm_parameter"`
lookups, one module call, and its outputs — on the order of 60 to 100 lines. If
app roots start diverging into hundreds of lines of bespoke resources, the
module boundary is wrong. Thin roots are what make N stacks affordable.

**No inter-app ordering.** App stacks are siblings, not a chain. They depend on
the platform tier and not on each other. If service A needs a value from service
B, that is a published contract — an SSM parameter, a queue URL, a DNS name —
not a stack ordering dependency. A deployment stack list therefore holds
platform stacks in dependency order followed by app stacks in any order.

## When Not to Split

The floor, so this model does not become boilerplate sprawl:

- Services that **always ship together** share one app stack. Two services
  behind one release train are one deployable unit.
- Below roughly three services and roughly two deploys per week, one combined
  stack is simpler and defensible. The triggers to split are **deploy
  frequency** and **IAM blast radius**, not aesthetics.
- A stack is never warranted merely because code can be factored into a module.

Each additional app stack costs one backend file per environment, one tfvars
file per environment, one lockfile, one deploy/destroy script pair, one entry in
the deployment stack list, and one cross-stack contract edge. Count that before
adding the stack.

## Shared Namespace Allocation

Anything with a single shared namespace across app stacks needs an allocation
rule, or two stacks planned concurrently will derive the same value and the
second apply will fail.

### ALB listener rule priorities

Priorities are one integer namespace (1 to 50000) per listener. The platform
tier owns the load balancer, the listener, and its default action. Each app
stack owns its own target group and listener rule, and receives its priority as
a **required input with no default**:

```hcl
variable "listener_rule_priority" {
  description = "Priority allocated to this service in platform-network/listener-priorities.md"
  type        = number

  validation {
    condition     = var.listener_rule_priority >= 1 && var.listener_rule_priority <= 50000
    error_message = "listener_rule_priority must be between 1 and 50000."
  }
}
```

Never compute a priority dynamically — for example from a `max()` over existing
rules discovered by a data source. Two app stacks planned at the same time read
the same current state and both pick the same next number.

Keep the allocation in **one committed file** so adding a service produces a
reviewable diff:

```text
Terraform/stacks/platform-network/listener-priorities.md

| Priority | Service   | Rule condition            |
|---------:|-----------|---------------------------|
|      100 | api       | host api.example.com      |
|      200 | scheduler | path /schedules/*         |
|      300 | admin     | host admin.example.com    |

Spacing of 100 leaves room to add per-service rules later.
The platform-owned default action has no priority and is not listed.
`app-worker` has no ingress and holds no allocation.
```

Use a validated `map(number)` variable in the platform stack instead when the
allocation should be machine-checked for duplicates. Either way, one file owns
it.

### API Gateway

Default to **one API per service**, owned by that app stack. There is then no
shared namespace at all. If a shared API is genuinely required, the platform
tier owns the API and its stage, and each app stack owns only its own
routes and integrations under an explicitly allocated path prefix, supplied the
same way as a listener priority: a required input, no default.

### Route 53

The platform tier owns the hosted zone. App stacks own only their own record
names within it, and receive the zone ID from the platform contract.

## Platform to Application Contract

The platform tier's published SSM parameter set **is its public API**.

Publish non-secret discovery values under
`/{project}/{env}/platform/{component}/{key}`, which extends the hierarchy in
[`ssm-secrets-pattern.md`](ssm-secrets-pattern.md) with a `platform` component
segment. Secrets keep using the store selected for that environment; this
namespace is for identifiers:

```hcl
resource "aws_ssm_parameter" "private_subnet_ids" {
  name  = "/${var.project_name}/${var.environment_name}/platform/network/private_subnet_ids"
  type  = "StringList"
  value = join(",", module.vpc.private_subnet_ids)
}
```

App stacks read those parameters with a data source:

```hcl
data "aws_ssm_parameter" "private_subnet_ids" {
  name = "/${var.project_name}/${var.environment_name}/platform/network/private_subnet_ids"
}

locals {
  private_subnet_ids = split(",", nonsensitive(data.aws_ssm_parameter.private_subnet_ids.value))
}
```

The `value` attribute is marked sensitive by the provider regardless of
parameter type, so wrap it in `nonsensitive()` before using it in `for_each`, a
resource name, or an output. Wrapping a genuine secret this way defeats
redaction; only do it for identifiers.

Rules that make this a contract rather than a convention:

- **Never use `terraform_remote_state` for the platform tier.** Output access
  implies read access to the entire platform state snapshot, which includes
  every other value in it. This is the existing cross-stack rule and the split
  makes it load bearing.
- **Parameter names are a breaking-change surface.** Renaming or removing a
  published parameter is a platform release with a consumer cutover, not a
  refactor. Publish the new name, cut consumers over, then retire the old one.
- **Data sources resolve at plan time.** An app plan fails outright when a
  platform parameter is absent. That is correct behaviour, not a bug to work
  around with a default or a `try()`. The app workflow should report
  `platform stack not applied for ENV=<env>` rather than proceeding.
- **Keep the published set small, stable, and acyclic.** A platform stack never
  reads an app stack's parameters.

Typical published set for a network platform stack: `vpc_id`,
`private_subnet_ids`, `public_subnet_ids`, `alb_https_listener_arn`,
`alb_dns_name`, `alb_zone_id`, `ecs_cluster_arn`, `ecs_cluster_name`,
`route53_zone_id`. For a data platform stack: `database_endpoint_parameter_name`
(or the endpoint itself), `database_security_group_id`, `cache_endpoint`,
`kms_key_arn`. For ECR: `<service>_repository_url` per service.
