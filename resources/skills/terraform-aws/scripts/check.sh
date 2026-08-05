#!/usr/bin/env bash
# Run non-mutating Terraform formatting, validation, lint, and security checks.
#
# Terraform initialization and provider-lock auditing operate on a temporary
# copy. The source tree is read only for every check.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  check.sh [options]

Options:
  --repo-root DIR         Repository root. Defaults to the current Git root,
                          or the current directory outside a Git repository.
  --terraform-dir DIR     Terraform directory. Relative paths are resolved from
                          the repository root. By default, discover exactly one
                          top-level directory named "terraform", ignoring case.
  --tflint-config FILE    TFLint config. Relative paths are resolved from the
                          repository root. Defaults to .tflint.hcl under the
                          Terraform directory, then the repository root.
  --platform OS_ARCH      Audit every root lockfile for this execution platform.
                          Repeat for multiple platforms, such as darwin_arm64
                          and linux_amd64. No cross-platform audit runs when this
                          option is omitted.
  --skip-tflint           Explicitly skip TFLint and its AWS ruleset check.
  --skip-trivy            Explicitly skip the Trivy Terraform configuration scan.
  -h, --help              Show this help.

The default run checks every Terraform/stacks/* root, Terraform/bootstrap/state,
and every reusable Terraform/modules/* module. It never runs terraform plan,
apply, destroy, state commands, or terraform test. It refuses symbolic links
inside the Terraform tree so temporary-copy writes cannot escape to source.
EOF
}

print_info() {
  printf '[INFO] %s\n' "$1"
}

print_success() {
  printf '[PASS] %s\n' "$1"
}

print_warning() {
  printf '[WARN] %s\n' "$1" >&2
}

print_error() {
  printf '[FAIL] %s\n' "$1" >&2
}

die() {
  print_error "$1"
  exit 2
}

require_option_value() {
  local option="$1"
  local count="$2"

  if [[ "$count" -lt 2 ]]; then
    die "$option requires a value."
  fi
}

resolve_directory() {
  local path="$1"
  local base="$2"

  case "$path" in
    /*) ;;
    *) path="$base/$path" ;;
  esac

  [[ -d "$path" ]] || return 1
  (cd "$path" && pwd -P)
}

resolve_file() {
  local path="$1"
  local base="$2"
  local directory
  local filename

  case "$path" in
    /*) ;;
    *) path="$base/$path" ;;
  esac

  [[ -f "$path" ]] || return 1
  directory="$(dirname "$path")"
  filename="$(basename "$path")"
  printf '%s/%s\n' "$(cd "$directory" && pwd -P)" "$filename"
}

has_terraform_configuration() {
  local directory="$1"
  local candidate

  for candidate in "$directory"/*.tf "$directory"/*.tf.json; do
    if [[ -f "$candidate" ]]; then
      return 0
    fi
  done
  return 1
}

append_platform() {
  local candidate="$1"
  local existing

  if [[ ! "$candidate" =~ ^[a-z0-9]+_[a-z0-9]+$ ]]; then
    die "Invalid platform '$candidate'; expected OS_ARCH, for example linux_amd64."
  fi

  if [[ "${#PLATFORMS[@]}" -gt 0 ]]; then
    for existing in "${PLATFORMS[@]}"; do
      if [[ "$existing" == "$candidate" ]]; then
        return 0
      fi
    done
  fi
  PLATFORMS[${#PLATFORMS[@]}]="$candidate"
}

REPO_ROOT_INPUT=""
TERRAFORM_DIR_INPUT=""
TFLINT_CONFIG_INPUT=""
SKIP_TFLINT=false
SKIP_TRIVY=false
PLATFORMS=()

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --repo-root)
      require_option_value "$1" "$#"
      REPO_ROOT_INPUT="$2"
      shift 2
      ;;
    --repo-root=*)
      REPO_ROOT_INPUT="${1#*=}"
      [[ -n "$REPO_ROOT_INPUT" ]] || die "--repo-root requires a value."
      shift
      ;;
    --terraform-dir)
      require_option_value "$1" "$#"
      TERRAFORM_DIR_INPUT="$2"
      shift 2
      ;;
    --terraform-dir=*)
      TERRAFORM_DIR_INPUT="${1#*=}"
      [[ -n "$TERRAFORM_DIR_INPUT" ]] || die "--terraform-dir requires a value."
      shift
      ;;
    --tflint-config)
      require_option_value "$1" "$#"
      TFLINT_CONFIG_INPUT="$2"
      shift 2
      ;;
    --tflint-config=*)
      TFLINT_CONFIG_INPUT="${1#*=}"
      [[ -n "$TFLINT_CONFIG_INPUT" ]] || die "--tflint-config requires a value."
      shift
      ;;
    --platform)
      require_option_value "$1" "$#"
      append_platform "$2"
      shift 2
      ;;
    --platform=*)
      append_platform "${1#*=}"
      shift
      ;;
    --skip-tflint)
      SKIP_TFLINT=true
      shift
      ;;
    --skip-trivy)
      SKIP_TRIVY=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown option: $1. Run with --help for usage."
      ;;
  esac
done

CALLER_DIR="$(pwd -P)"

if [[ -n "$REPO_ROOT_INPUT" ]]; then
  if ! REPO_ROOT="$(resolve_directory "$REPO_ROOT_INPUT" "$CALLER_DIR")"; then
    die "Repository root does not exist: $REPO_ROOT_INPUT"
  fi
elif command -v git >/dev/null 2>&1 &&
    GIT_ROOT="$(git -C "$CALLER_DIR" rev-parse --show-toplevel 2>/dev/null)"; then
  REPO_ROOT="$(resolve_directory "$GIT_ROOT" "$CALLER_DIR")"
else
  REPO_ROOT="$CALLER_DIR"
fi

if [[ -n "$TERRAFORM_DIR_INPUT" ]]; then
  if ! TF_ROOT="$(resolve_directory "$TERRAFORM_DIR_INPUT" "$REPO_ROOT")"; then
    die "Terraform directory does not exist: $TERRAFORM_DIR_INPUT"
  fi
else
  TERRAFORM_CANDIDATES=()
  for candidate in "$REPO_ROOT"/*; do
    [[ -d "$candidate" ]] || continue
    candidate_name="$(basename "$candidate")"
    case "$candidate_name" in
      [Tt][Ee][Rr][Rr][Aa][Ff][Oo][Rr][Mm])
        TERRAFORM_CANDIDATES[${#TERRAFORM_CANDIDATES[@]}]="$candidate"
        ;;
    esac
  done

  case "${#TERRAFORM_CANDIDATES[@]}" in
    0)
      die "No top-level Terraform directory found under $REPO_ROOT; pass --terraform-dir."
      ;;
    1)
      TF_ROOT="$(resolve_directory "${TERRAFORM_CANDIDATES[0]}" "$REPO_ROOT")"
      ;;
    *)
      die "Multiple case-insensitive Terraform directories found under $REPO_ROOT; pass --terraform-dir."
      ;;
  esac
fi

TFLINT_CONFIG=""
if [[ "$SKIP_TFLINT" == false ]]; then
  if [[ -n "$TFLINT_CONFIG_INPUT" ]]; then
    if ! TFLINT_CONFIG="$(resolve_file "$TFLINT_CONFIG_INPUT" "$REPO_ROOT")"; then
      die "TFLint config does not exist: $TFLINT_CONFIG_INPUT"
    fi
  elif [[ -f "$TF_ROOT/.tflint.hcl" ]]; then
    TFLINT_CONFIG="$(resolve_file "$TF_ROOT/.tflint.hcl" "$REPO_ROOT")"
  elif [[ -f "$REPO_ROOT/.tflint.hcl" ]]; then
    TFLINT_CONFIG="$(resolve_file "$REPO_ROOT/.tflint.hcl" "$REPO_ROOT")"
  else
    die "No .tflint.hcl found. Add an enabled, pinned AWS plugin config or pass --skip-tflint explicitly."
  fi
fi

for required_command in terraform cp cmp diff find mktemp; do
  if ! command -v "$required_command" >/dev/null 2>&1; then
    die "$required_command is required but was not found on PATH."
  fi
done

if ! FIRST_SYMLINK="$(find "$TF_ROOT" -type l -print -quit)"; then
  die "Unable to inspect the Terraform tree for symbolic links."
fi
if [[ -n "$FIRST_SYMLINK" ]]; then
  die "Terraform tree contains a symbolic link ($FIRST_SYMLINK); refusing because a temporary-copy check could escape back into the source tree."
fi

if [[ "$SKIP_TFLINT" == false ]] && ! command -v tflint >/dev/null 2>&1; then
  die "tflint is required. Install it or pass --skip-tflint explicitly."
fi

if [[ "$SKIP_TRIVY" == false ]] && ! command -v trivy >/dev/null 2>&1; then
  die "trivy is required. Install it or pass --skip-trivy explicitly."
fi

ROOT_UNITS=()
MODULE_UNITS=()

if [[ -d "$TF_ROOT/stacks" ]]; then
  for candidate in "$TF_ROOT/stacks"/*; do
    if [[ -d "$candidate" ]] && has_terraform_configuration "$candidate"; then
      ROOT_UNITS[${#ROOT_UNITS[@]}]="stacks/$(basename "$candidate")"
    fi
  done
fi

if [[ -d "$TF_ROOT/bootstrap/state" ]] &&
    has_terraform_configuration "$TF_ROOT/bootstrap/state"; then
  ROOT_UNITS[${#ROOT_UNITS[@]}]="bootstrap/state"
fi

if [[ -d "$TF_ROOT/modules" ]]; then
  for candidate in "$TF_ROOT/modules"/*; do
    if [[ -d "$candidate" ]] && has_terraform_configuration "$candidate"; then
      MODULE_UNITS[${#MODULE_UNITS[@]}]="modules/$(basename "$candidate")"
    fi
  done
fi

if [[ "${#ROOT_UNITS[@]}" -eq 0 ]]; then
  die "No root modules found under $TF_ROOT/stacks or $TF_ROOT/bootstrap/state."
fi

print_info "Repository root: $REPO_ROOT"
print_info "Terraform directory: $TF_ROOT"
print_info "Discovered ${#ROOT_UNITS[@]} root(s) and ${#MODULE_UNITS[@]} reusable module(s)."

# Do not let caller-provided CLI argument injection weaken read-only flags or
# redirect logs into the source tree. Repository CLI configuration and provider
# installation mirrors remain available.
unset TF_CLI_ARGS
unset TF_CLI_ARGS_fmt
unset TF_CLI_ARGS_init
unset TF_CLI_ARGS_validate
unset TF_CLI_ARGS_providers
unset TF_CLI_ARGS_lock
unset TF_LOG
unset TF_LOG_PATH
unset TF_PLUGIN_CACHE_MAY_BREAK_DEPENDENCY_LOCK_FILE
unset TF_WORKSPACE

FAILURES=0
ROOTS_VALIDATED=0
MODULES_VALIDATED=0
LOCKFILES_AUDITED=0
CHECK_TMP_DIR=""

record_failure() {
  FAILURES=$((FAILURES + 1))
  print_error "$1"
}

cleanup() {
  local exit_status="$?"
  trap - EXIT

  if [[ -n "$CHECK_TMP_DIR" ]] &&
      [[ "$CHECK_TMP_DIR" != "/" ]] &&
      [[ -d "$CHECK_TMP_DIR" ]]; then
    rm -rf "$CHECK_TMP_DIR"
  fi
  exit "$exit_status"
}

trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

print_info "Checking Terraform formatting..."
if terraform fmt -check -diff -recursive "$TF_ROOT"; then
  print_success "Terraform formatting"
else
  record_failure "Terraform formatting"
fi

TMP_BASE="${TMPDIR:-/tmp}"
TMP_BASE="${TMP_BASE%/}"
[[ -n "$TMP_BASE" ]] || TMP_BASE="/"
CHECK_TMP_DIR="$(mktemp -d "$TMP_BASE/terraform-aws-check.XXXXXX")"
chmod 700 "$CHECK_TMP_DIR"

TEMP_TF_ROOT="$CHECK_TMP_DIR/terraform"
print_info "Copying Terraform sources into an isolated temporary directory..."
cp -R "$TF_ROOT" "$TEMP_TF_ROOT"

PROVIDER_LOCK_ARGS=()
if [[ "${#PLATFORMS[@]}" -gt 0 ]]; then
  for platform in "${PLATFORMS[@]}"; do
    PROVIDER_LOCK_ARGS[${#PROVIDER_LOCK_ARGS[@]}]="-platform=$platform"
  done
fi

print_lock_remediation() {
  local source_unit="$1"
  local platform

  printf '       Review and run intentionally:\n' >&2
  printf '         terraform -chdir="%s" providers lock' "$source_unit" >&2
  for platform in "${PLATFORMS[@]}"; do
    printf ' -platform=%s' "$platform" >&2
  done
  printf '\n' >&2
}

validate_root() {
  local relative_path="$1"
  local unit_index="$2"
  local source_unit="$TF_ROOT/$relative_path"
  local copied_unit="$TEMP_TF_ROOT/$relative_path"
  local source_lock="$source_unit/.terraform.lock.hcl"
  local copied_lock="$copied_unit/.terraform.lock.hcl"
  local unit_data="$CHECK_TMP_DIR/terraform-data/root-$unit_index"
  local plugin_cache="$unit_data/plugin-cache"

  print_info "Validating root: $relative_path"

  if [[ ! -f "$source_lock" ]]; then
    record_failure "$relative_path has no committed .terraform.lock.hcl."
    return 0
  fi

  mkdir -p "$plugin_cache"

  if ! TF_DATA_DIR="$unit_data" \
      TF_PLUGIN_CACHE_DIR="$plugin_cache" \
      TF_IN_AUTOMATION=1 \
      TF_INPUT=0 \
      terraform -chdir="$copied_unit" init \
        -backend=false \
        -input=false \
        -lockfile=readonly \
        -no-color; then
    record_failure "Backendless readonly initialization failed: $relative_path"
    return 0
  fi

  if TF_DATA_DIR="$unit_data" \
      TF_PLUGIN_CACHE_DIR="$plugin_cache" \
      TF_IN_AUTOMATION=1 \
      TF_INPUT=0 \
      terraform -chdir="$copied_unit" validate -no-color; then
    ROOTS_VALIDATED=$((ROOTS_VALIDATED + 1))
    print_success "Validated root: $relative_path"
  else
    record_failure "Terraform validation failed: $relative_path"
  fi

  if [[ "${#PLATFORMS[@]}" -eq 0 ]]; then
    return 0
  fi

  print_info "Auditing provider lock platforms: $relative_path"
  if ! TF_DATA_DIR="$unit_data" \
      TF_PLUGIN_CACHE_DIR="$plugin_cache" \
      TF_IN_AUTOMATION=1 \
      TF_INPUT=0 \
      terraform -chdir="$copied_unit" providers lock "${PROVIDER_LOCK_ARGS[@]}"; then
    record_failure "Provider lock platform audit failed: $relative_path"
    return 0
  fi

  if cmp -s "$source_lock" "$copied_lock"; then
    LOCKFILES_AUDITED=$((LOCKFILES_AUDITED + 1))
    print_success "Provider lock platforms: $relative_path"
  else
    record_failure "Provider lockfile is incomplete or stale for requested platforms: $relative_path"
    diff -u "$source_lock" "$copied_lock" >&2 || true
    print_lock_remediation "$source_unit"
  fi
}

validate_module() {
  local relative_path="$1"
  local unit_index="$2"
  local copied_unit="$TEMP_TF_ROOT/$relative_path"
  local unit_data="$CHECK_TMP_DIR/terraform-data/module-$unit_index"
  local plugin_cache="$unit_data/plugin-cache"

  print_info "Validating reusable module: $relative_path"
  mkdir -p "$plugin_cache"

  # Reusable modules do not commit dependency lockfiles. Any lockfile generated
  # by this initialization exists only in the temporary source copy.
  if ! TF_DATA_DIR="$unit_data" \
      TF_PLUGIN_CACHE_DIR="$plugin_cache" \
      TF_IN_AUTOMATION=1 \
      TF_INPUT=0 \
      terraform -chdir="$copied_unit" init \
        -backend=false \
        -input=false \
        -no-color; then
    record_failure "Backendless initialization failed: $relative_path"
    return 0
  fi

  if TF_DATA_DIR="$unit_data" \
      TF_PLUGIN_CACHE_DIR="$plugin_cache" \
      TF_IN_AUTOMATION=1 \
      TF_INPUT=0 \
      terraform -chdir="$copied_unit" validate -no-color; then
    MODULES_VALIDATED=$((MODULES_VALIDATED + 1))
    print_success "Validated reusable module: $relative_path"
  else
    record_failure "Terraform validation failed: $relative_path"
  fi
}

root_index=0
for relative_path in "${ROOT_UNITS[@]}"; do
  root_index=$((root_index + 1))
  validate_root "$relative_path" "$root_index"
done

module_index=0
if [[ "${#MODULE_UNITS[@]}" -gt 0 ]]; then
  for relative_path in "${MODULE_UNITS[@]}"; do
    module_index=$((module_index + 1))
    validate_module "$relative_path" "$module_index"
  done
fi

if [[ "$SKIP_TFLINT" == true ]]; then
  print_warning "TFLint explicitly skipped."
else
  TFLINT_PLUGIN_PATH="$CHECK_TMP_DIR/tflint-plugins"
  mkdir -p "$TFLINT_PLUGIN_PATH"

  print_info "Installing configured TFLint plugins into the temporary directory..."
  if ! (
    cd "$TF_ROOT"
    TFLINT_PLUGIN_DIR="$TFLINT_PLUGIN_PATH" \
      TFLINT_DISABLE_VERSION_CHECK=1 \
      tflint --init --config="$TFLINT_CONFIG"
  ); then
    record_failure "TFLint plugin initialization failed."
  else
    TFLINT_VERSION_OUTPUT=""
    if ! TFLINT_VERSION_OUTPUT="$(
      cd "$TF_ROOT"
      TFLINT_PLUGIN_DIR="$TFLINT_PLUGIN_PATH" \
        TFLINT_DISABLE_VERSION_CHECK=1 \
        tflint --version --config="$TFLINT_CONFIG" 2>&1
    )"; then
      record_failure "Unable to verify installed TFLint plugins."
    elif [[ "$TFLINT_VERSION_OUTPUT" != *"ruleset.aws"* ]]; then
      printf '%s\n' "$TFLINT_VERSION_OUTPUT" >&2
      record_failure "The TFLint config did not install an enabled AWS ruleset. Declare plugin \"aws\" with enabled=true, an exact version, and its source."
    else
      printf '%s\n' "$TFLINT_VERSION_OUTPUT"
      print_info "Running TFLint recursively with the verified AWS ruleset..."
      if (
        cd "$TF_ROOT"
        TFLINT_PLUGIN_DIR="$TFLINT_PLUGIN_PATH" \
          TFLINT_DISABLE_VERSION_CHECK=1 \
          tflint --recursive --config="$TFLINT_CONFIG" --no-color
      ); then
        print_success "TFLint with AWS ruleset"
      else
        record_failure "TFLint reported issues."
      fi
    fi
  fi
fi

if [[ "$SKIP_TRIVY" == true ]]; then
  print_warning "Trivy explicitly skipped."
else
  TRIVY_CACHE_PATH="$CHECK_TMP_DIR/trivy-cache"
  mkdir -p "$TRIVY_CACHE_PATH"

  print_info "Scanning Terraform configuration with Trivy..."
  if (
    cd "$REPO_ROOT"
    trivy config \
      --cache-dir "$TRIVY_CACHE_PATH" \
      --exit-code 1 \
      --misconfig-scanners terraform \
      "$TF_ROOT"
  ); then
    print_success "Trivy Terraform configuration scan"
  else
    record_failure "Trivy reported Terraform misconfigurations or failed to scan."
  fi
fi

printf '\n'
print_info "Validation summary"
printf '  Roots:       %s/%s validated\n' "$ROOTS_VALIDATED" "${#ROOT_UNITS[@]}"
printf '  Modules:     %s/%s validated\n' "$MODULES_VALIDATED" "${#MODULE_UNITS[@]}"

if [[ "${#PLATFORMS[@]}" -gt 0 ]]; then
  printf '  Lockfiles:   %s/%s audited for' "$LOCKFILES_AUDITED" "${#ROOT_UNITS[@]}"
  for platform in "${PLATFORMS[@]}"; do
    printf ' %s' "$platform"
  done
  printf '\n'
else
  printf '  Lockfiles:   cross-platform audit not requested\n'
fi

if [[ "$SKIP_TFLINT" == true ]]; then
  printf '  TFLint:      skipped explicitly\n'
else
  printf '  TFLint:      enabled\n'
fi

if [[ "$SKIP_TRIVY" == true ]]; then
  printf '  Trivy:       skipped explicitly\n'
else
  printf '  Trivy:       enabled\n'
fi

if [[ "$FAILURES" -eq 0 ]]; then
  print_success "All enabled checks passed."
  exit 0
fi

print_error "$FAILURES check(s) failed."
exit 1
