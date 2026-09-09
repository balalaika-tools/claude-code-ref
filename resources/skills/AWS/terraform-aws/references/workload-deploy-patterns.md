# Per-Workload Application Deploy Patterns

How an application-tier stack turns a built artifact into a running release, per
workload type. The stack boundary itself is in
[`platform-application-split.md`](platform-application-split.md).

## Contents

- [The Artifact Rule](#the-artifact-rule)
- [ECS Services](#ecs-services)
- [Lambda Functions](#lambda-functions)
- [EC2 and Auto Scaling Groups](#ec2-and-auto-scaling-groups)
- [Step Functions](#step-functions)
- [API Gateway](#api-gateway)
- [EKS](#eks)

## The Artifact Rule

| Workload | Artifact | What the app-stack apply changes |
|---|---|---|
| ECS | image digest, or Git SHA tag in an immutable repository | new task definition revision, then the service |
| Lambda (zip) | versioned S3 object | `s3_key` + `s3_object_version`, new version, alias shift |
| Lambda (container) | image digest | `image_uri` pinned to a digest |
| EC2 / ASG | immutable AMI ID | new launch template version, then an ASG instance refresh |
| Step Functions | definition plus the referenced function and task versions | state machine definition |
| API Gateway | OpenAPI body or route set | routes, integrations, deployment |
| EKS | image digest **plus a commit to the GitOps repository** | nothing — Terraform is not in the release path |

Every artifact type follows the rule already stated for images in
[`docker-image-tagging.md`](docker-image-tagging.md): **immutable, explicitly
versioned, no convenience default.** An AMI ID and an S3 object version are
artifact versions in exactly the same sense as an image digest. Give each one a
typed, validated variable with no default, so a release that forgot to build
fails at plan instead of silently redeploying the previous artifact.

```hcl
variable "api_ami_id" {
  description = "AMI published by the image build for this release"
  type        = string

  validation {
    condition     = can(regex("^ami-[0-9a-f]{8,17}$", var.api_ami_id))
    error_message = "api_ami_id must be an ami-<hex> identifier."
  }
}
```

Pass artifact values through a generated, transient artifact tfvars file or
explicit `TF_VAR_*` values — never a committed default.

## ECS Services

The app stack owns the task definition, the service, the log group, the task and
execution roles, the target group, and the listener rule. The platform stack
owns the cluster and the load balancer.

```hcl
resource "aws_ecs_task_definition" "api" {
  family                   = "${var.project_name}-${var.environment_name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.api.cpu
  memory                   = var.api.memory
  execution_role_arn       = aws_iam_role.api_execution.arn
  task_role_arn            = aws_iam_role.api_task.arn

  container_definitions = jsonencode([{
    name         = "api"
    image        = "${local.api_repository_url}@${var.api_image_digest}"
    essential    = true
    portMappings = [{ containerPort = var.api.container_port, protocol = "tcp" }]
    secrets      = [for name, arn in var.api_secret_arns : { name = name, valueFrom = arn }]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "api"
      }
    }
  }])
}

resource "aws_ecs_service" "api" {
  name            = "${var.project_name}-${var.environment_name}-api"
  cluster         = local.ecs_cluster_arn
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api.desired_count
  launch_type     = "FARGATE"

  wait_for_steady_state = true

  network_configuration {
    subnets         = local.private_subnet_ids
    security_groups = [aws_security_group.api_tasks.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = var.api.container_port
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  lifecycle {
    ignore_changes = [desired_count] # only when autoscaling owns it after creation
  }
}
```

- **Do not set `ignore_changes = [task_definition]`.** This stack owns the task
  definition; ignoring it would leave Terraform holding a resource it can never
  update, and the image variable would become dead code. For a repository that
  already has it, see the recognition rule in `SKILL.md` under Resource and AWS
  Patterns before changing anything.
- `wait_for_steady_state = true` makes a failed rollout fail the apply. Without
  it the apply succeeds the moment the new revision is registered, and a
  crash-looping release reports as a successful deploy.
- `deployment_circuit_breaker` with `rollback = true` returns the service to the
  last healthy revision instead of grinding. Combined with the wait, the apply
  still fails, which is what you want.
- Keep `ignore_changes = [desired_count]` only where an autoscaling target
  genuinely owns capacity after creation.

The target group and listener rule live in the same stack, with the priority
allocated in the platform tier's committed table:

```hcl
resource "aws_lb_target_group" "api" {
  name        = "${var.project_name}-${var.environment_name}-api" # 32-character limit
  port        = var.api.container_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = local.vpc_id

  health_check {
    path                = "/healthz"
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_lb_listener_rule" "api" {
  listener_arn = local.alb_https_listener_arn
  priority     = var.listener_rule_priority

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  condition {
    host_header {
      values = [var.api_host_name]
    }
  }
}
```

Target group names are limited to 32 characters, so a long project and
environment prefix will hit the limit before a long service name does. A target
group that is still attached to a listener rule cannot be deleted, which is why
`create_before_destroy` belongs here.

**Expected release latency:** an app-stack release is an `init`, `plan`, and
`apply` cycle — roughly one to three minutes before the new revision reaches the
service, plus the rolling deployment itself. That is the normal cost of
Terraform owning the task definition, not a sign of a stuck deploy.

## Lambda Functions

Keep Python source under `lambdas/<function>/` at the root of the repository that
owns it — which is not this repository under a split layout — never in HCL or a
Terraform module. Read
[`python-lambda.md`](python-lambda.md) for the uv dependency/build policy and the
boundary between a thin AWS handler and substantial application business logic.

For a zip artifact, publish to a versioned S3 bucket and deploy the object
version. Terraform is the native deploy mechanism here; nothing about this path
is an exception.

```hcl
resource "aws_lambda_function" "worker" {
  function_name = "${var.project_name}-${var.environment_name}-worker"
  role          = aws_iam_role.worker.arn
  handler       = var.worker.handler
  runtime       = var.worker.runtime
  memory_size   = var.worker.memory_mib
  timeout       = var.worker.timeout_seconds

  s3_bucket         = var.artifact_bucket_name
  s3_key            = var.worker_lambda_s3_key
  s3_object_version = var.worker_lambda_s3_object_version
  source_code_hash  = var.worker_lambda_source_code_hash

  publish = true
}

resource "aws_lambda_alias" "worker_live" {
  name             = "live"
  function_name    = aws_lambda_function.worker.function_name
  function_version = aws_lambda_function.worker.version
}
```

- Prefer an S3 object over a local `filename` so a plan does not depend on a
  build directory being present. A plan run on a clean checkout must still work.
- `s3_object_version` requires bucket versioning. Without it the field is null
  and two different builds under the same key look identical to Terraform.
- `source_code_hash` is what makes AWS see a real change; carry the
  `base64sha256` of the zip through from the build.
- `publish = true` creates an immutable version. Everything that invokes the
  function — event source mappings, Step Functions, API Gateway integrations —
  should reference the **alias**, never `$LATEST`, so the release is the alias
  shift and rollback is pointing the alias back.

For a container-image Lambda, drop the S3 arguments and set
`package_type = "Image"` with `image_uri` pinned to a digest
(`<repo-url>@sha256:...`), never a mutable tag.

## EC2 and Auto Scaling Groups

Releases go through a **new AMI**. Do not copy application code onto running
instances, and do not treat an `aws s3 sync` plus `apply` as a deploy: when
`user_data` is unchanged the apply is a no-op, and the deploy reports success
having shipped nothing.

```hcl
resource "aws_launch_template" "api" {
  name_prefix            = "${var.project_name}-${var.environment_name}-api-"
  image_id               = var.api_ami_id
  instance_type          = var.api.instance_type
  update_default_version = true

  iam_instance_profile {
    arn = aws_iam_instance_profile.api.arn
  }

  vpc_security_group_ids = [aws_security_group.api.id]

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_autoscaling_group" "api" {
  name                = "${var.project_name}-${var.environment_name}-api"
  vpc_zone_identifier = local.private_subnet_ids
  min_size            = var.api.min_size
  max_size            = var.api.max_size
  target_group_arns   = [aws_lb_target_group.api.arn]
  health_check_type   = "ELB"

  launch_template {
    id      = aws_launch_template.api.id
    version = aws_launch_template.api.latest_version
  }

  instance_refresh {
    strategy = "Rolling"

    preferences {
      min_healthy_percentage = 90
      instance_warmup        = 300
      auto_rollback          = true
    }
  }

  lifecycle {
    ignore_changes = [desired_capacity] # only when a scaling policy owns it
  }
}
```

- A new launch template version does **not** replace running instances by
  itself. `instance_refresh` is what rolls them, and it triggers on a
  `launch_template` or `mixed_instances_policy` change; use its `triggers`
  argument to add others.
- Pin the ASG to `latest_version` (or the specific new version), not
  `"$Default"`, or a released template version may never be picked up.
- `user_data` changes take effect only on instance replacement. Bake
  configuration into the AMI or fetch it at boot; do not expect an edited
  `user_data` to reconfigure a running fleet.
- `health_check_type = "ELB"` makes the refresh wait for target group health
  rather than only EC2 status checks.
- Terraform returns as soon as the refresh starts. Have the release workflow
  wait for completion, or a failed rollout looks like a successful deploy.
- Auto Scaling Groups do not receive provider `default_tags`; set their tags
  explicitly.

## Step Functions

Naturally per-service, with no shared namespace. The state machine definition is
the artifact, and it must reference qualified function versions:

```hcl
resource "aws_sfn_state_machine" "ingest" {
  name     = "${var.project_name}-${var.environment_name}-ingest"
  role_arn = aws_iam_role.ingest.arn

  definition = templatefile("${path.module}/definition.asl.json", {
    worker_function_arn = aws_lambda_alias.worker_live.arn
  })
}
```

Passing the alias ARN rather than the unqualified function ARN keeps the state
machine and the function version releasing together. Grant `lambda:InvokeFunction`
on the alias ARN, not the bare function.

## API Gateway

One API per service by default, owned by the app stack. Deploy either an OpenAPI
document as the `body` of an `aws_api_gateway_rest_api`, or explicit
`aws_apigatewayv2_route` and `_integration` resources for an HTTP API. Point
integrations at a Lambda alias for the same reason as above. If a shared API is
unavoidable, the platform tier owns the API and stage and each app stack owns
only its allocated path prefix — see
[`platform-application-split.md`](platform-application-split.md).

## EKS

Terraform is not in the application release path at all. The release is an image
digest plus a commit to the GitOps source, reconciled by Argo CD or Flux. See
[`eks-gitops.md`](eks-gitops.md).
