# Validation, Static Analysis, and Tests

What the bundled checker covers, which static-analysis tools to standardize on,
how to author `terraform test` files, and how to review a real plan. `SKILL.md`
states the requirement to run these; this file is the detail.

## Contents

- [The Bundled Checker](#the-bundled-checker)
- [Static Analysis Tool Policy](#static-analysis-tool-policy)
- [Writing Tests](#writing-tests)
- [Reviewing a Real Plan](#reviewing-a-real-plan)

## The Bundled Checker

```sh
<skill-dir>/scripts/check.sh \
  --repo-root "$REPO_ROOT" \
  --terraform-dir "$TF_ROOT" \
  --platform darwin_arm64 \
  --platform linux_amd64
```

It performs, in order:

1. `terraform fmt` in check mode over the Terraform tree.
2. `terraform validate` for every stack, the bootstrap root, and every standalone
   module, in a temporary copy with backend access disabled, so validation never
   touches remote state or requires credentials.
3. A lockfile audit for each requested `-platform`, so a root missing a
   developer's or CI runner's platform hashes fails here rather than at `init`.
4. TFLint with the configured AWS ruleset.
5. Trivy, with findings failing the gate.

Missing TFLint or Trivy tools or configuration is a failure, not a skip, unless an
explicit skip flag is passed. It deliberately does **not** run `terraform test`,
because unmocked tests can create billable infrastructure.

Pass every platform any developer or runner actually uses. The audit is only as
good as the list it is given.

## Static Analysis Tool Policy

- **TFLint** is generic Terraform linting unless the AWS ruleset plugin is enabled
  and pinned to an exact version. Without that, do not describe or report it as
  AWS linting.
- **Trivy** is the default misconfiguration scanner here. Use **Checkov**
  alongside or instead of it only when the repository standardizes on Checkov;
  running both without triaging overlapping findings produces noise nobody reads.
- **Do not recommend tfsec for new setups.** Its scanning was folded into Trivy.
- Findings that are accepted risks belong in the tool's own ignore/config file
  with a reason, not in a commit message. An inline suppression with no
  justification is indistinguishable from an oversight at review time.

## Writing Tests

Run `terraform -chdir=<configuration> test` for each module or stack that owns
tests; Terraform discovers `tests/*.tftest.hcl` inside that configuration.

- Native `terraform test` requires Terraform 1.6.0; `mock_provider` requires
  1.7.0.
- Mocking uses real provider schemas but synthetic computed values, so an assertion
  on the *shape* of a generated ARN or ID needs a `.tfmock.hcl` file or an
  explicit default. Do not assert on values a mock invented.
- Put **module** tests beside the module: input validation, conditional resource
  creation, naming, and the output contract other stacks depend on.
- Test values transformed for an external API, especially tags assembled from
  free text or lists. Assert the rendered value and include a failing case for
  invalid characters or lengths; provider schemas do not necessarily catch the
  downstream service's constraints during `terraform plan`.
- Put **stack** tests beside the stack only for root composition, outputs,
  policies, or environment-independent invariants. Do not re-test module behavior
  in every stack that calls the module.
- An unmocked test creates real infrastructure. Run those only in a dedicated
  disposable account with cleanup monitoring, never against an account that holds
  anything else.

Useful assertions for an application stack: that a required artifact input has no
default and fails validation when malformed, that a shared-namespace input such as
a listener rule priority is present and in range, and that the published output
names have not changed.

## Reviewing a Real Plan

1. Initialize the target environment's backend with the isolated `TF_DATA_DIR`
   and `-reconfigure`.
2. `terraform plan -input=false -lock-timeout=5m -var-file=... -out=<plan>`.
3. Read the plan, not just the summary line. Every replacement and every deletion
   needs a reason you can state before the apply. `terraform show -json <plan>`
   piped through `jq` is the reliable way to find them in a large plan:

```sh
terraform show -json "$PLAN_FILE" \
  | jq -r '.resource_changes[]
      | select(.change.actions | index("delete"))
      | "\(.change.actions | join(",")) \(.address)"'
```

4. Review policy or check-block results in the same JSON output.
5. Apply that exact saved plan, only after authorization. Never re-plan implicitly
   at apply time.

`terraform plan -detailed-exitcode` returns 0 for no changes, 2 for changes, and 1
for an error — the right check for drift detection and for confirming a state
migration left both roots quiet.

Plan files contain resolved values, including ones marked `sensitive`. Treat them
as secrets: gitignored, removed on every exit path, and never uploaded to an
artifact store without access control.
