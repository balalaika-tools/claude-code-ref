# `settings.py`

Use this reference when creating or changing `src/<package>/core/settings.py`.

## Purpose

`settings.py` owns typed, non-secret operational config. It should not fetch
remote secrets and should not contain credentials. It may know how to locate
root `config/*.yaml` files and `.env`.

## Source Order

Prefer this priority, highest first:

1. Explicit kwargs for tests.
2. Process environment variables.
3. `.env` for local overrides.
4. `config/{ENVIRONMENT_NAME}.yaml` for committed environment baselines.
5. Class defaults.

Use `CONFIG_DIR` as an escape hatch when the process does not run from inside
the project tree.

## Field Conventions

- Use snake_case Python field names.
- Use SCREAMING_SNAKE_CASE aliases for env vars.
- Include concise `description=` text on fields.
- Use `Literal[...]` for constrained strings.
- Use native `int`, `float`, `bool`, `str`, `list[str]`, etc. for regular
  values.
- Use `Field(...)` only when the app cannot provide a safe default.
- Keep environment-specific values out of Python code.

## Scaffold

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


def _env_name() -> str:
    return os.environ.get("ENVIRONMENT_NAME", "local")


def _find_config_dir() -> Path:
    start = Path.cwd().resolve()
    for candidate in (start, *start.parents):
        config_dir = candidate / "config"
        if config_dir.is_dir():
            return config_dir
    raise FileNotFoundError(
        f"No config/ directory found from {start}. Set CONFIG_DIR explicitly."
    )


def _yaml_path() -> Path:
    config_dir = os.environ.get("CONFIG_DIR")
    base = Path(config_dir) if config_dir else _find_config_dir()
    return base / f"{_env_name()}.yaml"


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
        yaml_file = _yaml_path()
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
