# `secrets.py`

Use this reference when creating or changing `src/<package>/core/secrets.py`.

## Purpose

`secrets.py` owns sensitive values and secret-provider integration. It should
keep local development easy while making production secret loading explicit.

## General Conventions

- Use `SecretStr` for sensitive strings.
- Keep backend-level connection details that are not secret, such as a vault
  URL or project identifier, in `Settings` when the application consumes them.
  Keep per-secret source variables inside the secret bootstrap boundary when
  those same variables carry secret payloads locally.
- Do not put secrets in `config/*.yaml`.
- Do not log raw secret values. Use `.get_secret_value()` only at the boundary
  that needs the actual credential.
- Make missing secrets fail with a message that identifies the env var or
  logical secret key.

## Stable Logical Secret-Source Variables

When runtimes need the same logical secrets, prefer one neutral
environment-variable name per logical secret in every environment. The
provider selected from the already validated environment/provider mode
determines what the variable contains. A common local/remote policy looks like:

```text
ENVIRONMENT_NAME=local       DATABASE_SECRET=<local payload>
ENVIRONMENT_NAME=staging     DATABASE_SECRET=<remote-provider locator>
ENVIRONMENT_NAME=production  DATABASE_SECRET=<remote-provider locator>
```

This mapping is provider-based, not intrinsically tied to the word `local`.
When a deployment system injects final secret values, a deployed environment
can intentionally use the direct/env-backed provider and the variable remains a
payload. Only a provider that performs a remote lookup interprets it as a
locator.

Use neutral names such as `DATABASE_SECRET`, `SERVICE_ACCOUNT_SECRET`, or
`LLM_API_KEY_SECRET`. Do not use `*_ARN`, `*_PATH`, or `*_VALUE` when the same
variable has different source semantics across environments.

The payload schema is defined by the logical secret, independently of its
source or backend:

- A structured account credential can be a JSON object locally, for example
  `{"username":"replace-me","password":"replace-me"}`. The remote provider
  fetches a document with the same required fields.
- A scalar API key, token, password, or DSN is a plain string locally. The
  remote provider fetches a plain string. Do not wrap a scalar in a one-field
  JSON object merely to make every secret look alike.

This contract is backend-neutral. A remote value might be a cloud secret ID,
vault path, parameter name, URI, or another provider locator. The application
does not derive that locator from `ENVIRONMENT_NAME`; deployment tooling injects
the exact environment-scoped value.

Resolve in this order:

1. Validate non-secret settings and the environment/provider mode.
2. Select exactly one local or remote provider.
3. Let that provider read the stable source variables.
4. Resolve each variable to its raw payload: direct locally, fetched remotely.
5. Validate the expected scalar or structured payload schema and convert
   sensitive fields to `SecretStr` immediately.
6. Construct external clients and begin application I/O only after every
   required secret has resolved.

Reject missing sources, invalid locators, malformed JSON, missing structured
fields, unexpected scalar/object shapes, and provider failures before external
application work. Error messages may name the logical variable and expected
shape but must never include its raw value. In particular, do not pass these
source variables through an ordinary renderable `Settings` model: a value that
is a harmless locator remotely is a credential-bearing payload locally.

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
"""Secrets with environment-selected local or remote resolution."""

from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .settings import Settings, get_settings


class Secrets(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    database_password: SecretStr
    llm_api_key: SecretStr


class EnvSecrets(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    database_password: SecretStr = Field(alias="DATABASE_SECRET")
    llm_api_key: SecretStr = Field(alias="LLM_API_KEY_SECRET")

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

    @staticmethod
    def _required_source(variable: str) -> str:
        value = os.environ.get(variable)
        if not value:
            raise ValueError(f"Required secret source {variable!r} is not set.")
        return value

    def _fetch_scalar(self, source: str) -> str:
        del source
        raise NotImplementedError

    def _load_sync(self) -> Secrets:
        database = self._fetch_scalar(self._required_source("DATABASE_SECRET"))
        api_key = self._fetch_scalar(self._required_source("LLM_API_KEY_SECRET"))
        return Secrets(
            database_password=SecretStr(database),
            llm_api_key=SecretStr(api_key),
        )


def build_secrets_provider(settings: Settings | None = None) -> SecretsProvider:
    settings = settings or get_settings()
    # Common policy: local reads payloads directly, deployed environments
    # resolve locators remotely. Use an explicit validated provider mode instead
    # when deployed environments receive final secret values.
    if settings.environment_name == "local":
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

- AWS SSM: use `AwsSsmSecretsProvider`; fetch parameters with decryption.
- Azure Key Vault: use `AzureKeyVaultSecretsProvider`; keep the vault URL in
  `Settings` and prefer managed identity in deployed environments.
- GCP Secret Manager: use `GcpSecretManagerSecretsProvider`; keep a shared
  project ID in `Settings` when needed.
- Vault: use `VaultSecretsProvider`; keep the server address and mount in
  `Settings`; do not commit tokens.

In every case, deployment-owned backend coordinates belong to the env-only
runtime contract. When using stable logical secret-source variables, inject
each exact per-secret locator through its neutral variable rather than storing
secret names or paths in YAML or deriving them from the environment name.

For native async SDKs, use the SDK directly instead of `asyncio.to_thread`.
