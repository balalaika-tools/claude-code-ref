# `base.py` and `models/`

## `base.py`: shared metadata + mixins

`SQLModel.metadata` is a single global `MetaData` object — every
`table=True` class in the process attaches to it, the same way a classic
SQLAlchemy declarative `Base` works. `base.py` is where you configure that
metadata once and define mixins every table model reuses, so `models/` files
stay pure data-shape declarations.

Two things belong here:

**1. A naming convention**, set before any migration is ever generated.
Without one, Alembic autogenerate produces a different implicit constraint
name every time depending on column order, and every unrelated schema change
gets noisy renames mixed in:

```python
from sqlmodel import SQLModel

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
SQLModel.metadata.naming_convention = NAMING_CONVENTION
```

**2. Reusable mixins** — plain classes, not tables themselves, that concrete
models inherit from alongside `SQLModel`:

```python
import uuid
from datetime import datetime

from sqlalchemy import func
from sqlmodel import Field


class TimestampMixin:
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )


class UUIDPrimaryKeyMixin:
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
```

Use `server_default`/`onupdate` at the **database** level, not an
application-side `datetime.now()` default — the DB clock is the one source of
truth every replica agrees on, an app-side default is per-process and drifts
under clock skew or when two processes write concurrently.

There is no separate abstract `Base` class layered on top of `SQLModel`
itself — `SQLModel.metadata` already *is* the shared registry, so a plain
`class Base(SQLModel): pass` adds nothing. Mixins are the mechanism for
sharing fields; `SQLModel` is still the direct parent of every table model.

## `models/`: one file per table

```python
# models/user.py
from sqlmodel import Field, Relationship

from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, SQLModel, table=True):
    __tablename__ = "users"

    email: str = Field(unique=True, index=True)
    reports: list["Report"] = Relationship(back_populates="owner")
```

- One domain entity per file, named after the table.
- `models/__init__.py` re-exports every model class:

  ```python
  from .user import User
  from .report import Report

  __all__ = ["User", "Report"]
  ```

  This isn't cosmetic — Alembic's autogenerate diffs `SQLModel.metadata`
  against the live database, and a model that was never imported never
  registered itself on that metadata. A single `from db_models.models import *`
  (or explicit imports) at the top of Alembic's `env.py` is what actually
  makes every table visible; forgetting to re-export a new model here is the
  most common way a migration silently comes out empty.
- Put `Relationship()` fields on models freely, but see
  `references/repositories-and-queries.md` for the async-specific rule about
  how they get *loaded* — implicit lazy-loading a relationship inside an
  async session is a runtime error, not just a slow query.
