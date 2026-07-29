# AWS Deploy/Destroy Scripts Pattern

The Terraform conventions in `SKILL.md` are applied through shell scripts, one
pair per stack (`deploy-<stack>.sh` / `destroy-<stack>.sh`), plus
`deploy.sh`/`destroy.sh` orchestrators and `build-<service>.sh` for container
images. The full script patterns live in the sibling **`deploy-scripts`** skill.
This file is the interface contract between them.

Read the `deploy-scripts` skill in full before writing or modifying scripts. If
it is unavailable, limit work to the Terraform side and preserve this contract.
Examples use `Terraform/`; resolve and preserve the repository's exact
case-sensitive Terraform directory name before constructing paths.

## What the scripts assume about your Terraform

- **One shared root exists per stack** at `Terraform/stacks/<root>/`.
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
- **ECR repositories normally live in an `ecr` stack** with immutable tags and
  `force_delete = false`. Service roots consume a repository URL/ARN through a
  data source or intentional published value; they do not use routine
  `-target`.
- **Image versions are explicit.** Follow
  [`docker-image-tagging.md`](docker-image-tagging.md). Image tag/digest
  variables have no convenience default.
- **Wrapper-consumed outputs stay stable:** `ecs_cluster_name`,
  `ecs_service_names` (always a list), `<service>_ecr_repository_url`, and
  `<service>_image_tag` or `<service>_image_digest`.
- **Managed-ENI guardrails and script diagnostics complement each other.**
  Drain ECS services, configure supported Lambda replacement security groups,
  and keep the wrapper's ENI diagnostic path.
- **Autoscaling ownership is explicit.** Use
  `ignore_changes = [desired_count]` only when autoscaling truly owns that
  attribute after initial creation.

## What the Terraform side assumes about the scripts

- **`ENV` is required for mutating workflows.** Never default silently to
  production.
- **Terraform configuration never branches on `CI`.** CI changes wrapper
  approval behavior, not resource logic.
- **Initialization uses `-reconfigure` with the selected backend.** State
  migration requires a separate explicit workflow.
- **Plans are saved and the exact saved plan is applied.** Plan files are
  transient, sensitive, gitignored, and removed on every exit path.
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
