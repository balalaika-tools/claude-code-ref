---
name: fastapi-ai-service
description: >
  Use when creating, restructuring, or extending a FastAPI-based AI or agent
  backend service: project layout, app factory/lifespan, runtime dependencies,
  configuration and secrets, API routers, background workers, AI agent modules,
  and startup validation. Use when the user asks to scaffold a new FastAPI AI
  service, build a new agent backend, align a backend with this repo's service
  conventions, or coordinate focused sub-skills such as settings-config.
---

# FastAPI AI Service

Use this as the orchestration skill for FastAPI AI backends. Keep decisions
consistent with the existing codebase, then load focused sub-skills for
self-contained sections.

## Shape

Prefer this service layout unless the repo already has a stronger convention:

```text
<project-root>/
  config/
    local.yaml
    staging.yaml
    production.yaml
  .env.example
  src/
    <package>/
      app.py
      bootstrap/
        app_factory.py
        lifespan.py
        runtime.py
      core/
        settings.py
        secrets.py
        logger.py
        telemetry.py
        errors.py
      api/
        dependencies.py
        exceptions.py
        middleware.py
        routers/
          health.py
          <workflow>.py
        models/
      ai_engine/
        agents/
          <agent_name>/
            builder.py
            prompt.py
            schemas.py
            tools/
      services/
        <domain>/
      worker/
  tests/
```

Adapt names to the current repository. For example, this repo uses
`src/exceptionist/`, `bootstrap/`, `core/`, `api/`, `ai_engine/`, `services/`,
and `worker/`.

## Build Flow

1. Inspect the current package structure, dependency manager, and config files.
2. Define the service boundary: API endpoints, long-lived clients, agent entry
   points, background workers, and persistence dependencies.
3. Load `/settings-config` before creating or changing `settings.py`,
   `secrets.py`, `config/*.yaml`, or `.env.example`.
4. Build FastAPI through an app factory. Put long-lived resources in lifespan
   startup/shutdown, attach a typed runtime object to `app.state`, and fail fast
   before accepting traffic.
5. Keep routers thin. Validate requests with Pydantic models, call service
   modules, and translate domain errors through shared exception handlers.
6. Keep agent code isolated under `ai_engine/agents/<agent_name>/`: builder,
   prompt, schemas, and tools. Inject settings/secrets/runtime dependencies
   instead of reading globals deep inside tools.
7. Add focused tests for startup validation, config loading, router behavior,
   and agent/service contracts.

## Sub-Skills

- `/settings-config`: Operational YAML config, Pydantic settings, secrets,
  `.env.example`, and provider-specific secret loading.
- Future focused skills can cover API routing, agent module design, runtime
  lifecycle, persistence, observability, and deployment.

## Delegation

Use sub-agents when a task is self-contained and has a clear artifact boundary.
Configuration setup is a good candidate: pass the target package name, expected
environments, selected secret backend, and the current repo conventions, then
review the produced `settings.py`, `secrets.py`, `config/*.yaml`, and
`.env.example` before wiring the rest of the service.
