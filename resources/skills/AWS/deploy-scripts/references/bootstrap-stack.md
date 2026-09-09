# The Bootstrap State-Bucket Stack

The state-bucket stack is the one stack that cannot follow the standard workflow
in `SKILL.md`, because the remote backend it would use is the thing it creates.
Name it `create-<stack>.sh`, not `deploy-<stack>.sh`, so the exception is visible
in the filename.

Set this up once per project. Nothing else in `scripts/` should look like it.

## How it differs

- Uses a **local backend** — the remote state bucket doesn't exist yet.
- **Lives outside `stacks/`.** Its root is `Terraform/bootstrap/state/`, per
  `terraform-aws/SKILL.md`'s repository layout — not
  `Terraform/stacks/<stack>/`. The generic `TF_DIR="$REPO_ROOT/Terraform/stacks/$ROOT_STACK"`
  template in `SKILL.md`'s Path Resolution section does not apply to
  `create-<stack>.sh`; point it at `bootstrap/state` explicitly instead.
- May be shared across environments in a dedicated state account, with each role
  restricted to `<env>/<stack>/...`; projects that require account-level
  isolation may bootstrap separate buckets instead.
- Uses `import_if_exists` before apply to re-import buckets idempotently.
- Skips the plan file and interactive gate; in CI uses `-auto-approve`, locally
  uses Terraform's own default interactive prompt.
- Destroy uses a stricter confirmation token (e.g. `DESTROY-DATA`) for the state
  bucket.
- The state bucket carries `prevent_destroy = true`; removing it requires
  editing the source.

Because the backend is local, `TF_DATA_DIR` isolation is not what keeps
environments apart here — the state file's own path is. Gitignore that local
state and back it up through an approved encrypted, access-controlled mechanism,
exactly as `terraform-aws/SKILL.md`'s Remote State Backend section requires —
do not commit it, even as an exception for this one stack. Never let two
environments share one local state file.

## Idempotent Import

If the bootstrap wrapper collects optional Terraform arguments in an array,
expand that array with the Bash-3.2-safe form from `SKILL.md`:

```bash
terraform apply ${EXTRA_VARS[@]+"${EXTRA_VARS[@]}"}
```

This matters for the normal no-role-override path, where `EXTRA_VARS=()` is
legitimately empty and `set -u` would otherwise abort before Terraform runs.

```bash
import_if_exists() {
  local tf_addr="$1" resource_id="$2"
  if terraform state show "$tf_addr" &>/dev/null 2>&1; then
    print_info "Already in state: $tf_addr — skipping import"
    return
  fi
  if aws s3api head-bucket --bucket "$resource_id" 2>/dev/null; then
    print_info "Importing existing bucket '$resource_id' → $tf_addr"
    terraform import -var-file="$VAR_FILE" "$tf_addr" "$resource_id"
  fi
}
```

`$VAR_FILE` is the same `${ENV}`-resolved, absolute path every other script uses
— never hardcode a specific environment's file name here. A bootstrap script
that only ever imports `prod`'s bucket regardless of `$ENV` will happily import
the wrong environment's bucket into the wrong environment's local state.

The two guards run in this order for a reason: the state check is local and free,
and it short-circuits before the script spends an API call on a bucket Terraform
already owns. `head-bucket` returning non-zero also covers "exists but not
accessible to these credentials", so a permissions problem falls through to
`apply` and fails there with a clearer message than a failed import would give.

## Rendering Backend Configurations

When Terraform outputs a map of stack names to multi-line partial backend HCL,
serialize each map entry as exactly one line before feeding it to `read`. A raw
tab-separated `"\(.key)\t\(.value)"` is incorrect: `jq -r` emits the value's
newlines, so the shell treats every later HCL line as another record and may use
content such as `key = "..."` as a filename.

```bash
terraform output -json "$OUTPUT_NAME" \
  | jq -r 'to_entries[] | "\(.key)\t\(.value | gsub("\n"; "\\n"))"' \
  | while IFS=$'\t' read -r stack body; do
      printf '%b' "$body" > "$BACKEND_DIR/$stack.backend.hcl"
    done
```

The `gsub` converts embedded newlines to literal `\n` sequences, keeping each
entry on one transport line; `printf '%b'` restores the original HCL. Add a
behavioral test with at least two entries and multi-line values. Verify the exact
filenames and complete file contents, not only the script's exit status.

## Why the imperative CLI is correct here

The `terraform-aws` skill's general rule — prefer declarative `import` blocks
over the imperative `terraform import` CLI — assumes you already know the
resource is there to import. This bootstrap script doesn't: it has to check
`head-bucket` against real AWS state *at runtime* to decide whether an import is
even needed, which a static `import` block can't express. That's the one case
where the CLI form is correct, not a violation of the rule.

Keep the exception this narrow. Every other known import in the repository stays
declarative.
