# `config/*.yaml`

Use this reference when creating or changing environment YAML files under the
project-root `config/` directory.

## Purpose

YAML files hold committed, non-secret operational baselines for each
environment. They should make runtime behavior auditable without exposing
credentials.

## Conventions

- Keep `config/` at the project root, sibling to `src/` and `pyproject.toml`.
- Use one YAML file per environment.
- Prefer `local.yaml`, `staging.yaml`, and `production.yaml` for new services.
- Preserve existing names such as `dev.yaml` or `prod.yaml` in established
  repos.
- Use snake_case YAML keys matching the `Settings` field names.
- Include every operational setting that varies by environment.
- Never include passwords, API keys, tokens, signing keys, credential-bearing
  DSNs, or private keys.

## Operational Values

Put these in YAML:

- App metadata, host, port, and logging behavior.
- Cloud regions and non-secret resource names.
- Queue names, bucket names, table names, prefixes, and feature flags.
- Model providers, model IDs, retry limits, timeouts, and token limits.
- Database host, port, name, user, schema, and pool sizes.

Do not put these in YAML:

- Passwords.
- API keys.
- OAuth client secrets.
- JWT signing keys.
- Provider access tokens.
- DSNs that include credentials.

## Examples

`config/local.yaml`

```yaml
# Local non-secret defaults. Do not put secrets in YAML.
environment_name: local
log_level: DEBUG
app_title: AI Service
app_host: 0.0.0.0
app_port: 8080
model_provider: openai
primary_model_id: replace-me-local-model-id
request_timeout_seconds: 30
```

`config/staging.yaml`

```yaml
# Staging non-secret defaults. Do not put secrets in YAML.
environment_name: staging
log_level: INFO
app_title: AI Service
app_host: 0.0.0.0
app_port: 8080
model_provider: openai
primary_model_id: replace-me-staging-model-id
request_timeout_seconds: 30
```

`config/production.yaml`

```yaml
# Production non-secret defaults. Do not put secrets in YAML.
environment_name: production
log_level: WARNING
app_title: AI Service
app_host: 0.0.0.0
app_port: 8080
model_provider: openai
primary_model_id: replace-me-production-model-id
request_timeout_seconds: 30
```
