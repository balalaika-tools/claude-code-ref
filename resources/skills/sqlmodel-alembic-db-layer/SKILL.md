---
name: sqlmodel-alembic-db-layer
description: >-
  Scaffold or review an async Python database layer built on SQLModel and
  Alembic: `base.py` conventions and shared metadata/naming, `models/` table
  classes, `engine.py`/`session.py` with production-grade async connection
  pooling, a `repositories/` layer that is the only place doing DB access, a
  `queries/` folder for large reporting SQL kept out of Python code, and async
  Alembic migrations (async `env.py`, autogenerate, revision workflow). Covers
  both a uv-workspace monorepo (a shared `libs/`/`packages/` member holding
  only `base.py` + `models/`, a dedicated `services/db-migrate` deployable
  holding the Alembic history, and `engine.py`, `session.py`,
  `repositories/`, `queries/` per service) and a single-service repo
  (`src/<package>/infrastructure/db/` holding everything). Also covers the
  Dockerfile `ENTRYPOINT`/`CMD` for running migrations in each shape, and the
  schema-verification harness: an `alembic check` drift job in CI, model/DB
  parity tests, pinning trigger/function DDL that autogenerate cannot see,
  runtime schema-version guards, squashing pre-release history to a baseline,
  migration transaction semantics, backfills, and rollout runbooks for gated
  or destructive migrations. Use when adding or reviewing DB models, wiring an
  async SQLAlchemy/SQLModel engine, setting up, extending, squashing, or
  verifying Alembic migrations, investigating model/migration drift, deciding
  where repository/query code should live relative to shared model
  definitions, or wiring the migration runner's Dockerfile.
---

# Async DB Layer: SQLModel + Alembic

Everything in this layer is **async** — async engine, `AsyncSession`, async
repository methods, async Alembic `env.py`. There is no sync `Session`/
`create_engine` anywhere in code that follows this skill.

The layer has five concerns, always in this order of dependency:

```text
models/            SQLModel table classes — the shape of the data
   ↑
base.py            shared metadata/naming convention + mixins models/ use
   ↑
alembic/           migration history for that one metadata object — its own
                    deployable in a monorepo, colocated in a single-service repo
engine.py           →  session.py  →  repositories/  →  queries/*.sql
process-wide          per-unit-of-      only place that      large SQL kept
connection pool       work session      runs a query          out of .py files
```

`models/` and `base.py` describe the schema. `alembic/` versions it. Everything
from `engine.py` down is how a given process talks to that schema — and that
part legitimately differs per service, while the schema itself must not.

## Resolve the repo shape first

This skill assumes you already know whether you're in a **uv workspace
monorepo** (multiple independently-deployable services, or a repo that will
grow into that) or a **single-service repo**. That decision — and the
`services/` vs `libs/`/`packages/` naming, workspace sources, per-member
`pyproject.toml` — belongs to the `python-uv-workspace-monorepo` skill, not
this one. Resolve that first if it isn't already settled; this skill only
adds where the *DB* pieces specifically go once the shape is decided. See
`references/repo-layout.md` for both trees.

## Reference routing

Load only what you're touching:

- `references/repo-layout.md` — the monorepo vs. single-service folder trees,
  and specifically which DB pieces are shared vs. per-service.
- `references/models-and-base.md` — `base.py` (naming convention, mixins) and
  `models/` (one file per table, relationships, timestamps, PK conventions).
- `references/engine-and-session.md` — `engine.py` (async engine, driver
  choice, production connection-pool sizing) and `session.py` (session
  factory, per-unit-of-work lifecycle).
- `references/repositories-and-queries.md` — the repository pattern, when a
  query stays inline vs. moves to `queries/*.sql`, and the async
  relationship-loading gotcha.
- `references/alembic-migrations.md` — async `env.py`, autogenerate caveats,
  the revision workflow, migration transaction semantics (what a failed run
  leaves behind; `autocommit_block` for `CONCURRENTLY`), hand-written data
  backfills, keeping one head with many authors, what a fresh database
  replaying the full history implies for gated/destructive migrations,
  squashing pre-release history to a baseline before the first deployment,
  and the one-file head-only rollout runbook.
- `references/schema-verification.md` — making "migrations match models" a
  standing guarantee: the database-contract CI job (`upgrade head` +
  `alembic check` on a scratch database), model/DB parity tests, pinning
  schema objects created via `op.execute` (triggers, functions) that
  autogenerate cannot see, the runtime schema-version guard and its
  pinned-revision cost, and the disposable-database test convention.
- `references/docker-entrypoint.md` — what the runtime stage's
  `ENTRYPOINT`/`CMD` should be for running migrations: a dedicated
  always-migrates image in a monorepo vs. a command override on the app's own
  image in a single-service repo.

## Core conventions

- Async only, top to bottom. If you find yourself importing `Session` (not
  `AsyncSession`) or `create_engine` (not `create_async_engine`) anywhere in
  this layer, that's a bug, not a style choice.
- **Exactly one `SQLModel.metadata` for the schema, and exactly one Alembic
  migration history for it.** In a monorepo, that metadata lives once in the
  shared models package, and that one migration history lives once in a
  dedicated migration-runner deployable that depends on it — never redefined
  or re-migrated per service. Two migration histories against the same
  physical database is the failure mode this whole layout exists to prevent.
- The engine is a **process-wide singleton** — built once at startup, disposed
  once at shutdown. Never call `create_async_engine(...)` per request or per
  call; that silently defeats connection pooling.
- `repositories/` is the *only* code that imports `AsyncSession`, `text()`, or
  a model class for querying. Nothing outside `repositories/` runs a query
  directly — business logic calls a repository method, never the session.
- Simple lookups/filters use the SQLModel query builder (`select()` +
  `session.exec()`) inline in a repository method. Multi-join, aggregation, or
  reporting SQL goes in its own `.sql` file under `queries/`, read once at
  import time and executed via `text()`.
- Every autogenerated Alembic revision is read by a human before it's
  committed. Autogenerate detects structural drift between models and the
  live schema; it does not write data backfills and it misses some
  type/server-default changes unless `compare_type`/`compare_server_default`
  are explicitly enabled (see `references/alembic-migrations.md`).
- A fresh database replays the **entire** migration history, so a migration
  that can fail closed (an env-var gate, a preflight) blocks every fresh
  install unless that path is explicitly provided for — and history that has
  never deployed anywhere is squashed to a single verified baseline before
  the first deployment, not replayed forever
  (see `references/alembic-migrations.md`).
- "Migrations match models" is verified continuously, not assumed: CI applies
  the real history to a scratch database and runs `alembic check` against it,
  and schema objects created via `op.execute` — invisible to autogenerate and
  to that check — get their own pin the moment they are written
  (see `references/schema-verification.md`).

## Related skills

- `python-uv-workspace-monorepo` — repo-shape decision, workspace mechanics,
  per-member `pyproject.toml`, Docker builds. Use it first for the monorepo
  case.
- `settings-config` — where the database URL and credentials themselves are
  read from (`Settings`/`secrets.py`). This skill's `engine.py` takes a
  resolved connection string; it doesn't decide how that string is sourced.
