# `engine.py` and `session.py`

## `engine.py`: one async engine per process

```python
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def build_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(
        database_url,
        pool_size=10,
        max_overflow=5,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
    )


engine = build_engine(settings.database_url)
```

`database_url` uses an async driver in its scheme — `postgresql+asyncpg://…`
(the more mature, most common choice) or `postgresql+psycopg://…` (psycopg 3's
native async support, also fully supported by SQLAlchemy 2.x as an
alternative). Either is fine; don't mix them within one service. The URL
itself comes from resolved settings/secrets, not hardcoded here — see the
`settings-config` skill for where that string is sourced from.

Declare **`greenlet` as an explicit dependency** of anything that uses the
async engine. SQLAlchemy's own dependency marker for it only matches
`platform_machine == "aarch64"` (Linux ARM64); on macOS ARM the machine
reports `arm64`, the marker never fires, and the first `await` into the
engine dies with a `MissingGreenlet`/import error — but only on developer
Macs, not in the Linux containers where CI runs, which is what makes it
confusing. One explicit `"greenlet>=3,<4"` line ends the asymmetry.

Build `engine` **once**, at process/module import or an explicit startup hook
— never inside a request handler or a repository method. `create_async_engine`
allocates the connection pool; calling it repeatedly creates a new pool every
time and defeats pooling entirely, which shows up as connection exhaustion
under load that's very confusing to debug because it looks like a pool-sizing
problem rather than a pool-*count* problem. Dispose it once, symmetrically, on
process shutdown:

```python
await engine.dispose()
```

### Pool parameters, and what to actually set them to

An async engine automatically uses `AsyncAdaptedQueuePool` — don't pass
`poolclass` for the app engine (that override is only for Alembic's
one-shot migration engine, see `references/alembic-migrations.md`). The knobs
that matter:

| Parameter | What it controls | Starting point |
|---|---|---|
| `pool_size` | Persistent connections kept open per process | 5–10 for a typical service |
| `max_overflow` | Extra connections allowed above `pool_size` under burst load; closed once returned | 5–10 |
| `pool_timeout` | Seconds to wait for a free connection before raising, once `pool_size + max_overflow` are all checked out | 30 |
| `pool_recycle` | Force-close and reopen connections older than N seconds | 1800 (30 min) — essential for managed Postgres (RDS/Aurora/Cloud SQL) that silently drops idle connections server-side |
| `pool_pre_ping` | Cheap liveness check (`SELECT 1`-equivalent) before handing out a pooled connection | `True` — catches a connection the DB already closed before your query does, instead of surfacing as a query failure |

**Do the multiplication before picking `pool_size`.** Every replica of every
service that talks to this database holds up to `pool_size + max_overflow`
connections. If you run several independent processes against one Postgres
instance, total possible connections is `Σ(pool_size + max_overflow)` across
all of them — check that against the database's `max_connections` (and
whatever headroom other consumers need) before scaling any one service's pool
up, or a burst on one service starves every other service's ability to
connect. At real scale, a connection pooler in front of Postgres (PgBouncer in
transaction mode, or a managed equivalent) is the standard fix rather than
shrinking every service's pool to fit — but that's an infra decision layered
on top of this file, not a change to how `engine.py` itself is written.

## `session.py`: a session per unit of work

```python
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from .engine import engine

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session
```

`AsyncSession` here is `sqlmodel.ext.asyncio.session.AsyncSession` — a thin
wrapper over SQLAlchemy's own `AsyncSession` that adds the SQLModel-aware
`.exec()` method (see `references/repositories-and-queries.md`). Use this
import path, not SQLAlchemy's `AsyncSession` directly, so repositories get
`.exec()` in addition to `.execute()`.

`expire_on_commit=False` matters specifically for async: without it, accessing
an attribute on a committed object triggers an implicit refresh, which is an
implicit *query*, which in an async context either blocks the event loop or
raises — you want attributes to stay usable after commit without a second
round trip.

`get_session` is written as an async generator so it plugs directly into a
framework's dependency-injection lifecycle (FastAPI's `Depends`, or an
equivalent context manager elsewhere) — one session is opened per
request/per handler invocation and closed at the end of it via the `async
with` block, whether the work succeeded or raised. Never hold one `AsyncSession`
open across multiple unrelated units of work, and never share one session
across concurrent tasks — a session is not safe for concurrent use.
