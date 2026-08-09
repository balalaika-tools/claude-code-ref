---
name: split-repo-app-releases
description: >-
  Conventions for an application repository that owns service source code and its
  release pipeline while Terraform lives in a separate infrastructure repository.
  Use when adding or reviewing a service's build-and-publish workflow, its test and
  lint gates, its publish-only AWS role, or the handoff that hands an immutable
  artifact version to the infrastructure repository — including questions like
  "add a release workflow for this service", "how does this repo deploy", "wire up
  OIDC for the build", or "how do we ship a Lambda when Terraform is elsewhere".
  Applies to repositories that hold application source and no Terraform tree. For
  the Terraform and deploy-script side, and for a monorepo where both live
  together, use the sibling `terraform-aws` and `deploy-scripts` skills instead.
---
# Application Repository Releases

This skill covers the application side of a split repository layout: a repository
that owns `apps/<service>/` or `lambdas/<service>/`, their tests, and a pipeline
whose job ends at **"an immutable artifact is published and its version has been
handed to the infrastructure repository."** Nothing here applies `terraform`, and
this repository holds no credentials that could.

The infrastructure side — Terraform, `deploy-app-<service>.sh`, the applying role
— belongs to the sibling `terraform-aws` and `deploy-scripts` skills. The handoff
contract that joins the two is one file:
`deploy-scripts/references/split-repo-releases.md`. Read it before wiring a
pipeline; it defines the artifact file, both trust policies, and the promotion and
rollback paths. If that skill is unavailable, follow [The Handoff
Contract](#the-handoff-contract) below and do not invent a different mechanism.

## Confirm You Are In The Right Repository

Check before applying anything here:

- Application source present, **no** `Terraform/` → this skill.
- `Terraform/` **and** application source → monorepo. Use `deploy-scripts`; the
  build script is called inline by the deploy script and there is no handoff.
- `Terraform/` with `stacks/app-*` and no application source → the infrastructure
  repository. Use `deploy-scripts` and `terraform-aws`.

If application source and `Terraform/` are both present but the team says they are
splitting, the migration itself is a `deploy-scripts` task — the artifact handoff
has to exist before the source moves.

## What This Repository Owns

| Owns                                                                       | Does not own                              |
| -------------------------------------------------------------------------- | ----------------------------------------- |
| `apps/<service>/`, `lambdas/<service>/` — source, dependencies, tests | any`.tf` file                           |
| `scripts/build-<service>.sh` — builds and publishes the artifact        | `deploy-*.sh`, `destroy-*.sh`         |
| `scripts/open-release-pr.sh` — hands the version over                   | anything that runs`terraform`           |
| Unit, integration, lint, and type gates for the service                    | `terraform test`, `tflint`, `trivy` |
| A publish-only AWS role per service per environment                        | the applying role                         |

Two rules follow from that table and are the whole point of the split:

- **This repository's pipeline cannot deploy.** Its role publishes an artifact and
  nothing else — no Terraform state access, no `lambda:UpdateFunctionCode`, no
  `ecs:UpdateService`, no `iam:PassRole`. A compromised application pipeline can
  publish an artifact nobody approved; it cannot ship one.
- **The build travels with the source.** The build script belongs here, because it
  reads source and stamps the artifact with *this* repository's commit. A build
  script left in the infrastructure repository tags artifacts with the
  infrastructure commit, and every later "which commit is running?" answer is
  wrong.

## Repository Layout

```text
<repo-root>/
├── apps/<service>/            # container services: Dockerfile + source
├── lambdas/<service>/         # Lambda functions
│   ├── handler.py             # thin AWS entry point
│   ├── pyproject.toml
│   ├── uv.lock                # committed; the only dependency lock
│   ├── src/<package>/         # implementation
│   └── tests/
├── scripts/
│   ├── build-<service>.sh
│   └── open-release-pr.sh
├── build/                     # generated, gitignored
└── .github/workflows/
    ├── ci.yml                 # tests on every pull request
    └── release-<service>.yml  # one per service
```

One repository holding several services is preferred over one repository per
service: it gets the ownership boundary without N copies of near-identical release
CI. Keep each service independently releasable inside it — its own `paths:` filter,
its own artifact, its own role, its own lockfile.

For Python Lambda layout, the `handler.py`/`src/` boundary, and uv dependency
policy, follow `terraform-aws`'s `references/python-lambda.md`. It applies verbatim
here; only the absent `Terraform/` differs.

## Build Scripts

Do not write a new build script pattern. `deploy-scripts`'
`references/build-scripts.md` holds the Lambda ZIP/uv and Docker/ECR listings and
`references/ami-builds.md` holds the AMI path; both apply unchanged, because
`REPO_ROOT` resolved from `${BASH_SOURCE[0]}` is already this repository's root.
Duplicating those listings here would give one convention two copies that drift.

Three things differ in this repository, and only these three:

- **No `terraform output` fallback.** There is no Terraform tree, no backend
  configuration, and no state access. Pass the ECR repository URL or artifact
  bucket in as an argument or environment variable, sourced from a repository
  variable or a platform-published SSM parameter the publish role may read.
- **The artifact tfvars body is an intermediate**, not the final handoff. The build
  writes it under `build/<service>/`; `open-release-pr.sh` reads it and publishes
  it into the infrastructure repository.
- **`ENV` names the target environment for the artifact**, not a Terraform
  workspace. It still must be explicit and must never default to production.

Everything else holds: version explicitly, never `latest` or a branch name, make
the artifact immutable, and write the tfvars body on every exit path including the
"already published, nothing to do" short-circuit.

## The Handoff Contract

The pipeline's last step publishes the artifact version as a **committed file in
the infrastructure repository**, via pull request:

```text
Terraform/environments/{env}/{stack}.artifacts.tfvars
```

with a provenance header naming this repository, the source commit, and the
workflow run, followed by the artifact coordinates the build produced. That makes
every deploy a reviewable diff, makes the infrastructure repository's `git log` the
deploy history, and makes rollback a `git revert` against an artifact that is still
in the registry.

Full listing of `open-release-pr.sh`, the workflow that calls it, and the direct
dispatch alternative: `deploy-scripts/references/split-repo-releases.md`.

Four failure modes to get right, in rough order of how often they bite:

- **Mint a GitHub App installation token; never use `secrets.GITHUB_TOKEN`.** The
  default token cannot reach another repository, and a pull request opened by an
  Actions token does not trigger `on: pull_request` — so the infrastructure
  repository's plan workflow would never run and the release would merge unplanned.
  Prefer an App scoped to that one repository with `contents: write` and
  `pull-requests: write` over a personal access token, which carries a human's full
  access and dies with their account.
- **Exit 0 when the version has not changed.** Re-running a release for an
  already-published artifact must be a clean no-op, not an empty pull request.
- **Publish before handing over, always in that order.** A merged version pointing
  at an artifact that does not exist turns a deploy into a plan-time or runtime
  failure in someone else's repository.
- **One branch per source commit and environment.** Concurrent releases for
  different environments must not contend for one branch.

## Test And Lint Gates

This repository owns the gates that were previously mixed into a monorepo's CI.
Run them on pull request, and make the release depend on them:

- Unit and integration tests for the service, at the version being released.
- `uv lock --check` — a lockfile that has drifted from `pyproject.toml` fails
  fast here. The build script runs the same check again immediately before
  packaging (see `deploy-scripts/references/build-scripts.md`); running it in
  both places is deliberate defense in depth, not a sign one of them is
  redundant — the test job gives quick feedback on a pull request, and the
  build's own check is what actually protects a build invoked outside this
  pipeline.
- Lint and type checks per the repository's existing tooling.
- `shellcheck scripts/*.sh` and `chmod +x` on new scripts, exactly as
  `deploy-scripts` requires — a non-executable build script fails with a confusing
  permission error.

Gate the release job on the test job with `needs:`. In a monorepo the same job did
build and apply, so a test failure blocked the deploy implicitly; here the two are
separate jobs and the dependency has to be declared.

## What Belongs In A Contract, Not A Guess

This repository knows less about the deployment than the monorepo did, and that is
fine as long as the unknowns are passed in explicitly rather than inferred:

| Needed                                      | Where it comes from                                                                         |
| ------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Artifact bucket or ECR repository URL       | repository/environment variable, or a platform SSM parameter the publish role may read      |
| Publish role ARN                            | repository variable, per environment                                                        |
| Infrastructure repository and stack name    | literals in this service's workflow and`open-release-pr.sh`                               |
| Target environment                          | an explicit`workflow_dispatch` input, or the literal `dev` for merge-triggered releases |
| Runtime configuration, secrets, memory, IAM | **none of this repository's business** — it belongs to the app stack's Terraform     |

The last row matters most. A service that needs a new environment variable, a new
secret, or more memory needs a change in the infrastructure repository, not a
workaround here. Land the backward-compatible infrastructure change first, then
release the code that depends on it — the split removed the atomic commit, so the
ordering is now yours to get right.

## Adding A Service

1. Add source under `apps/<service>/` or `lambdas/<service>/` with its own tests
   and, for Python, its own `pyproject.toml` and `uv.lock`.
2. Copy the nearest `build-<service>.sh` and update the source directory, artifact
   name, and artifact destination. Follow
   `deploy-scripts/references/build-scripts.md` for the body.
3. Add `release-<service>.yml`: a `paths:` filter for that service, a test job, and
   a publish job that builds, publishes, then opens the release pull request.
4. Request the two AWS resources this needs from the infrastructure repository —
   the publish-only role for this service per environment, and the artifact prefix
   or ECR repository. Both are platform-tier Terraform changes there, not here.
5. Confirm the corresponding app stack exists in the infrastructure repository with
   its artifact variables declared and no default. Until it does, a merged release
   pull request has nothing to apply.
6. `chmod +x` and `shellcheck` the new scripts.
