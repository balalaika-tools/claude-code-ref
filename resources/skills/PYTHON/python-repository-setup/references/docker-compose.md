# Docker Compose and the root `.env`

Use this reference for local Docker Compose orchestration in either repository
mode.

## Ownership

Keep one real `<repo-root>/.env` for local Compose values and exclude it from
Git and Docker build contexts. Commit `<repo-root>/.env.example` as the stack
bootstrap contract.

In a workspace, also keep `services/<name>/.env.example` beside every
deployable. It is the complete authoritative runtime contract for that process,
whether started by Compose, `uv run`, tests, or a deployment platform. The root
file does not replace it: it documents Compose inputs, stack-only values, and
the service variables Compose passes through.

For a single service, the root `.env.example` is both the Compose input contract
and the service runtime contract; do not duplicate it under another directory.

## Explicit per-service mapping

Use interpolation from the root `.env`, but declare exactly which values enter
each container:

```yaml
services:
  api:
    build:
      context: .
      dockerfile: services/api/Dockerfile
    environment:
      ENVIRONMENT_NAME: ${API_ENVIRONMENT_NAME:?set API_ENVIRONMENT_NAME}
      DATABASE_URL: ${API_DATABASE_URL:?set API_DATABASE_URL}
      OPENAI_API_KEY: ${API_OPENAI_API_KEY:?set API_OPENAI_API_KEY}
      APP_PORT: ${API_APP_PORT:-8080}

  worker:
    build:
      context: .
      dockerfile: services/worker/Dockerfile
    environment:
      ENVIRONMENT_NAME: ${WORKER_ENVIRONMENT_NAME:?set WORKER_ENVIRONMENT_NAME}
      DATABASE_URL: ${WORKER_DATABASE_URL:?set WORKER_DATABASE_URL}
      QUEUE_URL: ${WORKER_QUEUE_URL:?set WORKER_QUEUE_URL}
```

Prefix root variables when services may legitimately need different values,
then map them to the stable variable name expected by each process. Share an
unprefixed root variable only when it intentionally represents one stack-wide
value. Use `${VAR:?message}` for required inputs and `${VAR:-value}` only for
safe local defaults.

Do not use `env_file: .env` as a shortcut for application services. It exposes
every root variable and secret to every container, hides the service dependency
contract, and creates accidental coupling. Explicit mapping produces container
process environment variables, which take precedence over pydantic-settings
dotenv, YAML, and class defaults.

The Compose project `.env` supplies `${...}` interpolation; its presence alone
does not expose every value inside a container. Shell variables and an explicit
Compose environment file can change interpolation precedence, so verify the
resolved model rather than reasoning from filenames alone.

## Secrets and validation

Runtime secrets may enter local containers through explicit `environment:`
mapping, but never through Dockerfile `ARG` or build-time `ENV`. Production uses
an orchestrator or secret provider rather than a committed dotenv file.

Run from the repository root:

```bash
docker compose config --quiet
docker compose up --build
```

Verify missing substitutions fail, required variables reach the intended
container, unrelated service secrets remain absent, and startup validation
succeeds. Do not print secret values during validation.
