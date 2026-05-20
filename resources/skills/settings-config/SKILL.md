---
name: settings-config
description: >
  Use when a Python developer is setting up, extending, or restructuring app
  configuration: creating a new settings module, adding a typed config field or
  SecretStr secret, organizing defaults into per-environment YAML files
  (local.yaml, prod.yaml), bootstrapping config/secrets for a new microservice,
  or replacing scattered os.getenv() calls with a centralized class. This skill
  delivers a pydantic-settings-based Settings + Secrets pattern with .env for
  local dev and AWS SSM for production. Invoke for any task where the user is
  building or extending this config/secrets structure. Skip for: generic env var
  reading without a settings class, raw boto3/SSM API calls, pydantic model
  validation unrelated to app config, logging setup, or infrastructure tooling.
  Also use when the user calls /settings-config explicitly.
---

# Settings & Secrets Configuration

This skill scaffolds the two-file config pattern used across our Python projects:
`settings.py` for non-secret configuration, `secrets.py` for secrets — both based
on the canonical template in `settings_config/`.

## The Pattern at a Glance

```
<project-root>/
  config/                         # Lives at the project root (committed)
    local.yaml                    # Baseline for ENVIRONMENT_NAME=local
    prod.yaml                     # Baseline for ENVIRONMENT_NAME=prod
  .env                            # Local developer overrides (gitignored)
  src/
    your_package/
      core/
        settings.py               # Settings(BaseSettings) + AppConfig entry point
        secrets.py                # SecretsProvider ABC + Secrets(BaseModel)
```

**Important — folder layout:**
- Code lives under `src/your_package/core/`. Both `settings.py` and `secrets.py`
  go inside the `core/` subpackage (alongside other cross-cutting infra like
  `logger.py`, `db.py`). They are **not** placed at the top of `your_package/`.
- The reference implementation is `src/exceptionist/core/settings.py`. Imports
  follow the absolute-package form, e.g.
  `from exceptionist.core.secrets import Secrets, get_secrets`.
- `config/` resides at the **project root** (sibling of `src/`, `pyproject.toml`),
  not inside the package. This keeps environment baselines decoupled from the
  shipped wheel and committable in the repo.

**Config directory tracking:** the helper `_find_config_dir()` in `settings.py`
walks up from the current working directory until it finds a `config/` folder.
That makes it work whether you run from the repo root, a subdirectory, or an
installed venv invoked from inside the project tree. For containers / CI where
CWD may not be inside the project, set `CONFIG_DIR` explicitly to bypass the
walk-up and point at the correct directory.

**Resolution order** (highest priority wins):
1. Process env vars — CI / container runtime
2. `.env` file — local developer overrides
3. `config/{ENVIRONMENT_NAME}.yaml` — environment baseline (committed)
4. Defaults on the `Settings` class — sensible fallbacks

**Secrets** are resolved separately:
- `SSM_PARAMETER_PREFIX` **not set** → `EnvSecretsProvider` reads from env vars (populated by `.env`)
- `SSM_PARAMETER_PREFIX` **set** → `SSMSecretsProvider` reads from AWS SSM Parameter Store

## Step-by-Step: Setting Up a New Project

### 1. Audit what the app needs

Before writing anything, ask (or infer from the codebase):
- What **non-secret** config does the app need? (hosts, ports, feature flags, region, timeouts…)
- What **secrets** does the app need? (passwords, API keys, signing keys, OAuth secrets…)
- Does the app deploy to AWS? (determines whether SSM is needed)
- What environments exist? (`local`, `dev`, `staging`, `prod`?)

The line between settings and secrets is: **could this value appear in a git commit without any risk?** If no → it's a secret.

### 2. Copy the template files

Copy the templates in `references/template_files.md` verbatim into
`src/your_package/core/` — **both** `settings.py` and `secrets.py` belong in
the `core/` subpackage, not at the top of `your_package/`. If `core/` does
not yet exist, create it with an `__init__.py`. These files are designed to
be copied as-is — **only edit the typed field declarations and
`load_secrets()` body**.

If you rename the package, also update the relative import in `settings.py`
(`from .secrets import Secrets, get_secrets`) — it stays relative, so no
absolute path change is needed.

Never change:
- `settings_customise_sources()` (source priority wiring)
- `_find_config_dir()` / `_yaml_path()` (config-dir walk-up; override with `CONFIG_DIR`)
- `build_secrets_provider()` (provider selection logic)
- `get_settings()`, `get_secrets()`, `get_config()` (cached accessors)

### 3. Declare config fields in `Settings`

For each non-secret config value, add a typed field with `Field(alias="ENV_VAR_NAME")`:

```python
# General
environment_name: Literal["local", "dev", "staging", "prod"] = Field(
    default="local", alias="ENVIRONMENT_NAME"
)
log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
    default="WARNING", alias="LOG_LEVEL"
)

# AWS
aws_default_region: str = Field(default="us-east-1", alias="AWS_DEFAULT_REGION")

# App-specific examples
s3_bucket: str = Field(default="my-app-bucket", alias="S3_BUCKET")
request_timeout_seconds: float = Field(default=30.0, alias="REQUEST_TIMEOUT_SECONDS")
feature_flag_x: bool = Field(default=False, alias="FEATURE_FLAG_X")
```

Rules:
- Use `Literal[...]` for enum-like strings
- Use native Python types (`str`, `int`, `float`, `bool`) everywhere else
- `alias` matches the env var / YAML key exactly (SCREAMING_SNAKE_CASE)
- Always provide a sensible `default`

### 4. Declare secrets in `Secrets` and wire `load_secrets()`

```python
# In Secrets class:
class Secrets(BaseModel):
    model_config = ConfigDict(frozen=True)

    db_password: SecretStr
    api_key: SecretStr
    jwt_signing_key: SecretStr
```

```python
# In load_secrets():
def load_secrets(provider=None):
    p = provider or build_secrets_provider()
    return Secrets(
        db_password=SecretStr(p.get("db/password")),
        api_key=SecretStr(p.get("api/key")),
        jwt_signing_key=SecretStr(p.get("jwt/signing-key")),
    )
```

The logical key (e.g., `"db/password"`) maps to:
- **Local dev**: env var `DB_PASSWORD` (key translated: `/` → `_`, uppercased)
- **Prod SSM**: `{SSM_PARAMETER_PREFIX}/db/password`

Document both mappings in a comment or runbook entry whenever you add a secret.

### 5. Create config YAML stubs

`config/local.yaml` — committed, safe for dev defaults, **no secrets**:
```yaml
environment_name: local
log_level: DEBUG
aws_default_region: us-east-1
# add all non-secret settings with local-appropriate values
```

`config/prod.yaml` — committed, production non-secret defaults:
```yaml
environment_name: prod
log_level: WARNING
aws_default_region: us-east-1
# prod values — still no secrets
```

The `CONFIG_DIR` env var overrides the auto-discovery walk-up. Set it explicitly in
containers if the process doesn't run from the project root.

### 6. Create / update `.env` for local dev

`.env` holds **both** local config overrides and local secret values (since
`SSM_PARAMETER_PREFIX` is not set locally):

```
# Config overrides (optional — YAML baseline is usually enough)
LOG_LEVEL=DEBUG

# Secrets (required locally — no SSM in local dev)
DB_PASSWORD=localpassword123
API_KEY=dev-api-key-here
JWT_SIGNING_KEY=dev-signing-key
```

**Always ensure `.env` is in `.gitignore`.**

### 7. Wire access in app code

```python
from your_package.core.settings import get_config

# Process-wide singleton — call anywhere, cached after first load
cfg = get_config()

# Non-secret config
print(cfg.settings.db_host)
print(cfg.settings.aws_default_region)

# Secrets — .get_secret_value() required; prevents accidental logging
db_pw = cfg.secrets.db_password.get_secret_value()
api_key = cfg.secrets.api_key.get_secret_value()
```

Prefer **injecting** `AppConfig` (or its sub-pieces) into services rather than
calling `get_config()` deep inside business logic — it makes unit testing easier
and avoids hidden import-time coupling.

### 8. Install dependencies

```bash
pip install "pydantic-settings[yaml]"
# boto3 only needed for prod SSM; skip if not deploying to AWS
pip install boto3
```

Or in `pyproject.toml`:
```toml
[project]
dependencies = [
    "pydantic-settings[yaml]>=2.14.1",
    "boto3",  # remove if no AWS
]
```

## Adding to an Existing Project

### Adding a new config setting

1. Add typed field to `Settings` with `Field(alias="...")`
2. Add the value to relevant `config/*.yaml` files
3. If overridable locally, document the env var name

### Adding a new secret

1. Add `secret_name: SecretStr` to `Secrets`
2. Add `secret_name=SecretStr(p.get("logical/key"))` in `load_secrets()`
3. Add `SECRET_NAME=value` to `.env` (local)
4. Add `{prefix}/logical/key` to SSM Parameter Store (prod)
5. Document: env var name + SSM path

## Common Pitfalls to Avoid

- **Secrets in YAML files** — YAML is committed; secrets must never appear there
- **Secrets in `settings.py` fields** — `Settings` is for non-secrets only
- **Using `os.getenv()` directly** — consolidate into `Settings` or `Secrets` instead
- **Forgetting `.env` in `.gitignore`** — check before first commit
- **Not wrapping secret reads in `.get_secret_value()`** — `SecretStr` masks in logs;
  reading `.get_secret_value()` is the intentional signal that you know you're exposing it
- **Hardcoding `config/` path** — use `CONFIG_DIR` env var for non-standard layouts
- **Putting `settings.py`/`secrets.py` at the package root** — they belong in
  `src/your_package/core/`, alongside other cross-cutting infra modules
- **Placing `config/` inside the package** — it lives at the **project root**
  (sibling of `src/`), so it stays out of the shipped wheel and is committed
  in the repo

## Quick Reference

| Goal | Where it goes |
|---|---|
| Non-secret config (host, port, region, flags) | `Settings` field + `config/*.yaml` |
| Secret (password, key, token) | `Secrets` field + `load_secrets()` + `.env` / SSM |
| Override in CI/containers | Process env var (highest priority) |
| Override locally | `.env` file |
| Environment baseline | `config/{env}.yaml` |

See `references/template_files.md` for the full verbatim template content to copy.
