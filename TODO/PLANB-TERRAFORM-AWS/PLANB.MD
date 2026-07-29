# Model B: Pipeline-Owned ECS Task Definitions

**Status:** reference document, not implemented, not part of either skill.

This describes the alternative this repo's skills deliberately do **not**
default to. `PLAN.MD` implements Model C (Terraform owns the task definition,
inside a small per-service app stack) as the skill default, and ships exactly two
lines about this model — a latency-expectation note and a recognition rule so an
agent meeting an existing B repo doesn't damage it. Everything else about B lives
here, on purpose, so it can't leak into the skill's generated output.

Read this if: you're deciding whether to adopt B for a specific service, you
inherited a repo already built this way and want to understand it, or you're
migrating a service between B and C.

---

## 1. The core idea

Terraform creates the ECS service and IAM the first time, then gets out of the
way of the thing that changes every release — the task definition. A
deployment pipeline (not `terraform apply`) registers new task definition
revisions and points the service at them.

| | Owner | An app release is | Deploy role can touch |
|---|---|---|---|
| **Model C** (skill default) | Terraform, per-service app stack | `terraform apply` over ~10 resources, 1–3 min | that one app stack's resources |
| **Model B** (this doc) | Pipeline, via AWS API | `register-task-definition` + `update-service`, seconds | ECS actions + `iam:PassRole` on two roles |

The trade: B is faster and its blast radius is procedurally narrower (no
`terraform plan` touches unrelated resources by construction), but the task
definition's **body** — image, env vars, secret ARNs, cpu/memory, port mappings,
log configuration — moves out of Terraform state into whatever the pipeline
renders. Terraform can no longer tell you what's actually running without
querying ECS directly, and `terraform plan` on the service stack will show
perpetual drift on that field unless suppressed.

---

## 2. Terraform side: create once, then disown

```hcl
resource "aws_ecs_task_definition" "app" {
  family                   = "${var.project_name}-${var.environment_name}-api"
  requires_compatibilities  = ["FARGATE"]
  network_mode              = "awsvpc"
  cpu                        = var.task_cpu
  memory                     = var.task_memory
  execution_role_arn         = aws_iam_role.execution.arn
  task_role_arn              = aws_iam_role.task.arn

  # Bootstrap body only. The pipeline overwrites this on every release;
  # this container_definitions value is never read again after the first apply.
  container_definitions = jsonencode([{
    name  = "api"
    image = "${var.ecr_repository_url}:bootstrap"
    portMappings = [{ containerPort = 8080 }]
  }])

  lifecycle {
    ignore_changes = [container_definitions]
  }
}

resource "aws_ecs_service" "app" {
  name            = "api"
  cluster         = var.ecs_cluster_arn
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count

  # The pipeline calls update-service with a new task_definition ARN on every
  # release. Terraform must not fight that on the next apply.
  lifecycle {
    ignore_changes = [task_definition]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "api"
    container_port   = 8080
  }
}
```

**Both `ignore_changes` blocks are required, on two different resources, and
that is the detail most implementations get wrong:**

- `ignore_changes = [container_definitions]` on the task definition stops
  Terraform from reverting the pipeline's new revision back to `:bootstrap` on
  the next `terraform apply`.
- `ignore_changes = [task_definition]` on the service stops Terraform from
  reverting the running service back to the original task definition ARN.

Skip either one and the next infrequent `terraform apply` — someone bumping
`desired_count`, say — silently redeploys the bootstrap image to production.
This is the single most common way B breaks in practice.

Terraform still owns and applies normally: the cluster/service shell, the
target group and listener rule, the IAM roles, the log group, autoscaling
targets. Nothing here is exempt from the platform/app-stack split in
`PLAN.MD` — B changes who writes the task definition, not where the surrounding
resources live.

---

## 3. IAM: two roles, two purposes

- **Task role** (`aws_iam_role.task`) — what the running container assumes at
  runtime (S3, DynamoDB, Secrets Manager, whatever the app calls). Unaffected by
  B; scope it exactly as you would under C.
- **Execution role** (`aws_iam_role.execution`) — what ECS assumes to pull the
  image and inject secrets/log config at task start. Under B, the deploy
  pipeline additionally needs its own principal, separate from both:

```hcl
data "aws_iam_policy_document" "pipeline_deploy" {
  statement {
    sid = "RegisterAndDeployTaskDefinitions"
    actions = [
      "ecs:RegisterTaskDefinition",
      "ecs:DescribeTaskDefinition",
      "ecs:UpdateService",
      "ecs:DescribeServices",
    ]
    resources = ["*"] # RegisterTaskDefinition does not support resource scoping
  }

  statement {
    sid       = "PassTaskRoles"
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.execution.arn, aws_iam_role.task.arn]
    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }
}
```

`RegisterTaskDefinition` cannot be scoped to a specific family by resource ARN —
narrow the blast radius with a separate deploy role per service (or per
cluster) rather than relying on resource-level scoping that doesn't exist for
this action. The `iam:PassedToService` condition is what stops this role from
passing an unrelated, more-privileged role to some other service's tasks.

---

## 4. The release pipeline

```bash
# 1. Fetch the current task definition (for cpu/memory/roles/etc. — everything
#    except the fields this release changes).
TASK_DEF=$(aws ecs describe-task-definition --task-definition "$FAMILY" --query 'taskDefinition')

# 2. Render a new container definition with the new image digest.
NEW_CONTAINER_DEFS=$(echo "$TASK_DEF" | jq --arg IMAGE "$ECR_REPO_URL@$IMAGE_DIGEST" \
  '.containerDefinitions[0].image = $IMAGE')

# 3. Register a new revision. Strip fields the API rejects on re-registration
#    (revision, status, taskDefinitionArn, requiresAttributes, compatibilities,
#    registeredAt, registeredBy).
NEW_TASK_DEF_ARN=$(aws ecs register-task-definition \
  --family "$FAMILY" \
  --task-role-arn "$(echo "$TASK_DEF" | jq -r .taskRoleArn)" \
  --execution-role-arn "$(echo "$TASK_DEF" | jq -r .executionRoleArn)" \
  --network-mode "$(echo "$TASK_DEF" | jq -r .networkMode)" \
  --container-definitions "$NEW_CONTAINER_DEFS" \
  --cpu "$(echo "$TASK_DEF" | jq -r .cpu)" \
  --memory "$(echo "$TASK_DEF" | jq -r .memory)" \
  --requires-compatibilities FARGATE \
  --query 'taskDefinition.taskDefinitionArn' --output text)

# 4. Point the service at it and wait for stability.
aws ecs update-service --cluster "$CLUSTER" --service "$SERVICE" \
  --task-definition "$NEW_TASK_DEF_ARN" >/dev/null
aws ecs wait services-stable --cluster "$CLUSTER" --services "$SERVICE"
```

Prefer the maintained `aws-actions/amazon-ecs-deploy-task-definition` GitHub
Action over hand-rolling this — it already handles the field-stripping in step 3
correctly, which is easy to get subtly wrong (an extra field in the
`register-task-definition` call is a runtime rejection, not a type error you'd
catch earlier).

Rollback is: register-or-reuse the previous task definition ARN and
`update-service` again. There is no `terraform apply` involved in rollback
either — which is the point of B, and also why Terraform state stops being a
useful audit trail for "what's running now." Use CloudTrail or the pipeline's own
deploy log for that instead.

---

## 5. When B is the right call

- Multiple releases per day per service, where a 1–3 minute `plan`/`apply` is a
  felt bottleneck, not a hypothetical one.
- A platform team owns Terraform and infra changes go through a slower review
  path than app teams want for routine image bumps.
- The org already has mature ECS deploy tooling (CodeDeploy blue/green, the
  GitHub Action above) that expects to own the task definition.

## 6. When it's the wrong call

- Anything below the frequency in §5 — the 1–3 minute apply under Model C is
  cheaper than the operational surface B adds (a second IAM principal, a second
  deploy tool, a `terraform plan` that shows permanent drift on
  `container_definitions`/`task_definition` that every new engineer will ask
  about).
- Compliance or audit requirements where "what's deployed" must be answerable
  from Terraform state alone.
- Any team not already running the pipeline tooling in §4 — building it is real
  work, and it's the same work regardless of release frequency.

## 7. Migrating

**C → B:** create the pipeline and its IAM role first, deploy through it once
successfully in a non-production environment, confirm `update-service` and
rollback both work, *then* add both `ignore_changes` blocks in the same PR that
stops the app-stack pipeline from writing image tags into tfvars. Doing this in
two separate PRs leaves a window where both Terraform and the new pipeline can
write the task definition — whichever runs last wins, silently.

**B → C:** the reverse is a state operation, not a config edit. `terraform
import` the pipeline's current task definition revision into
`aws_ecs_task_definition.app`, drop both `ignore_changes` blocks, move the image
reference into a proper Terraform variable, and run a plan to confirm it shows
no changes before merging. If the plan shows a diff, the imported revision
doesn't match what Terraform would generate — resolve that before removing
`ignore_changes`, or the next apply redeploys unintentionally.

**Never run B and C simultaneously against the same service.** Whichever
control plane writes last wins the next time the other one runs, and neither
side will show a warning that it happened.
