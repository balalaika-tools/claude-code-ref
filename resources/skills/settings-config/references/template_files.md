# Template Files

Copy these verbatim into your package. Edit only the field declarations.

## Where each file goes

```
<project-root>/
  config/
    local.yaml                ← from "config/local.yaml" section below
    prod.yaml                 ← derived from local.yaml with prod values
  src/
    your_package/
      core/
        __init__.py           ← create if missing
        settings.py           ← from "settings.py" section below
        secrets.py            ← from "secrets.py" section below
```

`config/` lives at the **project root** (sibling of `src/`). `settings.py` and
`secrets.py` live inside `src/your_package/core/`, not at the top of the package.
The relative import `from .secrets import …` works because both files share the
`core` subpackage.

## settings.py

```python
"""Application settings.

Resolution order — highest priority first:

    1. Process environment variables       (CI / runtime overrides)
    2. ``.env`` file                       (local developer overrides)
    3. ``config/{ENVIRONMENT_NAME}.yaml``  (environment baseline)
    4. Defaults declared on :class:`Settings`  (sensible fallbacks)

Secrets are **not** loaded here — see :mod:`secrets`. The top-level
:class:`AppConfig` composes both, and that is what the rest of the app
should depend on.

Requirements
------------
``pydantic-settings>=2.14.1`` with the YAML extra::

    pip install "pydantic-settings[yaml]"

Per-app customisation
---------------------
Copy this file as-is, then edit:
  * The fields on :class:`Settings` (add typed fields with ``Field(alias=...)``).
  * Optionally :func:`_yaml_path` if your config directory layout differs.
The source-priority plumbing in :meth:`Settings.settings_customise_sources`
should not need to change.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from .secrets import Secrets, get_secrets


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _env_name() -> str:
    """Environment name drives which YAML file we load."""
    return os.environ.get("ENVIRONMENT_NAME", "local")


def _find_config_dir() -> Path:
    """Walk up from CWD until we find a ``config/`` directory.

    Works whether the app runs from a source checkout or from a ``.venv``
    install, as long as the process is invoked from somewhere inside the
    consuming project's tree. Override with the ``CONFIG_DIR`` env var.
    """
    start = Path.cwd().resolve()
    for candidate in (start, *start.parents):
        if (candidate / "config").is_dir():
            return candidate / "config"
    raise FileNotFoundError(
        "No `config/` directory found walking up from CWD "
        f"({start}). Set CONFIG_DIR explicitly."
    )


def _yaml_path() -> Path:
    """``config/local.yaml``, ``config/dev.yaml``, ``config/prod.yaml``, …

    Resolution: ``CONFIG_DIR`` env var if set, else walk up from CWD looking
    for a ``config/`` directory.
    """
    config_dir = os.environ.get("CONFIG_DIR")
    base = Path(config_dir) if config_dir else _find_config_dir()
    return base / f"{_env_name()}.yaml"


# ──────────────────────────────────────────────────────────────────────────────
# Settings
# ──────────────────────────────────────────────────────────────────────────────


class Settings(BaseSettings):
    """Non-secret configuration.

    All fields are strongly typed. Prefer ``Literal[...]`` for enumerations,
    native Python types for everything else. Never put secrets here — they
    live in :class:`secrets.Secrets`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        populate_by_name=True,
        extra="ignore",
    )

    # ── General ──────────────────────────────────────────────────────────
    environment_name: Literal["local", "dev", "staging", "prod"] = Field(
        default="local", alias="ENVIRONMENT_NAME",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="WARNING", alias="LOG_LEVEL",
    )

    # ── AWS ──────────────────────────────────────────────────────────────
    aws_default_region: str = Field(default="us-east-1", alias="AWS_DEFAULT_REGION")

    # ── Database (host/port/user are config; password is a secret) ──────
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="postgres", alias="DB_NAME")
    db_user: str = Field(default="app", alias="DB_USER")
    db_pool_min_size: int = Field(default=1, alias="DB_POOL_MIN_SIZE")
    db_pool_max_size: int = Field(default=5, alias="DB_POOL_MAX_SIZE")

    # ── Examples (replace per app) ───────────────────────────────────────
    # s3_bucket: str = Field(default="my-app-bucket", alias="S3_BUCKET")
    # request_timeout_seconds: float = Field(default=30.0, alias="REQUEST_TIMEOUT_SECONDS")
    # feature_flag_x: bool = Field(default=False, alias="FEATURE_FLAG_X")

    # ──────────────────────────────────────────────────────────────────────
    # Source priority wiring.
    # The tuple is returned in priority order (highest first).
    # ──────────────────────────────────────────────────────────────────────
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
        yaml_source = YamlConfigSettingsSource(
            settings_cls,
            yaml_file=yaml_file if yaml_file.exists() else None,
        )
        return (
            init_settings,    # 0. explicit kwargs (tests)
            env_settings,     # 1. process env vars
            dotenv_settings,  # 2. .env file
            yaml_source,      # 3. config/{env}.yaml
            file_secret_settings,  # (unused; kept for completeness)
            # class defaults are implicit (lowest priority)
        )


# ──────────────────────────────────────────────────────────────────────────────
# Composed config (settings + secrets)
# ──────────────────────────────────────────────────────────────────────────────


class AppConfig(BaseModel):
    """The object the rest of the app depends on.

    Inject this — or its pieces — into services rather than reaching for
    :func:`get_settings` deep inside business logic. Easier to test, harder
    to accidentally couple modules to import-time globals.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    settings: Settings
    secrets: Secrets


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide cached :class:`Settings`."""
    return Settings()


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Process-wide cached :class:`AppConfig` (settings + secrets)."""
    return AppConfig(settings=get_settings(), secrets=get_secrets())
```

---

## secrets.py

```python
"""Secrets management.

Secrets are loaded via a pluggable :class:`SecretsProvider` so the same code
path works in local dev (reading from environment variables, populated from
``.env``) and in production (reading from AWS SSM Parameter Store).

The trigger for SSM is the presence of the ``SSM_PARAMETER_PREFIX`` env var.
In local dev it is simply not set; in prod, deployment infra sets it.

Adding a new secret
-------------------
1. Add a typed field to :class:`Secrets` (use ``SecretStr`` so the value is
   masked in logs / reprs / model dumps).
2. Add a line in :func:`load_secrets` populating it from the provider.
3. Document the corresponding env var name **and** SSM path in your runbook.

Per-app customisation
---------------------
Copy this file as-is, then edit only:
  * The :class:`Secrets` fields.
  * The :func:`load_secrets` body to wire each field to a provider key.
The provider plumbing should not need to change.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from functools import lru_cache

from pydantic import BaseModel, ConfigDict, SecretStr


# ──────────────────────────────────────────────────────────────────────────────
# Providers
# ──────────────────────────────────────────────────────────────────────────────


class SecretsProvider(ABC):
    """Resolves a logical secret key (e.g. ``"db/password"``) to its value."""

    @abstractmethod
    def get(self, key: str) -> str:
        """Return the secret stored at ``key``. Raise ``KeyError`` if missing."""


class EnvSecretsProvider(SecretsProvider):
    """Reads secrets from process environment variables.

    Logical keys are translated to env var names:
        ``db/password``      → ``DB_PASSWORD``
        ``third-party/key``  → ``THIRD_PARTY_KEY``

    This is the local-dev provider; values typically originate from ``.env``.
    """

    @staticmethod
    def _to_env_var(key: str) -> str:
        return key.replace("/", "_").replace("-", "_").upper()

    def get(self, key: str) -> str:
        env_var = self._to_env_var(key)
        try:
            return os.environ[env_var]
        except KeyError as exc:
            raise KeyError(
                f"Missing secret: env var {env_var!r} not set "
                f"(logical key {key!r})"
            ) from exc


class SSMSecretsProvider(SecretsProvider):
    """Reads secrets from AWS SSM Parameter Store under a fixed prefix.

    Example
    -------
    >>> p = SSMSecretsProvider(prefix="/myapp/prod")
    >>> p.get("db/password")  # GET /myapp/prod/db/password
    """

    def __init__(self, prefix: str, region_name: str | None = None) -> None:
        # Local import so apps that never use SSM don't pay the boto3 cost.
        import boto3  # noqa: WPS433

        self._client = boto3.client("ssm", region_name=region_name)
        self._prefix = "/" + prefix.strip("/")

    def get(self, key: str) -> str:
        name = f"{self._prefix}/{key.strip('/')}"
        try:
            result = self._client.get_parameter(Name=name, WithDecryption=True)
        except self._client.exceptions.ParameterNotFound as exc:
            raise KeyError(f"SSM parameter not found: {name}") from exc
        return result["Parameter"]["Value"]


def build_secrets_provider() -> SecretsProvider:
    """Pick a provider based on whether SSM is configured.

    * ``SSM_PARAMETER_PREFIX`` set → :class:`SSMSecretsProvider` (prod).
    * ``SSM_PARAMETER_PREFIX`` unset → :class:`EnvSecretsProvider` (local).
    """
    prefix = os.environ.get("SSM_PARAMETER_PREFIX")
    if prefix:
        return SSMSecretsProvider(
            prefix=prefix,
            region_name=os.environ.get("AWS_DEFAULT_REGION"),
        )
    return EnvSecretsProvider()


# ──────────────────────────────────────────────────────────────────────────────
# Typed container
# ──────────────────────────────────────────────────────────────────────────────


class Secrets(BaseModel):
    """All secrets the application needs, strongly typed.

    Every field is a :class:`pydantic.SecretStr` so values are masked in
    ``repr()``, logs, and ``model_dump()`` unless the caller explicitly calls
    ``.get_secret_value()``.
    """

    model_config = ConfigDict(frozen=True)

    # ── Database ─────────────────────────────────────────────────────────
    db_password: SecretStr

    # ── Examples (uncomment / replace per app) ──────────────────────────
    # api_key: SecretStr
    # jwt_signing_key: SecretStr
    # third_party_oauth_client_secret: SecretStr


def load_secrets(provider: SecretsProvider | None = None) -> Secrets:
    """Build a fresh :class:`Secrets` from the given (or default) provider.

    Prefer :func:`get_secrets` in app code; use this directly only in tests
    where you want to inject a custom provider.
    """
    p = provider or build_secrets_provider()
    return Secrets(
        db_password=SecretStr(p.get("db/password")),
        # api_key=SecretStr(p.get("api/key")),
        # jwt_signing_key=SecretStr(p.get("jwt/signing-key")),
    )


@lru_cache(maxsize=1)
def get_secrets() -> Secrets:
    """Return the cached process-wide :class:`Secrets`. Loads on first call."""
    return load_secrets()
```

---

## config/local.yaml

```yaml
# Environment baseline for ENVIRONMENT_NAME=local.
#
# Anything set here overrides the class defaults in settings.py but is itself
# overridden by .env and process env vars.
#
# DO NOT put secrets here — those go through secrets.py (env in local,
# SSM in prod).

environment_name: local
log_level: DEBUG

aws_default_region: us-east-1

db_host: localhost
db_port: 5432
db_name: app_dev
db_user: app
db_pool_min_size: 1
db_pool_max_size: 5
```
