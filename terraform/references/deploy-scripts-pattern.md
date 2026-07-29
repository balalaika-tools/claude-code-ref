# Deploy/Destroy Scripts Pattern

The Terraform conventions in `SKILL.md` are applied through a set of shell scripts, one pair per stack (`deploy-<stack>.sh` / `destroy-<stack>.sh`), plus `deploy.sh`/`destroy.sh` orchestrators and `build-<service>.sh` for stacks with container images. The full script bodies, structure, and rationale live in the **`deploy-scripts`** skill — this file is the interface contract between the two, so a Terraform change doesn't quietly break the wrapper scripts (or vice versa) without either skill noticing.

Read the `deploy-scripts` skill in full when writing or modifying any script in `scripts/`. Read this file when writing Terraform that a script will call, to know what it can assume.

## What the scripts assume about your Terraform

- **`{env}.tfvars` exists per environment stack** and is passed as `-var-file="$ENV.tfvars"`. If a stack needs additional vars (build artifacts, image tags), the script adds a second `-var-file`, it never edits the environment's own tfvars file.
- **`ENV` selects the environment directory**: `Terraform/environments/$ENV/<stack>/` and `Terraform/backend-config/$ENV/<stack>.backend.hcl`. A new stack must exist under all three environment directories the scripts expect (`dev`, `staging`, `prod`) before the orchestrator can deploy it everywhere.
- **The state bucket has `prevent_destroy = true`.** `destroy.sh`'s closing banner states this as fact and never attempts to remove it. If a stack's state bucket doesn't have this, the destroy orchestrator's safety message is a lie.
- **ECR repos live in their own `ecr` stack**, not inside the service stack that consumes them (see `SKILL.md`'s Module Design — "one module, one job" applied to stacks, not just modules). The scripts never use `-target` to reach into a combined stack; if a stack couples ECR and ECS/Lambda, split it before wiring up `build-<service>.sh`.
- **Image tags are the git SHA**, matching [`docker-image-tagging.md`](docker-image-tagging.md). The `image_tag` variable must have no default — the build script always supplies one explicitly. Don't add a default "for convenience"; it defeats the point of forcing CI to be explicit about what's deployed.
- **Outputs the scripts read must stay stable** — `ecs_cluster_name`, `ecs_service_names` (a JSON list, even for a single service — the drain-before-destroy loop depends on the list shape), `<service>_ecr_repository_url`, `<service>_image_tag`. Renaming one without updating the script that reads it fails at destroy or deploy time, not at `terraform plan` time — nothing type-checks a shell script against your outputs.
- **SG/ENI guardrails reduce, not eliminate, the manual diagnostic path.** `timeouts { delete = "30m" }` and `replace_security_groups_on_destroy` (see SKILL.md's ENI section) make a stuck destroy less likely; the scripts' ENI diagnostic pattern is what runs when it still happens. Both need to exist — the Terraform side isn't a substitute for the script-side fallback.
- **`lifecycle` blocks are load-bearing for the destroy workflow**, not optional cleanup. `ignore_changes = [desired_count]` on an autoscaled ECS service keeps `terraform plan` quiet between deploys; without it, every `deploy-<stack>.sh` run shows a diff the orchestrator's plan-review step has to route past.

## What the Terraform side assumes about the scripts

- **CI is signaled by `CI=true`, nothing else.** Don't gate any Terraform-adjacent behavior (module logic, data sources) on a different CI-detection mechanism — the scripts are the single source of truth for "are we in CI."
- **Bootstrap-time existence checks (S3 state bucket) use the imperative `terraform import` CLI**, not an `import` block — this is the one place the general "prefer declarative refactoring blocks" rule in `SKILL.md` doesn't apply, because the script needs a runtime decision (`head-bucket` exists or not) a static block can't express.
- **Plan files (`tfplan`) are transient and gitignored** — a script cleans them up via `trap ... EXIT` on every exit path, and the repo's `.gitignore` excludes `tfplan`/`*.tfplan` the same way it excludes `terraform.tfstate*`. A plan file carries resolved variable values; treat it with the same care as state.
