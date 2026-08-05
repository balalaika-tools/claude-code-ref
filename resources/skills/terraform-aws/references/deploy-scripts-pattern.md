# AWS Deploy/Destroy Scripts Pattern

The Terraform conventions in `SKILL.md` are applied through shell scripts, one
pair per stack (`deploy-<stack>.sh` / `destroy-<stack>.sh`), plus
`deploy.sh`/`destroy.sh` orchestrators and `build-<service>.sh` for artifacts.
The full script patterns live in the sibling **`deploy-scripts`** skill. This
file is the interface contract between them.

Consult the `deploy-scripts` skill — its `SKILL.md` plus the references it points
at for the parts you are touching — before writing or modifying scripts. If it is
unavailable, limit work to the Terraform side and preserve this contract.
Examples use `Terraform/`; resolve and preserve the repository's exact
case-sensitive Terraform directory name before constructing paths.

This contract holds whether the scripts and the application source share a
repository with `Terraform/` or the application code lives in its own repository.
The split changes only where the build runs and how the artifact version arrives;
every assumption below is unchanged by it.

## Tiers and workflows

- **Stacks are tiered.** `stacks/platform-<name>/` changes weekly to monthly;
  `stacks/app-<service>/` changes per release. Script names carry the tier:
  `deploy-platform-<name>.sh`, `deploy-app-<service>.sh`, and a
  `deploy-platform.sh` orchestrator for the platform tier.
- **Two CI workflows, not one.** Plan on pull request, apply on merge or manual
  dispatch behind environment protection. `CI=true` remains how a script behaves
  unattended, but it is no longer the approval gate — see
  [`platform-application-split.md`](platform-application-split.md).
- **A `--plan-only` invocation exists and must stay side-effect free.** The
  pull-request workflow runs it with a read-only role, so every root must plan
  without writing state. A `--detailed-exitcode` variant propagates Terraform's
  0/2/1 exit codes for drift detection.
- **`deploy.sh` is day-one bring-up and disaster recovery**, not the release
  path. An application release applies exactly one app stack.
- **App stacks are unordered siblings.** The stack list holds platform stacks in
  dependency order followed by app stacks in any order.

## What the scripts assume about your Terraform

- **One shared root exists per stack** at `Terraform/stacks/<root>/`, exactly one
  directory level deep.
- **Environment values exist separately** at
  `Terraform/environments/$ENV/<logical-stack>.tfvars`.
- **Partial backend configuration exists** at
  `Terraform/backend-config/$ENV/<logical-stack>.backend.hcl`.
- **`TF_DATA_DIR` is unique per environment, logical stack, and root stack.**
  Scripts must not reuse local metadata when switching environments or root
  implementations.
- **The root defines `aws_account_id` and the provider enforces
  `allowed_account_ids`.**
- **Only supported environments need files.** Do not assume every repository
  deploys exactly `dev`, `staging`, and `prod`.
- **Topology mappings are explicit.** A logical `database` stack may select
  `database-rds` in staging and `database-aurora` in production. Each root must
  use a distinct backend key and maintain a compatible consumer contract. Each
  standalone deploy/destroy wrapper derives the root from a closed `case` on
  `ENV`; do not accept an unrestricted root override.
- **ECR repositories live in a platform-tier stack** (`platform-ecr`) with
  immutable tags and `force_delete = false`. App roots consume a repository
  URL/ARN through a data source or intentional published value; they do not use
  routine `-target`.
- **Every artifact version is explicit, with no convenience default.** Container
  images follow [`docker-image-tagging.md`](docker-image-tagging.md); the same
  rule covers `<service>_ami_id` for EC2/ASG releases and
  `<service>_lambda_s3_key`, `<service>_lambda_s3_object_version`, and
  `<service>_lambda_source_code_hash` for Lambda
  zips. Build scripts hand these over in a generated artifact tfvars file that
  must exist on every exit path, including the already-published short-circuit.
- **An artifact version may originate in another repository, and is still required
  with no default.** Under a split application/infrastructure layout the value
  arrives as a committed `environments/{env}/{stack}.artifacts.tfvars`, written by
  the application repository's release and passed as the same second `-var-file`.
  Keep it strictly separate from the hand-edited `{stack}.tfvars`. The Terraform
  side is identical in both layouts: declare the variables, validate them, give
  them no default. The wrapper resolves where the file comes from.
- **A destroy plan must satisfy the artifact variables too.** They have no default,
  so `terraform plan -destroy -input=false` fails without them. Do not add a
  default to make destroy convenient.
- **Python Lambda builds use uv.** Source lives at `lambdas/<function>/` at the
  root of the repository that owns the source, outside the Terraform directory.
  `pyproject.toml` plus committed `uv.lock` are the dependency source of truth;
  any exported requirements file is generated only under the ignored build
  directory. Build for the configured runtime and architecture, and never run uv
  from Terraform. Full policy:
  [`python-lambda.md`](python-lambda.md).
- **Wrapper-consumed outputs stay stable** and belong to the app stack that owns
  the workload: `ecs_cluster_name`, `ecs_service_names` (always a list),
  `<service>_ecr_repository_url`, and `<service>_image_tag` or
  `<service>_image_digest`. A platform stack publishes its contract to SSM
  instead; a script that needs a platform value reads the parameter, not the
  platform state.
- **Managed-ENI guardrails and script diagnostics complement each other.**
  Drain ECS services, configure supported Lambda replacement security groups,
  and keep the wrapper's ENI diagnostic path. Both belong to the app tier.
- **Autoscaling ownership is explicit.** Use `ignore_changes = [desired_count]`
  only when autoscaling truly owns that attribute after initial creation. Never
  add `ignore_changes = [task_definition]` to a stack this skill generates.

## What the Terraform side assumes about the scripts

- **`ENV` is required for mutating workflows.** Never default silently to
  production.
- **Terraform configuration never branches on `CI`.** CI changes wrapper
  approval behavior, not resource logic.
- **Initialization uses `-reconfigure` with the selected backend.** State
  migration requires a separate explicit workflow.
- **Plans are saved and the exact saved plan is applied.** Plan files are
  transient, sensitive, gitignored, and removed on every exit path. A pull-request
  plan job that hands its plan to a protected apply job must treat that artifact
  as sensitive data with restricted access.
- **A missing platform contract is a hard failure.** App-stack plans resolve
  platform SSM parameters at plan time. When one is absent, report which platform
  stack has not been applied for which environment; never fall back to a default.
- **Bootstrap-time conditional imports may use the imperative CLI** when the
  script must first discover whether the state bucket exists. Other known
  imports remain declarative.
- **`bootstrap/state/` is the local-backend exception.** Its `create-*` wrapper
  does not use the standard remote-backend `-reconfigure` path and does not
  automatically migrate state into the bucket it creates. Gitignore the local
  state, serialize bootstrap operations, and durably back it up through an
  approved encrypted, access-controlled mechanism. Any later migration to an
  independently available backend is a separate reviewed operation.
- **Account and environment identity are shown before plan/apply.** The AWS
  provider's `allowed_account_ids` remains the authoritative guard.
