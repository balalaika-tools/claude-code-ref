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

Create a small, typed configuration surface for FastAPI agent services:
operational parameters live in committed YAML, secrets stay out of git, and
startup fails early when configuration is invalid.

## Target Layout

```text
<project-root>/
  config/
    local.yaml
    staging.yaml
    production.yaml
  .env.example
  src/
    <package>/
      core/
        settings.py
        secrets.py
```

Keep existing environment names when a repo already uses them, such as `dev`
or `prod`.

## Reference Routing

Load only the reference needed for the file you are creating or changing:

- `references/settings-py.md`: `core/settings.py`, `Settings`, config source
  ordering, Pydantic field conventions, and startup validation.
- `references/secrets-py.md`: `core/secrets.py`, `SecretStr`, env-backed
  secrets, remote secret providers, async loading, and local bypass.
- `references/config-yaml.md`: root `config/*.yaml`, environment baselines,
  YAML key conventions, and non-secret operational parameters.
- `references/env-example.md`: `.env.example`, required variables, comments,
  local defaults, and remote-provider bypass variables.

If scaffolding the whole configuration structure, read all four references.
For a small field addition, read only the affected reference files.

## Core Conventions

- Put non-secret operational parameters in `config/{environment}.yaml`.
- Put secrets in `secrets.py`, never in YAML and never as `Settings` fields.
- Always create or update `.env.example`.
- Use `Field(..., description="...")` for required values and
  `Field(default=..., description="...")` for sensible defaults.
- Use `Literal[...]` for constrained values such as environments, log levels,
  providers, and modes.
- Use `SecretStr` for passwords, tokens, API keys, signing keys, and DSNs that
  contain credentials.
- When `Settings` fields use env-var aliases and YAML uses snake_case field
  names, set `populate_by_name=True`; otherwise aliased fields may ignore YAML
  keys and silently fall back to Python defaults.
- Avoid direct `os.getenv()` calls outside configuration bootstrap code.
- Validate settings and secrets during FastAPI startup before accepting traffic.

## Secret Backend Decision

If the user does not name a secret manager, generate an env-backed
`pydantic-settings` secrets model that reads `.env` and process env vars.

If the user names a backend, create a dedicated provider class in `secrets.py`
for that backend, such as `AwsSsmSecretsProvider`,
`AzureKeyVaultSecretsProvider`, `GcpSecretManagerSecretsProvider`, or
`VaultSecretsProvider`. Prefer async loading; when the SDK is sync-only, wrap
the remote calls with `asyncio.to_thread`. Local development must still be able
to bypass the remote provider through `.env` injection.

## Change Checklist

When adding a setting, update `Settings`, every relevant `config/*.yaml`, and
`.env.example` if local developers commonly override it.

When adding a secret, update the secrets model, the env-backed loader, any
selected remote provider, and `.env.example`.
