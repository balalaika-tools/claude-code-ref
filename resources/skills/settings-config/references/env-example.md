# `.env.example`

Use this reference when creating or changing the root `.env.example`.

## Purpose

`.env.example` documents the environment variables needed for local
development, CI, deployment injection, and environment-selected secret
resolution. It must be safe to commit.

## Conventions

- Include the environment selector/name used by the service, such as
  `ENVIRONMENT_NAME=local` or `APP_ENV=local`.
- Include all required local secret env vars with fake values.
- Include required non-secret settings when the app has no safe
  `Field(default=...)` value.
- Include common local overrides for settings only when useful; do not copy
  every default from `Settings`.
- In the env vars + Pydantic defaults pattern, `.env.example` is the main
  operator-facing list of env vars. It should document required values and
  commonly overridden defaults.
- In the YAML environment-baseline pattern, `.env.example` should avoid
  duplicating YAML-owned keys unless local developers commonly override them.
- Include deployment-topology values — non-secret settings deliberately kept
  out of `config/*.yaml` because they can differ between clusters in the same
  environment (cloud region, a downstream service URL, etc.) — with a comment
  explaining why they live here instead of YAML. See `config-yaml.md`'s
  "Deployment-Topology Values Are Not YAML Either" for the test that puts a
  value in this category.
- Include infrastructure-owned resource names even when they are currently
  stable; the deployment system, not application YAML, remains their source of
  truth.
- Include remote-provider variables only for the selected backend. When local
  payloads and deployed locators use the same stable logical variable, show the
  local value active and the deployed form commented as documentation.
- Never include real credentials.

For YAML/config + `.env`, use prominent separators and this order:

1. **Required — all runtimes**: environment selection and non-secret runtime
   coordinates with no safe default.
2. **Required — local only**: logical secret payloads and local-emulator
   credentials. Use JSON only for structured secret schemas; use a plain string
   for scalar secrets.
3. **Deployed only — injected**: commented examples of the same logical secret
   variables holding remote-provider locators, plus notes on which deployment
   system owns the values.
4. **Useful local overrides**: host/base-URL overrides, log level, safety
   switches, or other settings developers commonly change.
5. **Advanced/diagnostic overrides**: a small curated commented list with
   operational warnings where appropriate.

Do not add an exhaustive "all possible overrides" dump. That duplicates the
typed settings schema and becomes stale. The template is a safe, copyable local
bootstrap plus a deployment-contract guide; the settings model or generated
configuration reference remains authoritative for uncommon overrides.

## Env Vars + Pydantic Defaults Template

Use this template when there are no committed `config/*.yaml` baselines.

```dotenv
# Runtime environment name for logs, telemetry, and conditional behavior.
ENVIRONMENT_NAME=local

# Required non-secret settings with no safe application default.
PRIMARY_MODEL_ID=replace-me-local-model-id

# Optional local overrides for non-secret settings.
LOG_LEVEL=DEBUG
APP_HOST=0.0.0.0
APP_PORT=8080
REQUEST_TIMEOUT_SECONDS=30

# Deployment-topology values, not application defaults. The deployment system
# injects the real values outside local development.
PLATFORM_REGION=replace-me-local-region
DOWNSTREAM_SERVICE_BASE_URL=http://localhost:9000

# Local-development secrets. Replace with safe local/test values only.
DATABASE_PASSWORD=local-dev-password
LLM_API_KEY=replace-me
```

## YAML Application-Baseline + Env Contract Template

Use this template when `config/{ENVIRONMENT_NAME}.yaml` exists and owns
committed non-secret baselines.

```dotenv
################################################################################
# REQUIRED — ALL RUNTIMES
################################################################################

# Selects config/{ENVIRONMENT_NAME}.yaml and the matching secret provider.
ENVIRONMENT_NAME=local

# Deployment topology has no YAML fallback. Deployment tooling injects the
# real values; these local values point at developer-owned infrastructure.
RESOURCE_BUCKET_NAME=local-app-resources
DOWNSTREAM_SERVICE_BASE_URL=http://127.0.0.1:9000


################################################################################
# REQUIRED — LOCAL ONLY
################################################################################

# Same logical source variables are used when deployed. Locally they carry
# payloads. JSON is used only because SERVICE_ACCOUNT_SECRET is structured;
# the scalar API key remains a plain string.
DATABASE_SECRET=replace-me-local-dsn
SERVICE_ACCOUNT_SECRET={"username":"replace-me","password":"replace-me"}
LLM_API_KEY_SECRET=replace-me

# Credentials for a local emulator only; deployed workloads use runtime identity.
LOCAL_STORE_ACCESS_KEY=replace-me
LOCAL_STORE_SECRET_KEY=replace-me


################################################################################
# DEPLOYED ONLY — INJECTED BY THE DEPLOYMENT SYSTEM
################################################################################

# In a deployed runtime the same variables contain provider-specific locators.
# Do not uncomment these in the local .env file.
# DATABASE_SECRET=provider-specific/database-locator
# SERVICE_ACCOUNT_SECRET=provider-specific/account-locator
# LLM_API_KEY_SECRET=provider-specific/api-key-locator


################################################################################
# USEFUL LOCAL OVERRIDES
################################################################################

LOG_LEVEL=DEBUG
APP_HOST=0.0.0.0
APP_PORT=8080


################################################################################
# ADVANCED / DIAGNOSTIC OVERRIDES
################################################################################

# REQUEST_TIMEOUT_SECONDS=60
# DATABASE_TRACING_ENABLED=false
```

When adding a new secret, add its stable logical source variable here even when
production uses a remote provider. The selected provider changes the variable's
interpretation; its name and the resolved payload schema stay stable.
