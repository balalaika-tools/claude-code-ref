# `.env.example`

Use this reference when creating or changing the root `.env.example`.

## Purpose

`.env.example` documents the environment variables needed for local
development, CI, and optional remote-secret-provider bypass. It must be safe to
commit.

## Conventions

- Always include `ENVIRONMENT_NAME=local`.
- Include optional `CONFIG_DIR` with a commented example.
- Include all required local secret env vars with fake values.
- Include common local overrides for settings only when useful.
- Include remote-provider variables only for the selected backend, or comment
  them as examples during scaffolding.
- Never include real credentials.

## Template

```dotenv
# Selects config/{ENVIRONMENT_NAME}.yaml.
ENVIRONMENT_NAME=local

# Optional: set when running outside the project root.
# CONFIG_DIR=/absolute/path/to/config

# Optional local overrides for non-secret settings.
LOG_LEVEL=DEBUG
APP_HOST=0.0.0.0
APP_PORT=8080

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
