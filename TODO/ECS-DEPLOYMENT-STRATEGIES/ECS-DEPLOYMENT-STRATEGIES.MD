# ECS: Zero-Disconnect Rollback and Progressive Delivery

**Status:** idea backlog, not implemented, not part of the `terraform-aws` skill
yet.

Gap identified while reviewing `resources/skills/terraform-aws/`:
`workload-deploy-patterns.md`'s ECS section documents a plain rolling
deployment plus `deployment_circuit_breaker`, and nothing about connection
draining, blue/green, or canary. This doc collects what a "ψαγμένο" (sophisticated)
ECS release/rollback story would need, so it can be turned into a real
reference section later without re-deriving the reasoning from scratch.

Read this if: you're about to write `ecs-deployment-strategies.md` (or extend
the ECS section of `workload-deploy-patterns.md`), or a specific service needs
one of these techniques now and you want the trade-offs already thought through.

---

## 1. Baseline gap: rollback drops in-flight connections

The current skill's ECS example has `deployment_circuit_breaker { rollback =
true }` but no `deregistration_delay` and no `stopTimeout`. Without both, a
rollback (automatic or manual) can kill tasks that still have live requests.

- **`deregistration_delay` on `aws_lb_target_group`** — ALB stops routing new
  requests to a deregistering target but keeps it registered until in-flight
  requests finish or the delay elapses (default 300s). This is what makes any
  ECS transition — forward or rollback — connection-safe.
- **`stopTimeout` on the container definition** — how long ECS waits after
  SIGTERM before SIGKILL. Must be ≥ how long the app needs to finish in-flight
  work after it stops accepting new connections. Currently undocumented in the
  skill's container definition example.
- **App-side requirement the skill doesn't currently call out**: the process
  must actually handle SIGTERM by stopping new-connection accept and draining
  existing ones — the Terraform settings are necessary but not sufficient
  without this.

**Action:** add both fields to the ECS example in `workload-deploy-patterns.md`
with the rationale above. This alone answers "rollback χωρίς disconnect" for
the rolling-deployment model — no new architecture needed, just two missing
settings.

---

## 2. CloudWatch-alarm-driven rollback (beyond circuit breaker)

`deployment_circuit_breaker` only reacts to ECS's own steady-state/health-check
signal. It won't catch "deployed fine, health checks pass, but error rate/
latency spiked" — that needs the `alarms` block:

```hcl
resource "aws_ecs_service" "api" {
  # ...
  alarms {
    enable   = true
    rollback = true
    alarm_names = [
      aws_cloudwatch_metric_alarm.api_5xx.alarm_name,
      aws_cloudwatch_metric_alarm.api_latency_p99.alarm_name,
    ]
  }
}
```

- Needs the referenced alarms to already exist and be in `OK` state before the
  deployment starts, or the deployment fails immediately.
- Complements, doesn't replace, the circuit breaker — keep both.
- **Open question:** which alarms should be the skill's *default* pair (5xx
  rate, p99 latency) vs. left to the service to define. Probably default to
  none required, document the pattern, let the service opt in.

---

## 3. Weighted listener rule canary (no new deploy tooling)

A lighter-weight canary than full blue/green: two target groups behind the
same listener rule, weighted `forward`:

```hcl
resource "aws_lb_listener_rule" "api" {
  # ...
  action {
    type = "forward"
    forward {
      target_group {
        arn    = aws_lb_target_group.api_stable.arn
        weight = 90
      }
      target_group {
        arn    = aws_lb_target_group.api_canary.arn
        weight = 10
      }
    }
  }
}
```

- Two `aws_ecs_service` resources (stable + canary), same task definition
  family, different revisions during a release.
- Rollback = set canary weight to 0 (or delete the canary service). Instant,
  no drain wait on the stable path since it never stopped serving.
- Manual weight/promotion steps unless scripted — this is the "cheap canary,"
  not the automated one. No automatic analysis of canary metrics; a human (or
  a script polling CloudWatch) decides to promote or roll back.
- **Trade-off vs. §4:** no CodeDeploy dependency, stays inside plain
  `aws_ecs_service` + ALB primitives the skill already uses — but all
  promotion/rollback logic has to be hand-rolled (script or CI step), where
  CodeDeploy gives you that machinery built-in.

---

## 4. CodeDeploy blue/green (the "real" answer)

```hcl
resource "aws_ecs_service" "api" {
  # ...
  deployment_controller {
    type = "CODE_DEPLOY"
  }
  # desired_count, task_definition still Terraform-owned; CodeDeploy drives
  # the actual traffic shift between the two target groups it creates/manages.
}

resource "aws_codedeploy_deployment_group" "api" {
  app_name               = aws_codedeploy_app.api.name
  deployment_group_name  = "api"
  service_role_arn       = aws_iam_role.codedeploy.arn
  deployment_config_name = "CodeDeployDefault.ECSLinear10PercentEvery1Minute"

  auto_rollback_configuration {
    enabled = true
    events  = ["DEPLOYMENT_FAILURE", "DEPLOYMENT_STOP_ON_ALARM"]
  }

  alarm_configuration {
    alarms  = [aws_cloudwatch_metric_alarm.api_5xx.alarm_name]
    enabled = true
  }

  ecs_service {
    cluster_name = local.ecs_cluster_name
    service_name = aws_ecs_service.api.name
  }

  load_balancer_info {
    target_group_pair_info {
      prod_traffic_route {
        listener_arns = [local.alb_https_listener_arn]
      }
      target_group {
        name = aws_lb_target_group.api_blue.name
      }
      target_group {
        name = aws_lb_target_group.api_green.name
      }
    }
  }
}
```

- Terraform's role shrinks to: create the service with the CodeDeploy
  controller, create both target groups, create the deployment group and its
  alarms/rollback config. **The actual release (registering the new task def
  revision and starting the shift) happens through the CodeDeploy API, not
  `terraform apply`** — same shape of split as the EKS/GitOps case already in
  `eks-gitops.md`, just with CodeDeploy instead of Argo/Flux as the reconciler.
- Rollback is instant and connection-safe by construction: traffic just
  points back at the target group that never stopped running, no drain wait
  needed on the rollback path itself (draining still applies to whichever
  target group is being torn down after a *successful* shift).
- Deployment configs give canary (`ECSCanary10Percent5Minutes`, etc.) or
  linear traffic shifting for free, plus alarm-triggered auto-rollback during
  the shift — this is the direct answer to the original "καμια ψαγμένη
  τεχνικη" question.
- **Cost of adopting this:** second IAM role (CodeDeploy service role), the
  release pipeline must call CodeDeploy's `create-deployment` instead of (or
  in addition to) `terraform apply`, and — same warning as `PLANB.MD` §7 for
  pipeline-owned task definitions — Terraform and the deploy pipeline must
  never both try to own the same field. Here specifically: don't let
  `terraform apply` fight over `task_definition` while a CodeDeploy shift is
  in progress.

---

## 5. Where this belongs in the skill

- Likely a new reference file, `ecs-deployment-strategies.md`, linked from the
  ECS section of `workload-deploy-patterns.md` the same way `eks-gitops.md` is
  linked from the EKS section.
- §1 (drain settings) is small enough to just fix inline in the existing ECS
  example — no new file needed for that part.
- §2–4 are progressively bigger commitments (an alarm, a second target group,
  a second control plane) and should probably be presented as a decision
  table like `PLANB.MD`'s §5/§6 ("when is plain rolling enough vs. when do you
  need blue/green"), not as a single recommended default — the skill's
  existing stance is "Terraform provisions, does not own release
  orchestration," and blue/green is the point where that stance has the
  sharpest teeth.

## 6. Open questions before writing the real reference

- Does this repo's actual ECS usage ever need canary-with-automated-analysis,
  or does "manual promote after watching a dashboard" (§3) cover every real
  case so far? Don't build §4 tooling nobody will operate.
- Should `alarms` (§2) become a required part of the skill's default ECS
  example, or stay opt-in? Leaning opt-in — mandatory alarms means the skill
  has to also prescribe *which* metrics, and that's service-specific.
- If a service adopts CodeDeploy blue/green, does its release pipeline already
  exist, or does this drag in the same "who owns the release pipeline" scoping
  question that `PLANB.MD` covers for pipeline-owned task definitions? Answer
  is probably "yes, cross-reference `PLANB.MD`" rather than duplicating that
  discussion here.
