---
name: settings-config
description: >
  Use when creating, extending, or reviewing application configuration for a
  Python/FastAPI AI service settings and secrets modules, YAML application
  baselines under root `config/*.yaml`, `.env.example`,
  Pydantic/pydantic-settings models, SecretStr usage, or secret-manager
  integration with AWS SSM, Azure Key Vault, GCP Secret Manager, Vault, or
  another SDK. Also use when the user calls /settings-config explicitly.
---

# Settings & Secrets

Create a small, typed configuration surface for FastAPI agent services.
Secrets stay out of git, startup fails early when configuration is invalid,
and non-secret settings follow one clear ownership pattern.

## Pattern Decision

Use **YAML application baselines + env deployment contract** by default. Do not
ask the user to choose a non-secret value source when they have expressed no
preference. Use the env-vars + Pydantic-defaults-only pattern only when the user
explicitly says they do not want YAML configuration. This default also applies
to an existing env-only project when the task is a configuration refactor; keep
an existing env-only pattern only when the user explicitly asks to preserve it.

For the default YAML pattern, precedence is always: explicit constructor kwargs,
process environment variables, `.env`, YAML, then class defaults. Process env
and `.env` must always win over YAML; never configure a YAML source above
either environment source.

Field grouping remains a separate choice. When an existing project already
uses flat or nested grouping consistently, preserve it unless the user asks to
migrate. Otherwise ask before choosing because grouping changes the deployment
environment-variable contract.

### Non-secret value source

1. **YAML application baselines + env deployment contract (default)**: committed
   `config/{environment}.yaml` files hold stable, application-owned policy that
   is intentionally different per environment. Deployment-owned topology and
   resource coordinates have no YAML fallback: `.env` supplies them locally
   and the deployment system injects them in real environments. Process env
   vars may still override YAML-owned application settings exceptionally, but
   deployment should not routinely inject a second copy of a YAML-owned key.
2. **Env vars + Pydantic field defaults (explicit opt-out only)**: no YAML
   source. Safe application defaults live directly in `Field(default=...)`;
   values with no safe default use `Field(...)`; `.env` is only a local
   override file; staging/production overrides are provided by real environment
   variables/Helm.

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

Do not ask whether to use YAML unless the user has explicitly raised the
possibility of opting out. Ask only about field grouping when neither the user
nor the existing repository has selected flat or nested grouping.

## Configuration Ownership Contract

Under the default YAML/config baselines plus `.env` pattern, classify every
value by ownership before choosing its source. A value gets one authoritative
home:

1. **Code invariant** — the application has no legitimate operator choice.
   Keep it in code, not in settings merely to make it adjustable.
2. **YAML application policy** — non-secret behavior owned by the application,
   intentionally auditable in git, and valid for every deployment represented
   by that baseline. Examples include retry policy, limits, timeouts, feature
   policy, object-key prefixes generated and interpreted by the application,
   and service identity.
3. **Environment-only deployment contract** — topology or a resource
   coordinate owned by infrastructure/deployment tooling. Examples include
   regions/zones, resource names created by infrastructure, bucket or queue
   names, deployment-specific base URLs, hosts, ports, network addresses,
   runtime identity, and vendor SDK/platform variables. `.env` provides these
   locally; Terraform, Argo CD, Helm, an ECS
   task definition, Kubernetes, or the selected deployment system injects them
   outside local development. Required values have no YAML or Python fallback.
4. **Secret provider boundary** — credential-bearing values and the stable
   logical variables used to locate or carry them. These belong in
   `secrets.py`, never in YAML or ordinary renderable `Settings`.

GenAI runtime selection belongs to the environment-only deployment contract,
not to YAML application policy. Treat model IDs, provider deployment names,
model/provider base URLs or endpoints, regions, projects, resource names, and
deployment-owned API versions as required env vars with no YAML or Python
fallback. This remains true when every current environment happens to use the
same model: the deployment must choose the runtime model explicitly. Keep
application-owned GenAI behavior in YAML instead, such as retry/backoff policy,
timeouts, token limits, confidence thresholds, prompt/evidence versions, and
feature/safety policy. A provider enum may remain YAML only when it selects an
application-supported integration rather than a deployment resource.

Do not duplicate an env-only value into YAML as documentation. A stale fallback
can make a misconfigured deployment appear valid. Document the runtime contract
in `.env.example` and deployment documentation instead.

Resource names and application namespaces are distinct. An infrastructure-owned
bucket name belongs to the environment contract; an object-key prefix created,
validated, and consumed by application code remains YAML policy (or a code
invariant when operators have no reason to change it).

Network location and API contract are also distinct. A service host, base URL,
port, or deployment-local address is topology and therefore env-only. A relative
API route/path such as `/api/v1/items` describes how application code speaks to
that service; keep it in YAML when it is configurable/auditable application
policy, or in code when it is a true invariant. Do not move API paths to env
merely because they are joined to an env-owned base URL at runtime.

Resolve and validate the complete non-secret configuration first, select the
secret provider from the validated environment/mode, resolve and validate every
secret, and only then construct SDK clients or perform external I/O.

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

In a multi-service repository (a uv workspace with `services/*`), every deployable
service directory owns its own `.env.example` describing that service's complete
runtime contract, and the repository-root `.env.example` documents only what the
deployment tool (Compose, Helm, Terraform) consumes and passes through. Add a
contract test per service that parses the service file and compares each section
with the settings class, so the file cannot drift. See `references/env-example.md`,
"Per-Service Files and Section Taxonomy".

For the YAML application-baseline pattern, also include:

```text
<project-root>/
  config/
    local.yaml
    staging.yaml
    production.yaml
```

Keep existing environment names when a repo already uses them, such as `dev`
or `prod`.

## Reference Routing

Load only the reference needed for the file you are creating or changing:

- `references/settings-py.md`: `core/settings.py`, `Settings`, pattern-specific
  source ordering, Pydantic field conventions, and startup validation.
- `references/secrets-py.md`: `core/secrets.py`, `SecretStr`, stable logical
  secret-source variables, provider routing, payload validation, async loading,
  and local resolution.
- `references/config-yaml.md`: root `config/*.yaml`, environment baselines,
  YAML key conventions, and non-secret operational parameters.
- `references/env-example.md`: `.env.example`, required deployment-contract
  variables, local secret sources, useful overrides, advanced overrides, and
  remote-provider examples.

For the default YAML environment-baseline pattern, read all four references.
Only when the user explicitly opts out of YAML, read
`settings-py.md`, `secrets-py.md`, and `env-example.md`.
For a small field addition, read only the affected reference files.

## Core Conventions

- For the YAML application-baseline pattern, put non-secret operational
  parameters in `config/{environment}.yaml` only when the value rarely changes,
  is application-owned, and is correct for every deployment represented by the
  baseline. Do not put a key in YAML when deployment normally injects the same
  key as an env var; that makes YAML stale documentation with runtime side
  effects. See `references/config-yaml.md`.
- For the env vars + Pydantic defaults pattern, put safe application defaults
  directly on the Pydantic fields with `Field(default=...)`. Do not create
  defaults for values that the app cannot safely choose; use `Field(...)` and
  document the required env var in `.env.example`.
- Deployment-owned values, and any value that legitimately differs across
  environments or deployments (region/zone, a downstream service base URL or
  host reached through a deployment-local address, etc.), belong in
  `.env.example` / env vars and are injected in real deployments. The test: if
  this value would ever differ between two deployments represented by the same
  environment baseline, it must be env-only.
- A value created, named, or wired by infrastructure tooling is env-only even
  when it happens to be identical across current deployments. Do not encode an
  infrastructure output as an application baseline.
- Always classify GenAI runtime coordinates as deployment-owned: model IDs,
  provider deployment names, model endpoints/base URLs, regions/projects,
  resource identifiers, and deployment-owned API versions. Add them to the
  typed settings contract and `.env.example`, with no YAML or Python fallback.
- Put secrets in `secrets.py`, never in YAML and never as `Settings` fields.
- Always create or update `.env.example`. In a multi-service repository, create
  or update the service-local `services/<name>/.env.example` as well; the root
  file never replaces it.
- Treat the environment selector `ENVIRONMENT_NAME` as an environment-only,
  required deployment input under both configuration patterns. Declare it with
  `Field(...)`; never give it a YAML or Python default. List it first in the
  REQUIRED section of every service `.env.example`.
- Structure every service `.env.example` as exactly three sections: REQUIRED
  (deployment contract with no default; startup fails naming the variable; the
  environment selector `ENVIRONMENT_NAME` is always required and always listed
  first), OVERRIDABLE (every YAML policy key, commented out, with its baseline
  value), and OPTIONAL (the rare runtime-only knobs such as an instance id, a
  config-dir escape hatch, or a diagnostic switch). A value with a safe default
  is YAML policy, not an optional variable.
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
the remote calls with `asyncio.to_thread`. Local development must still resolve
through `.env` without contacting the remote provider.

When local and deployed environments resolve the same logical secrets, prefer
one stable, neutrally named source variable per logical secret across all
environments. The selected provider determines how to interpret its value:

- with a direct/env-backed provider, the variable carries the secret payload
  itself (normally local, but also valid when a deployment system injects final
  secret values);
- with a remote provider, the same variable carries that provider's locator,
  identifier, path, or URI, and the provider fetches the payload.

The payload shape belongs to the logical secret, not to the backend. A
multi-field credential may use a JSON object such as
`{"username":"replace-me","password":"replace-me"}` locally and the same
object schema in the remote store. A scalar API key or token remains a plain
string locally and a plain-string payload remotely; do not wrap it in JSON just
to imitate a structured secret. Read source variables inside the secret
bootstrap boundary, choose the provider only after environment/provider-mode
validation, and mask payload values immediately. See `references/secrets-py.md`
for the full contract and failure rules.

## Change Checklist

When adding a setting under the YAML application-baseline pattern, classify its
ownership first. For YAML policy, update `Settings` and every relevant
`config/*.yaml`; add it to `.env.example` only when it is a useful override.
For an env-only deployment input, update `Settings` and `.env.example` but add
no YAML or Python fallback.

Only after an explicit YAML opt-out, when adding a setting under the env vars +
Pydantic defaults pattern, update `Settings` and `.env.example` when the setting
is required or commonly overridden. Add a `Field(default=...)` only when the
default is safe and intentional.

When adding a secret, update the secrets model, the env-backed loader, any
selected remote provider, and `.env.example`.

Test at least the ownership boundaries affected by the change: missing required
env-only input, process-env precedence, absence of env-only keys and secret
sources from YAML, local versus deployed provider selection, scalar or
structured payload validation, redaction in rendering/errors, and the guarantee
that complete settings and secrets resolve before any external client is used.
