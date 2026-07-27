# `secrets.py`

Use this reference when creating or changing `src/<package>/core/secrets.py`.

## Purpose

`secrets.py` owns sensitive values and secret-provider integration. It should
keep local development easy while making production secret loading explicit.

## General Conventions

- Use `SecretStr` for sensitive strings.
- Keep secret-manager connection details that are not secret in `Settings`.
- Do not put secrets in `config/*.yaml`.
- Do not log raw secret values. Use `.get_secret_value()` only at the boundary
  that needs the actual credential.
- Make missing secrets fail with a message that identifies the env var or
  logical secret key.

## Env-Backed Model

Use this when the user does not name a remote secret manager.

```python
"""Secrets loaded from process env vars and .env for local development."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Secrets(BaseSettings):
    """Sensitive values. SecretStr masks values in reprs and logs."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    database_password: SecretStr = Field(alias="DATABASE_PASSWORD")
    llm_api_key: SecretStr = Field(alias="LLM_API_KEY")


@lru_cache(maxsize=1)
def get_secrets() -> Secrets:
    return Secrets()
```

Use explicit uppercase aliases for every secret env var so `.env.example`,
runtime injection, and Pydantic field names stay synchronized.

## Remote Provider Shape

Use this when the user explicitly names AWS SSM, Azure Key Vault, GCP Secret
Manager, Vault, or another SDK. Rename `RemoteSecretsProvider` for the chosen
backend.

```python
"""Secrets with local .env bypass and optional remote provider."""

from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .settings import Settings, get_settings


class Secrets(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    database_password: SecretStr = Field(alias="DATABASE_PASSWORD")
    llm_api_key: SecretStr = Field(alias="LLM_API_KEY")


class EnvSecrets(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    database_password: SecretStr = Field(alias="DATABASE_PASSWORD")
    llm_api_key: SecretStr = Field(alias="LLM_API_KEY")

    def to_secrets(self) -> Secrets:
        return Secrets(
            database_password=self.database_password,
            llm_api_key=self.llm_api_key,
        )


class SecretsProvider(ABC):
    @abstractmethod
    async def load(self) -> Secrets:
        """Load and validate all application secrets."""


class EnvSecretsProvider(SecretsProvider):
    async def load(self) -> Secrets:
        return EnvSecrets().to_secrets()


class RemoteSecretsProvider(SecretsProvider):
    """Rename for the selected backend, e.g. AwsSsmSecretsProvider."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def load(self) -> Secrets:
        return await asyncio.to_thread(self._load_sync)

    def _load_sync(self) -> Secrets:
        # Replace with SDK calls and wrap raw strings in SecretStr.
        raise NotImplementedError


def _use_local_bypass(settings: Settings) -> bool:
    bypass = os.environ.get("BYPASS_REMOTE_SECRETS", "").lower()
    return settings.environment_name == "local" or bypass in {"1", "true", "yes"}


def build_secrets_provider(settings: Settings | None = None) -> SecretsProvider:
    settings = settings or get_settings()
    if _use_local_bypass(settings):
        return EnvSecretsProvider()
    return RemoteSecretsProvider(settings)


_cached_secrets: Secrets | None = None


async def load_secrets(settings: Settings | None = None) -> Secrets:
    global _cached_secrets
    if _cached_secrets is None:
        provider = build_secrets_provider(settings)
        _cached_secrets = await provider.load()
    return _cached_secrets
```

## Nested Field Grouping

Same rule as `settings.py`: default to a flat `Secrets`/`EnvSecrets` model.
Secret counts are usually small (a handful of API keys and DSNs), so nested
grouping is rarely justified here — reach for it only when a project
genuinely accumulates many secrets across several integrations (e.g. a
distinct API key per LLM provider, per third-party service).

If you do group, use the same mechanics as `settings.py`: plain `BaseModel`
subgroups nested under the single root, `env_nested_delimiter="__"`, and
dropped per-field `alias=` in favor of the delimiter matching
SCREAMING_SNAKE_CASE env var names. In the remote-provider shape, also
update `to_secrets()` to pass the nested groups through; that mapping does
not happen automatically.

Do not create separate independent `BaseSettings`/`BaseModel` secret classes
per integration. That duplicates `model_config` and loses the single point
of validation-at-startup that one root class gives you.

## Provider Notes

- AWS SSM: use `AwsSsmSecretsProvider`; keep prefix and region in `Settings`;
  fetch parameters with decryption.
- Azure Key Vault: use `AzureKeyVaultSecretsProvider`; keep vault URL in
  `Settings`; prefer managed identity in deployed environments.
- GCP Secret Manager: use `GcpSecretManagerSecretsProvider`; keep project ID
  and secret names or paths in `Settings`.
- Vault: use `VaultSecretsProvider`; keep address, mount, and path in
  `Settings`; do not commit tokens.

For native async SDKs, use the SDK directly instead of `asyncio.to_thread`.
