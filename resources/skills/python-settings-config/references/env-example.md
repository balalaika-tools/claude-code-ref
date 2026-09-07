# `.env.example`

Use this reference when creating or changing the root `.env.example`.

## Purpose

`.env.example` documents the environment variables needed for local
development, CI, deployment injection, and environment-selected secret
resolution. It must be safe to commit.

## Conventions

- Always treat the environment selector/name used by the service, such as
  `ENVIRONMENT_NAME` or `APP_ENV`, as required. It must have no YAML or Python
  default and must be listed first in the REQUIRED section (for example,
  `ENVIRONMENT_NAME=local`).
- Include all required local secret env vars with fake values.
- Include required non-secret settings when the app has no safe
  `Field(default=...)` value.
- Include common local overrides for settings only when useful; do not copy
  every default from `Settings`.
- When the user explicitly opts out of YAML, `.env.example` is the main
  operator-facing list of env vars. It should document required values and
  commonly overridden defaults.
- In the default YAML environment-baseline pattern, `.env.example` should avoid
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
- Include required GenAI runtime coordinates — model ID/provider deployment
  name, endpoint/base URL when configurable, region/project/resource name, and
  deployment-owned API version — under **Required — all runtimes**. Do not rely
  on a YAML model fallback.
- Keep `.env.example` as the complete operator and deployment contract even
  when Docker Compose supplies some or all active local values. Cleanup of a
  developer's real `.env` must not remove those documented variables from
  `.env.example`.

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

## Per-Service Files and Section Taxonomy

A repository with several deployables (a uv workspace with `services/*`) has two
kinds of `.env.example`, and they answer different questions:

| File | Question it answers | Content |
| --- | --- | --- |
| `<repo-root>/.env.example` | What does the deployment tool need to render and start the stack? | Secrets, image pins, credential passthrough, and the deployment coordinates Compose or Helm injects into containers |
| `services/<name>/.env.example` | What does this process read at startup, whatever starts it? | The service's complete settings contract, in the three sections below |

The root file never substitutes for the service file: a service can be started by
`uv run`, a test, or another orchestrator, and the person doing that must find the
complete contract beside the code. Keep the two consistent; the service file is
authoritative for names and defaults.

Structure every service file as exactly these three sections, in this order,
with a one-line comment per variable:

```dotenv
################################################################################
# REQUIRED — the service fails at startup, naming the variable, when any is missing
################################################################################
# Selects config/<service>/<name>.yaml. Always required; there is no implicit environment.
ENVIRONMENT_NAME=local
DATABASE_URL=postgresql+psycopg://app:replace-me@127.0.0.1:5432/app
PRIMARY_MODEL_ID=
MODEL_REGION=

################################################################################
# OVERRIDABLE — application policy baselined in config/<service>/<environment>.yaml
# Setting one here overrides the YAML key for this process only. Values shown are
# the baseline defaults.
################################################################################
# DB_POOL_SIZE=5
# REQUEST_TIMEOUT_SECONDS=30
# LOG_LEVEL=INFO

################################################################################
# OPTIONAL — rare runtime-only variables for specific situations
################################################################################
# Resource identity; the container hostname is used when unset.
SERVICE_INSTANCE_ID=
# Escape hatch when the baseline is not discoverable beside the package.
<SERVICE>_CONFIG_DIR=
```

Classification rules:

- **REQUIRED** always starts with `ENVIRONMENT_NAME`: the environment selector
  has no default, because an implicit environment is how a production process
  ends up reading a local baseline. It then holds the rest of the deployment
  contract with no safe default: resource coordinates, secrets or their
  locators, GenAI runtime coordinates. Credential
  passthrough variables read by an SDK chain rather than by settings are listed
  here too, marked as such, because the process cannot work without them.
- **OVERRIDABLE** lists every key of the YAML policy baseline, commented out,
  with its baseline value. Anything that has a safe application default belongs
  in YAML and therefore here, including endpoints or paths whose default is
  correct for every deployment represented by the baseline. Nothing in this
  section is uncommented in a fresh copy.
- **OPTIONAL** is deliberately small: variables that exist for a specific
  runtime situation and are rarely set, such as a per-instance identity supplied
  by the platform, a configuration-directory escape hatch, or a diagnostic
  switch. It is
  not the home of "values with a default"; those are OVERRIDABLE.

Add a contract test that reads the service file, splits it on the three headers,
and asserts: REQUIRED equals the aliases of the settings fields without a default
(plus any documented passthrough), OVERRIDABLE equals the aliases of the YAML
policy allowlist, and OPTIONAL equals the remaining fields plus the documented
escape hatches. The test is what keeps the file honest after the next setting is
added.

## Env Vars + Pydantic Defaults Template — Explicit YAML Opt-Out Only

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

## YAML Application-Baseline + Env Contract Template — Default

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

# Runtime-selected GenAI coordinates also have no YAML fallback.
PRIMARY_MODEL_ID=replace-me-model-id
MODEL_REGION=replace-me-region


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
