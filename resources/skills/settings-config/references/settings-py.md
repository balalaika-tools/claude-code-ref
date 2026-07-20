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
- Use native `int`, `float`, `bool`, `str`, `list[str]`, etc. for regular
  values.
- Use `Field(...)` only when the app cannot provide a safe default.
- Use `Field(default=...)` only for safe, intentional application defaults.
- In the env vars + Pydantic defaults pattern, keep environment-specific values
  out of Python code and provide them through `.env` locally or deployment env
  vars in staging/production.
- In the YAML pattern, keep only intentionally environment-specific,
  rarely-changing, non-secret baselines in `config/*.yaml`.

## Env Vars + Pydantic Defaults Scaffold

Use this scaffold when the selected pattern is env vars + Pydantic field
defaults. This is the lighter pattern: Python owns safe defaults, `.env` is for
local overrides, and real deployments inject env vars.

```python
"""Application settings: typed, non-secret operational config."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
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
    app_port: int = Field(
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
    request_timeout_seconds: float = Field(
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

from pydantic import Field
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
    app_port: int = Field(
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
    request_timeout_seconds: float = Field(
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
