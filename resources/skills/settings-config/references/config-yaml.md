# `config/*.yaml`

Use this reference only when the selected pattern is YAML environment
baselines and you are creating or changing files under the project-root
`config/` directory. If the user has not chosen between YAML baselines and env
vars + Pydantic field defaults, ask before creating YAML files.

## Purpose

YAML files hold committed, non-secret operational baselines for each
environment. They should make runtime behavior auditable without exposing
credentials. YAML is useful when these values rarely change and the repo should
show the intended difference between `local`, `staging`, `production`, or the
project's equivalent environments.

Do not use YAML as a second copy of values that deployment normally provides as
environment variables. In that case, the environment variable is the real
source of truth and the YAML value is likely to become stale or misleading.

## Conventions

- Keep `config/` at the project root, sibling to `src/` and `pyproject.toml`.
- Use one YAML file per environment.
- Prefer `local.yaml`, `staging.yaml`, and `production.yaml` for new services.
- Preserve existing names such as `dev.yaml` or `prod.yaml` in established
  repos.
- Use snake_case YAML keys matching the `Settings` field names.
- If the matching `Settings` fields use env-var aliases, ensure the settings
  model has `populate_by_name=True`; otherwise these snake_case YAML keys may
  not populate aliased fields.
- Include every non-secret operational setting that rarely changes and is
  intentionally owned by the environment baseline.
- Never include passwords, API keys, tokens, signing keys, credential-bearing
  DSNs, or private keys.
- Do not include keys that are normally supplied by deployment env vars/Helm.
  If a key is always overridden in real deployments, remove it from YAML and
  document it in `.env.example` instead.

## Secret vs. Non-Secret Is Not About Volatility

The only test for whether a value belongs in `Settings` vs. `secrets.py` is
whether it is credential-bearing. A value that changes often, differs per
environment, or needs frequent local overriding is still a plain `Settings`
field — do not move it into secrets on that basis.

For the YAML pattern, use YAML only when the plain `Settings` value is also a
rarely-changing environment baseline. Otherwise use a Pydantic field default
or an env var depending on whether the app can safely choose a default.

Non-secret `Settings` fields are already environment-variable overridable
without any special handling: the source order in `settings-py.md` places
process env vars above `.env` and above YAML, so `APP_PORT=9090` overrides
`app_port` from YAML at runtime with no code change. That override capability
is useful for exceptional cases and local debugging. It should not become the
normal deployment ownership model for YAML-owned keys.

## Deployment-Topology Values Are Not YAML Either

Being non-secret does not automatically make a value YAML-owned. A YAML file
ships baked into the built artifact and is shared by every deployment that
runs that artifact — including every cluster within one environment. If a
value can legitimately differ between two clusters in the same environment,
YAML cannot be its source of truth, no matter how non-secret or how
operational it looks.

**The test:** if this value would ever differ between two clusters in the
same environment, it must be env-var / Helm-only — no exceptions. Only when a
value is identical across every cluster an environment spans does it belong
in `config/{environment}.yaml`.

Fails the test — keep these env-var/Helm-injected, documented in
`.env.example`, never given a value in YAML:

- Cloud region, when one cluster in an environment runs in a different
  physical region than the rest (e.g. `eu-central-1` for one cluster,
  `us-west-2` for the others in the same "production").
- A downstream service URL reached via a different cluster-local hostname
  per cluster.
- Any value a deploy manifest already sets per-cluster today — "identical
  across clusters right now" is not the same guarantee as "identical by
  design"; if nothing stops it from diverging, treat it as topology, not a
  default.

Passes the test — safe to bake into YAML when the value is rarely changed and
intentionally environment-owned: log level, model provider, model IDs, retry
limits, timeouts, queue/bucket/table names, feature flags — when the same
value is correct everywhere an environment's image runs.

### Anti-pattern: a stale YAML value silently masked by env-var overrides

Env vars outrank YAML (see `settings-py.md`), so a wrong or stale value
committed to `config/production.yaml` can sit unnoticed indefinitely as long
as every real deployment injects its own env var for that key — production
traffic is never affected, so nothing alerts anyone. The rot surfaces later
and expensively: a new cluster that forgets to set the env var silently
inherits the wrong YAML default, or someone reads the YAML file to answer
"what does production actually use" and draws the wrong conclusion from a
value that hasn't been live in months. Treat a YAML key that is *always*
overridden in every real deployment as a signal that the key does not belong
in YAML at all — move it to `.env.example` and stop giving it a value in
`config/*.yaml` entirely (relying on the env var or a class default instead).

## Operational Values

Put these in YAML only when they are rarely-changing, environment-owned values
that are identical across every cluster an environment spans:

- App metadata, host, port, and logging behavior.
- Non-secret resource names: queue names, bucket names, table names,
  prefixes, and feature flags.
- Model providers, model IDs, retry limits, timeouts, and token limits.
- Database host, port, name, user, schema, and pool sizes.

Do not put these in YAML:

- Passwords, API keys, OAuth client secrets, JWT signing keys, provider
  access tokens, DSNs that include credentials — these are secrets, see
  above.
- Cloud regions, downstream-service URLs, or any other value that can differ
  between two clusters in the same environment — these are deployment-
  topology values, see "Deployment-Topology Values Are Not YAML Either"
  above.
- Values that Helm, Kubernetes manifests, CI/CD, or another deployment system
  routinely injects as env vars. Document those in `.env.example` instead.

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
