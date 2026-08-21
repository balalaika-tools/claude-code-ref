---
name: settings-config
description: >
  Use when creating, extending, or reviewing application configuration for a
  Python/FastAPI AI service: `src/<package>/core/settings.py`,
  `src/<package>/core/secrets.py`, root `config/*.yaml`, `.env.example`,
  Pydantic/pydantic-settings models, SecretStr usage, environment-specific
  YAML baselines, or secret-manager integration with AWS SSM, Azure Key Vault,
  GCP Secret Manager, Vault, or another SDK. Also use when the user calls
  /settings-config explicitly.
---

# Settings & Secrets

Create a small, typed configuration surface for FastAPI agent services.
Secrets stay out of git, startup fails early when configuration is invalid,
and non-secret settings follow one clear ownership pattern.

## Pattern Decision

Two independent choices must be resolved before scaffolding or changing
configuration. If the user has not clearly chosen for either axis, ask before
proceeding — do not silently pick one. When an existing project already uses
one pattern consistently, follow that pattern unless the user asks to migrate.

### Non-secret value source

1. **YAML environment baselines**: committed `config/{environment}.yaml` files
   hold non-secret values that rarely change and are intentionally different
   per environment. Process env vars and `.env` may still override them, but
   deployment should not routinely override YAML-owned keys. Once there's a
   baseline worth sharing across environments and/or a per-service file worth
   keeping separate from the environment overlay, use the layered variant
   instead — `config/base.yaml` plus a `config/{environment}.yaml` overlay
   plus a per-service file under `config/services/`. Same design whether the
   repo has one deployable or many; see `references/config-yaml.md`, "Layered
   Composition".
2. **Env vars + Pydantic field defaults**: no YAML source. Safe application
   defaults live directly in `Field(default=...)`; values with no safe default
   use `Field(...)`; `.env` is only a local override file; dev/staging/prod
   overrides are provided by real environment variables/Helm.

### Field grouping

1. **Flat** (default — recommend this unless the user asks for grouping): a
   single `Settings` class with all fields at the top level.
2. **Nested**: one `Settings(BaseSettings)` root with related fields grouped
   into plain `BaseModel` subgroups (see `references/settings-py.md`,
   "Nested Field Grouping"). Flag two things when asking: this renames env
   vars for every grouped field (e.g. `SERVER__APP_PORT` instead of
   `APP_PORT`) — a breaking change for existing deployments, not a
   transparent refactor — and it only pays off once field count is large
   enough (several dozen+) that flat namespacing hurts readability.

If the user gives no preference on either axis, ask explicitly (e.g. "YAML
baselines or env-vars/defaults only? Flat `Settings` or nested groups?")
rather than assuming flat/env-vars by default.

## Target Layout

```text
<project-root>/
  .env.example
  src/
    <package>/
      core/
        settings.py
        secrets.py
```

For the YAML environment-baseline pattern, also include:

```text
<project-root>/
  config/
    local.yaml
    dev.yaml
    staging.yaml
    prod.yaml
```

Standardize new services on four environments: `local`, `dev`, `staging`,
`prod`. Keep an existing repo's current environment names (e.g. `production`
instead of `prod`, or a missing `dev` tier) rather than renaming a live
project's env values — that changes the `ENVIRONMENT_NAME` contract every
deployment relies on.

## Reference Routing

Load only the reference needed for the file you are creating or changing:

- `references/settings-py.md`: `core/settings.py`, `Settings`, pattern-specific
  source ordering, Pydantic field conventions, and startup validation.
- `references/secrets-py.md`: `core/secrets.py`, `SecretStr`, env-backed
  secrets, remote secret providers, async loading, and local bypass.
- `references/config-yaml.md`: root `config/*.yaml`, environment baselines,
  YAML key conventions, and non-secret operational parameters.
- `references/env-example.md`: `.env.example`, required variables, comments,
  local defaults, and remote-provider bypass variables.

If scaffolding the YAML environment-baseline pattern, read all four references.
If scaffolding the env vars + Pydantic defaults pattern, read
`settings-py.md`, `secrets-py.md`, and `env-example.md`.
For a small field addition, read only the affected reference files.

## Core Conventions

- For the YAML environment-baseline pattern, put non-secret operational
  parameters in `config/{environment}.yaml` only when the value rarely changes,
  is intentionally environment-specific, and is correct for every cluster an
  environment spans. Do not put a key in YAML when deployment normally injects
  the same key as an env var; that makes YAML stale documentation with runtime
  side effects. See `references/config-yaml.md`.
- For the env vars + Pydantic defaults pattern, put safe application defaults
  directly on the Pydantic fields with `Field(default=...)`. Do not create
  defaults for values that the app cannot safely choose; use `Field(...)` and
  document the required env var in `.env.example`.
- Operationally/business configurable values, and any value that legitimately
  differs across environments or clusters (cloud region, a downstream service
  URL reached at a different cluster-local hostname per cluster, etc.), belong
  in `.env.example` / env vars, Helm-injected in real deployments. The test: if
  this value would ever differ between two clusters in the *same* environment,
  it must be env-var/Helm-only.
- Set `extra="forbid"` on every `model_config` — `Settings`, `Secrets`, and any
  nested `BaseModel` group or section. A misspelled key or a renamed field
  should fail startup as an unknown key, not silently vanish as an ignored
  extra while the app runs on an unset default.
- Put secrets in `secrets.py`, never in YAML and never as `Settings` fields.
- Always create or update `.env.example`.
- Use `Field(..., description="...")` for required values and
  `Field(default=..., description="...")` only for sensible, safe defaults.
- Use `Literal[...]` for constrained values such as environments, log levels,
  providers, and modes.
- Use `SecretStr` for passwords, tokens, API keys, signing keys, and DSNs that
  contain credentials.
- Prefer Pydantic's specific types over bare `str`/`int`/`float` whenever a
  field's value has a narrower natural type — ports and limits as
  `PositiveInt`/`NonNegativeInt`, timeouts as `PositiveFloat`, URLs as
  `AnyHttpUrl`/`AnyUrl`, filesystem paths as `Path`, IDs as `UUID`, money as
  `Decimal`, calendar/time values as `date`/`datetime`/`AwareDatetime`, memory
  or payload sizes as `ByteSize`. See `references/settings-py.md`, "Preferred
  Pydantic Types" for the full decision list.
- When using the YAML pattern and `Settings` fields use env-var aliases while
  YAML uses snake_case field names, set `populate_by_name=True`; otherwise
  aliased fields may ignore YAML keys and silently fall back to Python defaults.
- Treat `BaseSettings` as a config reader, not an environment mutator. Values
  loaded from `.env` or YAML are available on the `Settings` object, but are not
  written back to `os.environ`.
- When a library can be configured either by env vars or constructor arguments,
  prefer passing resolved `Settings` values explicitly. Only bridge values into
  `os.environ` deliberately, in one bootstrap helper, when the library has no
  explicit configuration API.
- Avoid direct `os.getenv()` calls outside configuration bootstrap code.
- Validate settings and secrets during FastAPI startup before accepting traffic.
- In the YAML pattern, resolve `config/` by walking upward from `settings.py`'s
  actual installed file path until a real ancestor-owned `config/` directory is
  found. Do not hard-code `Path(__file__).parents[N]`: non-editable Docker
  installs move the module into `.venv/.../site-packages` while `config/`
  still lives under the app root. Do not resolve from the process working
  directory. See
  `references/settings-py.md`.

## Secret Backend Decision

If the user does not name a secret manager, generate an env-backed
`pydantic-settings` secrets model that reads `.env` and process env vars.

If the user names a backend, create a dedicated provider class in `secrets.py`
for that backend, such as `AwsSsmSecretsProvider`,
`AzureKeyVaultSecretsProvider`, `GcpSecretManagerSecretsProvider`, or
`VaultSecretsProvider`. Prefer async loading; when the SDK is sync-only, wrap
the remote calls with `asyncio.to_thread`. Local development must still be able
to bypass the remote provider through `.env` injection.

When `Settings` names secrets rather than hardcoding them (a `secrets:
SecretNames | None` field, required outside `local`), select the provider by
environment instead of a bypass flag: `local` always uses the env-backed
provider, every other environment always resolves through the remote one
using the names `Settings.secrets` supplies. See `references/secrets-py.md`,
"Environment-Selected Secrets Provider".

## Change Checklist

When adding a setting under the YAML environment-baseline pattern, update
`Settings`, every relevant `config/*.yaml`, and `.env.example` if local
developers commonly override it. Do not add YAML values for keys that
deployment normally supplies as env vars.

When adding a setting under the env vars + Pydantic defaults pattern, update
`Settings` and `.env.example` when the setting is required or commonly
overridden. Add a `Field(default=...)` only when the default is safe and
intentional.

When adding a secret, update the secrets model, the env-backed loader, any
selected remote provider, and `.env.example`.
