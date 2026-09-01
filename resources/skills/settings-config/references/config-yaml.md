# `config/*.yaml`

Use this reference by default when creating or changing application
configuration and files under the project-root `config/` directory. Skip YAML
only when the user explicitly says they do not want YAML configuration.

## Purpose

YAML files hold committed, non-secret application-policy baselines for each
environment. They should make runtime behavior auditable without exposing
credentials or duplicating deployment topology. YAML is useful when these
values rarely change and the repo should show the intended behavioral
difference between `local`, `staging`, `production`, or the project's
equivalent environments.

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
- Include every non-secret application setting that rarely changes and is
  intentionally owned by the application baseline.
- Never include passwords, API keys, tokens, signing keys, credential-bearing
  DSNs, or private keys.
- Do not include keys that are normally supplied by deployment env vars.
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

**The tests:** if this value would ever differ between two clusters in the
same environment, or if infrastructure/deployment tooling creates, names, or
wires it, it must be env-only — no exceptions. Only application-owned policy
that is identical across every deployment represented by a baseline belongs in
`config/{environment}.yaml`.

Fails the test — keep these deployment-injected env vars, documented in
`.env.example`, never given a value in YAML:

- Cloud region, when one cluster in an environment runs in a different
  physical region than the rest (e.g. `eu-central-1` for one cluster,
  `us-west-2` for the others in the same "production").
- A downstream service base URL or host reached via a different deployment-local
  network address.
- Any value a deploy manifest already sets per-cluster today — "identical
  across clusters right now" is not the same guarantee as "identical by
  design"; if nothing stops it from diverging, treat it as topology, not a
  default.
- Resource identifiers emitted by infrastructure, such as bucket, queue,
  topic, cluster, or task/service names. Their current stability does not make
  the application their owner.

Passes the test — safe to bake into YAML when the value is rarely changed and
application-owned: log level, an application-supported provider enum, retry
limits, timeouts, token limits, prompt/evidence versions,
application-generated object-key prefixes, relative API routes/paths, and
feature policy — when the same value is correct everywhere an environment's
image runs. Model IDs and provider deployment names never pass this test; they
are explicit runtime selection and remain env-only.

Do not confuse a resource with the namespace the application owns inside it.
For example, a deployment-created bucket name is env-only, while a stable key
prefix that application code creates, validates, and consumes is YAML policy
(or a code invariant when operators never need to change it).

Likewise, do not confuse a service's network location with its API contract. A
host, port, base URL, or deployment-local address is env-only. A relative route
such as `/api/v1/items` is application-owned YAML policy when it is meant to be
auditable/configurable, or a code invariant when it is not. Joining a base URL
and a relative path at runtime does not give both values the same owner.

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

Put these in YAML only when they are rarely-changing, application-owned values
that are identical across every deployment represented by the baseline:

- App metadata, safe application bind defaults, and logging behavior.
- Application-owned namespaces, prefixes, API routes/paths, and feature policy.
- Application-supported provider enums, retry limits, timeouts, token limits,
  prompt/evidence versions, and model feature policy.
- Database pool, timeout, and retry policy.

Do not put these in YAML:

- Passwords, API keys, OAuth client secrets, JWT signing keys, provider
  access tokens, DSNs that include credentials — these are secrets, see
  above.
- Cloud regions, downstream-service base URLs/hosts, or any other value that can
  differ between two deployments represented by one environment baseline —
  these are deployment-topology values, see "Deployment-Topology Values Are
  Not YAML Either" above.
- Database hosts, ports, resource names, and other coordinates supplied by the
  deployment system.
- Resource names and identifiers supplied by infrastructure/deployment tooling,
  even when they are non-secret and currently stable.
- GenAI runtime coordinates: model IDs, provider deployment names,
  model/provider endpoints or base URLs, regions/projects/resource names, and
  deployment-owned API versions.
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
request_timeout_seconds: 30
```
