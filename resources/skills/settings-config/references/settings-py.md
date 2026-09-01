# `settings.py`

Use this reference when creating or changing `src/<package>/core/settings.py`.

## Purpose

`settings.py` owns typed, non-secret operational config. It should not fetch
remote secrets and should not contain credentials. By default it reads YAML
application baselines and knows how to locate root `config/*.yaml`, while env
and `.env` sources retain higher precedence. It uses env vars plus Pydantic
field defaults without YAML only after an explicit user opt-out.

## Source Order

Use the YAML environment-baseline source order unless the user explicitly opts
out of YAML configuration.

Env vars + Pydantic field defaults (explicit YAML opt-out only):

1. Explicit kwargs for tests.
2. Process environment variables.
3. `.env` for local overrides.
4. Class defaults.

YAML environment baselines (default):

1. Explicit kwargs for tests.
2. Process environment variables.
3. `.env` for local overrides.
4. `config/{ENVIRONMENT_NAME}.yaml` for committed environment baselines.
5. Class defaults.

Do not ask the user to choose when they have expressed no preference: use YAML.
Use the env-only source order only after an explicit request not to use YAML.

## YAML Discovery

Only add YAML discovery when using the YAML environment-baseline pattern.
Resolve `config/` by walking upward from `settings.py`'s actual installed file
path until a real ancestor-owned `config/` directory is found. Do not hard-code
`Path(__file__).resolve().parents[N] / "config"`: that only works for editable
source-tree installs. Non-editable Docker installs commonly put the module
under `.venv/.../site-packages` while `config/` is copied to the app root, so a
fixed parent index can point inside `.venv` and miss the deployed YAML files.

Do not walk upward from the process's working directory. The CWD is launch
context, not package layout. A narrow service-specific env override such as
`MY_SERVICE_CONFIG_DIR` is acceptable as an emergency/operator escape hatch,
but normal runtime discovery should work without it.

## Field Conventions

- Use snake_case Python field names.
- Use SCREAMING_SNAKE_CASE aliases for env vars.
- In the YAML pattern, set `populate_by_name=True` whenever fields have env-var
  aliases but `config/*.yaml` uses snake_case field names. Without it, YAML
  values for aliased fields can be ignored as extras and the app may silently
  use Python defaults.
- Do not assume `BaseSettings(env_file=".env")` exports values to
  `os.environ`. It only reads and merges sources into the settings instance.
- For SDKs that normally read their own env vars, either pass the resolved
  settings value explicitly to the SDK constructor or create a narrow bootstrap
  helper that writes selected values to `os.environ` before SDK initialization.
  Prefer explicit constructor arguments whenever the SDK supports them.
- Include concise `description=` text on fields.
- Use `Literal[...]` for constrained strings.
- Prefer a specific Pydantic type over bare `str`/`int`/`float` whenever the
  field's value maps onto one; see "Preferred Pydantic Types" below.
- Use `Field(...)` only when the app cannot provide a safe default.
- Use `Field(default=...)` only for safe, intentional application defaults.
- In the env vars + Pydantic defaults pattern, keep environment-specific values
  out of Python code and provide them through `.env` locally or deployment env
  vars in staging/production.
- In the YAML pattern, keep only intentionally environment-specific,
  rarely-changing, application-owned non-secret policy in `config/*.yaml`.

## Environment-Only Runtime Contract

Under the YAML application-baseline pattern, deployment topology is still
env-only. Add typed required `Settings` fields for non-secret runtime inputs
that the application consumes, but do not give those fields a YAML value or
Python default. This includes infrastructure-owned resource names,
deployment-specific base URLs, hosts, ports, network addresses, regions or
zones, and runtime identity. `.env` satisfies them locally; the selected
deployment system injects them elsewhere.

GenAI runtime coordinates follow the same rule even when they are not created
by Terraform: model IDs, provider deployment names, model/provider endpoints
or base URLs, regions/projects/resource identifiers, and deployment-owned API
versions are required env inputs with no YAML or class default. Keep retries,
timeouts, token limits, prompt/evidence versions, thresholds, and feature
policy in YAML. With nested settings, derive the env name from the actual field
path (for example, `classification.model.model_id` becomes
`CLASSIFICATION__MODEL__MODEL_ID`); do not shorten it to an invented alias.

Do not classify a relative API path as topology. Paths such as token, resource,
or versioned API routes are integration behavior: keep them in YAML when they
are application-owned configuration, or in code when they are invariants. A
client normally combines an env-owned base URL with a YAML/code-owned relative
path after both have validated.

Keep the repository's existing field grouping. A nested repository may expose
`WORKBOOK_STORE__BUCKET_NAME`; a flat repository may expose
`WORKBOOK_STORE_BUCKET_NAME`. Do not flatten or regroup unrelated settings as
part of moving one value to the runtime contract.

Validate cross-field invariants at startup. When two platform variables are
aliases or compatibility forms for one concept, require them to agree rather
than silently choosing one. When an SDK consumes its own environment variable,
validate the application-facing contract before SDK initialization; pass the
validated value explicitly when supported, otherwise leave the SDK variable in
the process environment and use one narrow bootstrap check. Never create a
service-specific override for a value that the chosen architecture requires all
clients to share.

Do not put secret-source variables on `Settings` when the same variable carries
a secret payload locally and a remote locator when deployed. Read and mask it
inside `secrets.py`; see `secrets-py.md`.

## Preferred Pydantic Types

Env vars and `.env`/YAML values arrive as strings; pydantic-settings parses
them into the field's declared type automatically, including URLs, UUIDs,
dates, and `ByteSize`. Choose the narrowest type below before falling back to
a bare `str`/`int`/`float` — do not hand-roll validation in code that
Pydantic already gives you for free on the field.

| Value shape | Type | Examples |
| --- | --- | --- |
| Must be `> 0` / `>= 0` | `PositiveInt`, `NonNegativeInt` | ports, retry counts, pool sizes, page sizes |
| Must be `> 0.0` / `>= 0.0` | `PositiveFloat`, `NonNegativeFloat` | timeouts, backoff multipliers, ratios |
| Must reject NaN/inf | `FiniteFloat` | any float used in arithmetic or comparisons |
| HTTP(S) base or complete callback URL | `AnyHttpUrl` (or stricter `HttpUrl`) | downstream base URL, webhook target |
| Non-HTTP URL/DSN without credentials | `AnyUrl` | `postgresql://`, `redis://` connection strings |
| Filesystem location | `Path` | log directory, mount point, cert/key file path |
| Opaque identifier | `UUID` (or `UUID4` when the version is guaranteed) | tenant ID, request ID, external resource ID |
| Exact decimal quantity | `Decimal` | money, billing units — anything where float rounding is a bug |
| Calendar date | `date` | billing cycle date, effective date |
| Timestamp | `datetime`, `AwareDatetime` | schedules, expirations — use `AwareDatetime` whenever a naive value would be a bug |
| Email address | `EmailStr` | operator/notification address |
| Human-readable size | `ByteSize` | memory/disk/payload limits (`"512MB"`) instead of a raw byte count |
| Fixed set of named values used elsewhere as `.name`/`.value` | `Enum` subclass | only when code needs named members, not just string comparison |
| Fixed set of values compared only as strings | `Literal[...]` | environments, log levels, providers, modes (already covered above) |
| Coercion itself would hide a bug | `StrictBool`, `StrictInt`, `StrictStr` | reach for these only when implicit coercion (e.g. `"false"` parsing truthy) is the specific failure to guard against, not as a default habit |
| No narrower type applies | `str`, `bool`, `list[str]`, etc. | free-text titles, flags, tag lists |

`SecretStr`/`SecretBytes` never belong on `Settings` — see `secrets-py.md`.

## Nested Field Grouping

Use this section once the Field Grouping decision (see `SKILL.md`) has landed
on nested — either the user asked for it, or an existing project already
groups fields this way. This is a namespacing change, not a functional split:
keep one `Settings(BaseSettings)` root and one cached `get_settings()`, and
group related fields into plain `BaseModel` subgroups nested under it.

Do not create multiple independent `BaseSettings` classes to categorize
config (e.g. a separate `DatabaseSettings(BaseSettings)` and
`LLMSettings(BaseSettings)`). Each `BaseSettings` subclass re-runs the full
source-resolution stack (env vars, `.env`, YAML discovery,
`settings_customise_sources`) independently, which duplicates `model_config`
and drifts out of sync over time. A nested `BaseModel` group under the single
root avoids this: it is still resolved by the root's one source order.

Keep environment-selection fields (`environment_name`, `log_level`) at the
top level, ungrouped. `environment_name` is required with no default in every
pattern; resolve it from the process environment or `.env` before choosing the
YAML file, and fail startup naming `ENVIRONMENT_NAME` when it is absent. In the YAML pattern, `_env_name()` reads
`ENVIRONMENT_NAME` directly from `env_settings`/`dotenv_settings` before
`Settings` is constructed, so it must stay a flat, unaliased top-level key.

Before adopting nested groups, account for these mechanics:

- Set `env_nested_delimiter="__"` in `model_config`. Env vars become
  `SERVER__APP_PORT`, `MODEL__PRIMARY_MODEL_ID` instead of flat `APP_PORT`,
  `PRIMARY_MODEL_ID`. This changes every deployment env var and
  `.env.example` entry for grouped fields; treat it as a breaking change, not
  a transparent refactor.
- Per-field `alias=` on nested model fields does not compose cleanly with
  `env_nested_delimiter`. On grouped fields, drop the individual `alias=`
  and let the delimiter plus the SCREAMING_SNAKE_CASE-matching field name
  resolve the env var instead. Keep `case_sensitive=True` so the nested path
  matches exactly.
- In the YAML pattern, nested YAML maps onto nested models directly
  (`server: {app_port: ...}` onto `ServerSettings`), but alias/
  `populate_by_name` precedence gets harder to verify with nesting. Test the
  YAML load path explicitly for every grouped field, not just the flat ones.

### Nested Grouping Scaffold

```python
from pydantic import BaseModel, Field, PositiveFloat, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerSettings(BaseModel):
    """HTTP server bind config."""

    app_title: str = Field(default="AI Service", description="FastAPI application title.")
    app_host: str = Field(default="0.0.0.0", description="Server bind host.")
    app_port: PositiveInt = Field(default=8080, description="Server bind port.")


class ModelSettings(BaseModel):
    """LLM provider config."""

    model_provider: Literal["openai", "bedrock", "bedrock_converse", "azure-openai"] = Field(
        default="openai", description="Primary LLM provider."
    )
    primary_model_id: str = Field(description="Primary model used by the main agent.")
    request_timeout_seconds: PositiveFloat = Field(
        default=30.0, description="Default outbound request timeout."
    )


class Settings(BaseSettings):
    """Non-secret settings. Secrets belong in core/secrets.py."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_nested_delimiter="__",
    )

    environment_name: EnvironmentName = Field(default="local", alias="ENVIRONMENT_NAME")
    log_level: LogLevel = Field(default="INFO", alias="LOG_LEVEL")

    server: ServerSettings = Field(default_factory=ServerSettings)
    model: ModelSettings = Field(default_factory=ModelSettings)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
```

Usage: `settings.server.app_port`, `settings.model.primary_model_id`.

## Env Vars + Pydantic Defaults Scaffold

Use this scaffold only when the user explicitly opts out of YAML. Python then
owns safe defaults, `.env` is for local overrides, and real deployments inject
env vars.

```python
"""Application settings: typed, non-secret operational config."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PositiveFloat, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict

EnvironmentName = Literal["local", "staging", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Non-secret settings. Secrets belong in core/secrets.py."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    environment_name: EnvironmentName = Field(
        default="local",
        alias="ENVIRONMENT_NAME",
        description="Deployment environment name for logging/telemetry.",
    )
    log_level: LogLevel = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="Application log level.",
    )
    app_title: str = Field(
        default="AI Service",
        alias="APP_TITLE",
        description="FastAPI application title.",
    )
    app_host: str = Field(
        default="0.0.0.0",
        alias="APP_HOST",
        description="Server bind host.",
    )
    app_port: PositiveInt = Field(
        default=8080,
        alias="APP_PORT",
        description="Server bind port.",
    )
    model_provider: Literal[
        "openai",
        "bedrock",
        "bedrock_converse",
        "azure-openai",
    ] = Field(
        default="openai",
        alias="MODEL_PROVIDER",
        description="Primary LLM provider.",
    )
    primary_model_id: str = Field(
        alias="PRIMARY_MODEL_ID",
        description="Primary model used by the main agent.",
    )
    request_timeout_seconds: PositiveFloat = Field(
        default=30.0,
        alias="REQUEST_TIMEOUT_SECONDS",
        description="Default outbound request timeout.",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
```

## YAML Environment-Baseline Scaffold

Use this scaffold by default. YAML should own values that rarely change, are
intentionally environment-specific, and are not normally overridden by
deployment env vars.

```python
"""Application settings: typed, non-secret operational config."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PositiveFloat, PositiveInt
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


def _discover_config_dir(module_file: Path) -> Path | None:
    """Find the nearest ancestor-owned `config` directory.

    Source-tree runs place `config` next to `src`. Non-editable Docker installs
    can place this module under `.venv/.../site-packages` while copying
    `config` to the app root. Walking upward from the module path covers both
    layouts without depending on the process working directory.
    """
    for parent in module_file.resolve().parents:
        candidate = parent / "config"
        if candidate.is_dir():
            return candidate
    return None


_CONFIG_DIR = _discover_config_dir(Path(__file__)) or (Path.cwd() / "config")


def _config_dir() -> Path:
    override = os.environ.get("MY_SERVICE_CONFIG_DIR")
    return Path(override) if override else _CONFIG_DIR


def _env_name(
    env_settings: PydanticBaseSettingsSource,
    dotenv_settings: PydanticBaseSettingsSource,
) -> str:
    """ENVIRONMENT_NAME, checked in the same priority order as the rest of
    Settings. Needed before Settings is constructed, to pick which
    config/{ENVIRONMENT_NAME}.yaml to load. Reuses the already-configured
    env_settings/dotenv_settings sources instead of hand-parsing `.env`, so
    this stays consistent with whatever `.env` file is actually in effect
    (including `_env_file` overrides in tests).
    """
    return (
        env_settings().get("ENVIRONMENT_NAME")
        or dotenv_settings().get("ENVIRONMENT_NAME")
        or "local"
    )


class Settings(BaseSettings):
    """Non-secret settings. Secrets belong in core/secrets.py."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        populate_by_name=True,
        extra="ignore",
    )

    environment_name: Literal["local", "staging", "production"] = Field(
        default="local",
        alias="ENVIRONMENT_NAME",
        description="Deployment environment; selects config/{environment}.yaml.",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="Application log level.",
    )
    app_title: str = Field(
        default="AI Service",
        alias="APP_TITLE",
        description="FastAPI application title.",
    )
    app_host: str = Field(
        default="0.0.0.0",
        alias="APP_HOST",
        description="Local server bind host.",
    )
    app_port: PositiveInt = Field(
        default=8080,
        alias="APP_PORT",
        description="Local server bind port.",
    )
    model_provider: Literal[
        "openai",
        "bedrock",
        "bedrock_converse",
        "azure-openai",
    ] = Field(
        default="openai",
        alias="MODEL_PROVIDER",
        description="Primary LLM provider.",
    )
    primary_model_id: str = Field(
        alias="PRIMARY_MODEL_ID",
        description="Runtime-selected primary model; required from env.",
    )
    request_timeout_seconds: PositiveFloat = Field(
        default=30.0,
        alias="REQUEST_TIMEOUT_SECONDS",
        description="Default outbound request timeout.",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        yaml_file = _config_dir() / f"{_env_name(env_settings, dotenv_settings)}.yaml"
        if not yaml_file.exists():
            raise FileNotFoundError(
                f"Missing config file: {yaml_file}. "
                "Create the matching config/{ENVIRONMENT_NAME}.yaml file."
            )
        yaml_source = YamlConfigSettingsSource(settings_cls, yaml_file=yaml_file)
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            yaml_source,
            file_secret_settings,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

When adapting this to an existing repo, keep its current environment enum and
project-specific settings.
