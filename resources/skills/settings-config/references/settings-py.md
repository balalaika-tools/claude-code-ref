# `settings.py`

Use this reference when creating or changing `src/<package>/core/settings.py`.

## Purpose

`settings.py` owns typed, non-secret operational config. It should not fetch
remote secrets and should not contain credentials. It either reads values from
env vars plus Pydantic field defaults, or it additionally knows how to locate
root `config/*.yaml` files when the user has chosen committed environment
baselines.

## Source Order

Use the source order for the selected pattern.

Env vars + Pydantic field defaults:

1. Explicit kwargs for tests.
2. Process environment variables.
3. `.env` for local overrides.
4. Class defaults.

YAML environment baselines:

1. Explicit kwargs for tests.
2. Process environment variables.
3. `.env` for local overrides.
4. `config/{ENVIRONMENT_NAME}.yaml` for committed environment baselines.
5. Class defaults.

If the user has not chosen between these patterns, ask before implementing.

## Environment Enum

Define the environment `Literal` (or `Enum`) with all four tiers the project
actually deploys to — typically `Literal["local", "dev", "staging", "prod"]`.
Dropping a tier the project genuinely has (most commonly `dev`, since it's
easy to reach for `local`/`staging`/`prod` and forget the tier in between) is
a silent gap: nothing fails until someone deploys to the missing environment
and every value falls back to whatever the *next* recognized environment
resolves to. Cross-check the enum against `config/` (every environment must
have a file) and against the deployment pipeline's actual environment names
before treating the enum as final.

Resolve the environment explicitly and fail loudly when it is missing or
unrecognized — never default silently to `"local"` in this resolution step
(a `Field(default="local", ...)` on `Settings` itself is fine; that only
matters for local dev runs with no env var set at all, and still surfaces
immediately since nothing loads without it):

```python
def resolve_environment() -> str:
    raw = os.environ.get("ENVIRONMENT_NAME")
    recognised = ", ".join(get_args(EnvironmentName))
    if not raw:
        raise ConfigurationError(f"ENVIRONMENT_NAME is not set. Set it to one of: {recognised}.")
    if raw not in get_args(EnvironmentName):
        raise ConfigurationError(
            f"ENVIRONMENT_NAME={raw!r} is not recognised. Recognised values: {recognised}."
        )
    return raw
```

An environment guessed wrong is not a cosmetic bug: it points a run's YAML
overlay, and any environment-selected secrets provider (see `secrets-py.md`),
at the wrong tier's resources.

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
  vars in dev/staging/prod.
- In the YAML pattern, keep only intentionally environment-specific,
  rarely-changing, non-secret baselines in `config/*.yaml`.

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
| HTTP(S) endpoint | `AnyHttpUrl` (or stricter `HttpUrl`) | downstream service URL, webhook target |
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
top level, ungrouped. In the YAML pattern, `_env_name()` reads
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
- Set `model_config = ConfigDict(extra="forbid")` on every nested `BaseModel`
  group too, not just on the root `Settings`. The root's `extra="forbid"`
  only catches unknown top-level keys; a typo inside a nested map (`server:
  {app_prot: 8080}`) is only caught if the group itself forbids extras.

### Nested Grouping Scaffold

```python
from pydantic import BaseModel, ConfigDict, Field, PositiveFloat, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerSettings(BaseModel):
    """HTTP server bind config."""

    # extra="forbid" on every nested group, same as the root: a misspelled
    # key inside `server:` should fail startup, not sit ignored beside the
    # field it was meant to override.
    model_config = ConfigDict(extra="forbid")

    app_title: str = Field(default="AI Service", description="FastAPI application title.")
    app_host: str = Field(default="0.0.0.0", description="Server bind host.")
    app_port: PositiveInt = Field(default=8080, description="Server bind port.")


class ModelSettings(BaseModel):
    """LLM provider config."""

    model_config = ConfigDict(extra="forbid")

    model_provider: Literal[
        "openai", "bedrock", "bedrock_converse", "azure-openai"
    ] = Field(default="openai", description="Primary LLM provider.")
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
        extra="forbid",
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

Use this scaffold when the selected pattern is env vars + Pydantic field
defaults. This is the lighter pattern: Python owns safe defaults, `.env` is for
local overrides, and real deployments inject env vars.

```python
"""Application settings: typed, non-secret operational config."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PositiveFloat, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict

EnvironmentName = Literal["local", "dev", "staging", "prod"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Non-secret settings. Secrets belong in core/secrets.py."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="forbid",
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

Use this scaffold only when the selected pattern is committed YAML environment
baselines. YAML should own values that rarely change, are intentionally
environment-specific, and are not normally overridden by deployment env vars.

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
        extra="forbid",
    )

    environment_name: Literal["local", "dev", "staging", "prod"] = Field(
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
        default="replace-me-model-id",
        alias="PRIMARY_MODEL_ID",
        description="Primary model used by the main agent.",
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

## Layered YAML Scaffold

Use this variant of `settings_customise_sources` when the layout is layered
`config/base.yaml` + `config/{environment}.yaml` + per-service file (see
`config-yaml.md`, "Layered Composition"). The design is identical whether the
repo has one deployable or many — a single-service repo just has one entry
under `config/services/`.

Extend the single-file scaffold's `settings_customise_sources` to resolve a
list of layers instead of one file, requiring each and merging first-wins
(most specific first):

```python
required = [
    config_dir / "base.yaml",
    config_dir / f"{environment}.yaml",
    config_dir / "services" / f"{SERVICE_NAME}.yaml",
]
for path in required:
    if not path.is_file():
        raise ConfigurationError(f"Missing configuration file: {path}")

# Optional: a per-service, per-environment override. Don't require an empty
# file to prove an environment needs none.
optional = config_dir / "services" / f"{SERVICE_NAME}.{environment}.yaml"
layers = required + ([optional] if optional.is_file() else [])

yaml_sources = tuple(
    YamlConfigSettingsSource(settings_cls, yaml_file=path)
    for path in reversed(layers)  # most specific first, so it wins the merge
)
return (init_settings, env_settings, *yaml_sources)
```

Pair it with a `secrets` field that names the secrets this deployable needs
(never their values) and is required for every environment except `local`,
checked once after the model is built rather than left for whatever reads
`secrets` later to notice it's missing:

```python
class SecretNames(BaseModel):
    model_config = ConfigDict(extra="forbid")
    database_dsn: str = Field(description="Name/path of the secret holding the DB DSN.")


class Settings(BaseSettings):
    ...
    secrets: SecretNames | None = None  # None only for `local` — see secrets-py.md

    @model_validator(mode="after")
    def _secrets_required_outside_local(self) -> "Settings":
        if self.environment_name != "local" and self.secrets is None:
            raise ValueError(f"secrets: is required outside local (got {self.environment_name!r}).")
        return self
```
