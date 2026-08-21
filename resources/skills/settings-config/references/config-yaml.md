# `config/*.yaml`

Use this reference only when the selected pattern is YAML environment
baselines and you are creating or changing files under the project-root
`config/` directory. If the user has not chosen between YAML baselines and env
vars + Pydantic field defaults, ask before creating YAML files.

## Purpose

YAML files hold committed, non-secret operational baselines for each
environment. They should make runtime behavior auditable without exposing
credentials. YAML is useful when these values rarely change and the repo should
show the intended difference between `local`, `dev`, `staging`, `prod`, or the
project's equivalent environments.

Do not use YAML as a second copy of values that deployment normally provides as
environment variables. In that case, the environment variable is the real
source of truth and the YAML value is likely to become stale or misleading.

## Conventions

- Keep `config/` at the project root, sibling to `src/` and `pyproject.toml`.
- Use one YAML file per environment.
- Standardize new services on `local.yaml`, `dev.yaml`, `staging.yaml`, and
  `prod.yaml`.
- Preserve an established repo's existing environment names (e.g.
  `production.yaml`, or no `dev` tier) rather than renaming them.
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
committed to `config/prod.yaml` can sit unnoticed indefinitely as long
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

## Layered Composition

Use this shape instead of one flat file per environment once there's a
non-secret baseline worth sharing across environments, a per-service file
worth separating from the environment overlay, or both. The design is the
same for a single-service repo and a monorepo with many deployables — a
single-service repo just has one file under `config/services/`; nothing about
the layering itself changes.

Each layer is a deep merge on top of the one before it, key by key — not a
whole-file replacement. `prod.yaml` therefore holds only the keys that differ
from `base.yaml`; any key `prod.yaml` doesn't mention still comes from
`base.yaml` in the final `Settings`.

Layers, lowest precedence first:

1. `config/base.yaml` — shared by every deployable in the repo.
2. `config/{environment}.yaml` — that baseline's environment overlay.
3. `config/services/{service}.yaml` — one deployable's own non-secret file.
4. `config/services/{service}.{environment}.yaml` — optional, only when that
   deployable needs a per-environment override; do not create an empty file
   just to prove an environment needs none.
5. the process environment.

Each layer must exist for every recognized environment, including `local`
(only step 4 is optional). `Settings.settings_customise_sources` should fail
startup naming the missing file rather than silently falling back to a lower
layer — see `settings-py.md`.

**What never belongs in `base.yaml`, even though it is non-secret:**

- Values that are genuinely environment-owned, such as a downstream host —
  one per environment, never shared — because a baseline value here is a
  value every real environment overrides, and the failure mode of a stale
  baseline default is silent misrouting (a call reaching the wrong
  environment's system) rather than a startup failure. Put these in each
  environment's overlay instead, with no default in `base.yaml`.
- A telemetry/observability endpoint, for the same reason: it is a property of
  where the deployable runs, not a property shared across environments.
- Secret *names* (not values — those never belong in YAML at all regardless of
  layer). A shared secret name in `base.yaml` is the same hazard: two
  environments naming the same secret-manager entry resolve identical
  credentials if their execution roles ever share an account. Give each
  non-`local` environment overlay its own complete secret-names block instead.

**Placeholder convention for not-yet-established hosts.** When an
environment's real hostname is not yet known (e.g. a downstream service that
does not exist yet in that environment), use a value under a domain reserved
by RFC 2606, such as `*.invalid`, rather than guessing a plausible-looking
hostname. `.invalid` can never resolve, so a run against an unreplaced
placeholder fails to connect instead of silently succeeding against nothing or
being routed somewhere unintended. Comment the placeholder with what must
happen before the environment is enabled.

`config/base.yaml` (excerpt — shared, no environment-owned host or secret name)

```yaml
downstream_api:
  request_path: /v1/widgets    # identical everywhere; the host is not — see below
  timeout_seconds: 30.0
```

`config/prod.yaml` (excerpt — only the keys that differ from `base.yaml`)

```yaml
downstream_api:
  # PLACEHOLDER — real host not established yet; .invalid (RFC 2606) can
  # never resolve, so an unreplaced value fails to connect instead of
  # silently reaching the wrong system. Replace before enabling this env.
  host: https://replace-me-prod-downstream.invalid

secrets:                                 # names only; scoped per environment
  downstream_api_credential: my-service/prod/downstream-api
```

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

`config/dev.yaml`

```yaml
# Dev non-secret defaults. Do not put secrets in YAML.
environment_name: dev
log_level: DEBUG
app_title: AI Service
app_host: 0.0.0.0
app_port: 8080
model_provider: openai
primary_model_id: replace-me-dev-model-id
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

`config/prod.yaml`

```yaml
# Prod non-secret defaults. Do not put secrets in YAML.
environment_name: prod
log_level: WARNING
app_title: AI Service
app_host: 0.0.0.0
app_port: 8080
model_provider: openai
primary_model_id: replace-me-prod-model-id
request_timeout_seconds: 30
```
