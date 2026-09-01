# `repositories/` and `queries/`

## Repositories are the only DB-access boundary

A repository takes a session by constructor injection — never reaches for a
global session, never opens its own:

```python
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.exec(select(User).where(User.email == email))
        return result.first()
```

Constructor injection (rather than a module-level singleton repository) is
what makes this testable against a real transactional test database and safe
under concurrent requests, since the session it wraps is itself scoped per
unit of work (`references/engine-and-session.md`).

Business/workflow code calls `UserRepository(session).get_by_email(...)`; it
never imports `select`, `text`, or a model class to query directly. That rule
is what keeps "where does this table get read or written" answerable by
grepping one directory.

## Inline query builder vs. an external `.sql` file

Simple filters and lookups stay inline, using SQLModel's `select()` +
`session.exec()` as above — `.exec()` (not `.execute()`) is what returns
model instances directly for a `Select[T]`; `.execute()` still works but is
the SQLAlchemy-core-shaped path and is the one to reach for specifically when
running a raw `text()` query, as below.

Once a query is a multi-table join, a reporting aggregate, or anything long
enough that reading it interleaved with Python hurts, move it to its own
`.sql` file under `queries/`, read once at import time, and run it via
`text()`:

```python
# queries/monthly_report.sql
SELECT ...
FROM ...
WHERE created_at >= :month_start AND created_at < :month_end
GROUP BY ...
```

```python
# repositories/report_repository.py
from pathlib import Path

from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

QUERY_PATH = Path(__file__).parent.parent / "queries" / "monthly_report.sql"
MONTHLY_REPORT_SQL = QUERY_PATH.read_text()


class ReportRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_monthly_report(self, month: str):
        result = await self.session.execute(text(MONTHLY_REPORT_SQL), {"month": month})
        return result.all()
```

The `await` is on `execute()` itself; once the `Result` object comes back,
`.all()`/`.first()`/`.scalars()` on it are plain synchronous calls — there's
no second `await` needed to consume it.

Read the file once, at module import, not on every call — `QUERY_PATH.read_text()`
at module level, not inside `get_monthly_report`. The module-level constant in
the example above already does this correctly; the mistake to avoid is moving
the `.read_text()` call inside the method "for clarity" and re-reading the
file from disk on every query.

## Async relationships: eager-load explicitly, never lazy-load implicitly

A `Relationship()` field on a model (`references/models-and-base.md`) is not
safe to access lazily inside an async session — the default lazy-load
strategy issues a query synchronously under the hood, and doing that inside
an async context either raises (`MissingGreenlet`-style errors) or silently
reintroduces blocking I/O on the event loop. Load what you need explicitly,
in the repository method, with `selectinload`/`joinedload`:

```python
from sqlalchemy.orm import selectinload


async def get_with_reports(self, user_id: uuid.UUID) -> User | None:
    result = await self.session.exec(
        select(User).where(User.id == user_id).options(selectinload(User.reports))
    )
    return result.first()
```

If a caller only needs `user.email`, don't eager-load `reports` for it —
eager-loading is a per-query decision made in the repository method that
matches what that specific call site actually needs, not a blanket option set
once on the model.
