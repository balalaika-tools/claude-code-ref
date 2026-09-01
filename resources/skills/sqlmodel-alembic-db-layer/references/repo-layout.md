# Repo Layout: Monorepo vs. Single-Service

The internal architecture is identical in both cases — `base.py` → `models/`
→ `alembic/` → `engine.py` → `session.py` → `repositories/` → `queries/`. What
differs is purely **which pieces are shared and which are per-service**. This
is a structural difference, not an architectural one.

## Single-service repo

Everything lives together under the one package's source tree:

```text
repo/
├── pyproject.toml
├── alembic.ini                          # script_location points below
└── src/
    └── myservice/
        └── infrastructure/
            └── db/
                ├── base.py               # shared metadata + mixins
                ├── engine.py             # async engine, pool config
                ├── session.py            # session factory / DI
                ├── models/
                │   ├── __init__.py       # re-exports every model
                │   ├── user.py
                │   └── report.py
                ├── alembic/
                │   ├── env.py
                │   └── versions/
                ├── repositories/
                │   ├── user_repository.py
                │   └── report_repository.py
                └── queries/
                    └── monthly_report.sql
```

One process, one schema, one everything. There's no split to reason about
beyond the five concerns themselves — see the other reference files for what
goes in each file.

## Monorepo (uv workspace)

The schema — `base.py` and `models/` — is the one thing every service must
agree on, so it lives **once**, in a shared workspace member with no
deployable of its own. The Alembic history that versions that schema is
itself a deployable — it's exactly the thing a migration-runner task/job
executes — so it gets its **own** service, depending on the shared models
package rather than living inside it. Nothing downstream should have to
install `alembic` and a DB driver just because it depends on the table
definitions. Everything from `engine.py` down is *how a given process talks
to the database*, and that legitimately varies per service (a read-heavy API
wants a bigger pool than a low-traffic batch worker; each service only has
repositories for the tables it actually touches), so those stay per-service:

```text
repo/
├── pyproject.toml                        # workspace root
├── uv.lock
├── libs/                                 # or packages/ — match whatever
│   └── db_models/                        # this repo already uses
│       ├── pyproject.toml                # deps: sqlmodel, sqlalchemy — nothing heavier
│       └── src/
│           └── db_models/
│               ├── __init__.py
│               ├── base.py               # shared metadata + mixins
│               └── models/
│                   ├── __init__.py
│                   ├── user.py
│                   └── report.py
│
└── services/
    ├── db-migrate/                       # the only thing that owns Alembic
    │   ├── pyproject.toml                # deps: db-models{workspace=true}, alembic, asyncpg
    │   ├── Dockerfile
    │   ├── alembic.ini
    │   ├── alembic/
    │   │   ├── env.py                    # imports db_models.base / db_models.models
    │   │   └── versions/
    │   └── src/
    │       └── db_migrate/
    │           └── __init__.py           # empty — this service has no app code
    │
    ├── api/
    │   ├── pyproject.toml                # depends on db-models (workspace=true)
    │   └── src/
    │       └── api/
    │           └── infrastructure/
    │               └── db/
    │                   ├── engine.py
    │                   ├── session.py
    │                   ├── repositories/
    │                   │   └── user_repository.py
    │                   └── queries/
    └── worker/
        ├── pyproject.toml
        └── src/
            └── worker/
                └── infrastructure/
                    └── db/
                        ├── engine.py
                        ├── session.py
                        ├── repositories/
                        │   └── report_repository.py
                        └── queries/
                            └── monthly_report.sql
```

`db_models` is a workspace member exactly like any shared library in the
`python-uv-workspace-monorepo` skill: its own `pyproject.toml`, no
`Dockerfile` of its own, consumed via `{ workspace = true }`. `db-models` is
just a placeholder name — call it whatever fits the domain (`db-schema`,
`core-db`, …); what matters is that it holds *only* `base.py` and `models/`,
nothing that turns it into a heavier dependency than a service actually
needs. `db-migrate` is a placeholder too — the point is that it's a
`services/` member (it ships as its own image, per the deployable-unit rule
in `python-uv-workspace-monorepo`), not a `libs/` member.

Each app service's `pyproject.toml` declares:

```toml
[project]
dependencies = ["db-models", "sqlalchemy[asyncio]", "asyncpg"]

[tool.uv.sources]
db-models = { workspace = true }
```

`db-migrate`'s `pyproject.toml` declares the migration-specific dependencies
that no other service needs:

```toml
[project]
dependencies = ["db-models", "alembic", "asyncpg"]

[tool.uv.sources]
db-models = { workspace = true }
```

### Why migrations are never split per service

`users`/`reports`/whatever the actual tables are live in **one physical
database**. If each service kept its own Alembic history against that same
database, two services could each believe they own the "next" revision, race
on `alembic_version`, or — worse — one service's migration silently drops a
column another service still reads. Concentrating the Alembic history in one
dedicated migration-runner service, importing the one shared models package,
makes this structurally impossible: there is exactly one place that can
generate a revision, because there's exactly one place with both `alembic`
installed and the model metadata to diff against. See
`references/alembic-migrations.md` for how that one history runs in
practice — still just `alembic upgrade head`, run as this service's
container command.
