# `.env.example`

Use this reference when creating or changing the root `.env.example`.

## Purpose

`.env.example` documents the environment variables needed for local
development, CI, deployment overrides, and optional remote-secret-provider
bypass. It must be safe to commit.

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
- Include remote-provider variables only for the selected backend, or comment
  them as examples during scaffolding.
- Never include real credentials.

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

# Deployment-topology values, not application defaults — differ per cluster
# even within one environment (e.g. eu-central-1 for one cluster vs
# us-west-2 for the rest of "production"), so they're Helm-injected in every
# real environment.
AWS_REGION=us-west-2
DOWNSTREAM_SERVICE_URL=http://localhost:9000

# Local-development secrets. Replace with safe local/test values only.
DATABASE_PASSWORD=local-dev-password
LLM_API_KEY=replace-me

# Remote secret-manager bypass for local debugging.
BYPASS_REMOTE_SECRETS=true
```

## YAML Environment-Baseline Template

Use this template when `config/{ENVIRONMENT_NAME}.yaml` exists and owns
committed non-secret baselines.

```dotenv
# Selects config/{ENVIRONMENT_NAME}.yaml.
ENVIRONMENT_NAME=local

# Optional local overrides for non-secret settings.
LOG_LEVEL=DEBUG
APP_HOST=0.0.0.0
APP_PORT=8080

# Deployment-topology values, not application defaults — differ per cluster
# even within one environment (e.g. eu-central-1 for one cluster vs
# us-west-2 for the rest of "production"), so they're Helm-injected in every
# real environment rather than owned by config/{ENVIRONMENT_NAME}.yaml.
AWS_REGION=us-west-2
DOWNSTREAM_SERVICE_URL=http://localhost:9000

# Local-development secrets. Replace with safe local/test values only.
DATABASE_PASSWORD=local-dev-password
LLM_API_KEY=replace-me

# Remote secret-manager bypass for local debugging.
BYPASS_REMOTE_SECRETS=true

# Remote provider settings, if the project uses one. Keep only the variables
# required by the selected backend.
# SECRET_BACKEND=aws-ssm
# AWS_DEFAULT_REGION=us-east-1
# SECRET_PARAMETER_PREFIX=/my-service/local
# AZURE_KEY_VAULT_URL=https://example.vault.azure.net/
# GCP_SECRET_PROJECT_ID=my-gcp-project
# VAULT_ADDR=http://127.0.0.1:8200
```

When adding a new secret, add its env var here even when production uses a
remote secret manager; `.env` remains the local bypass path.
