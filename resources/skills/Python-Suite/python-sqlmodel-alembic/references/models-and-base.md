# `base.py` and `models/`

## `base.py`: shared metadata + reusable table base

`SQLModel.metadata` is a single global `MetaData` object — every
`table=True` class in the process attaches to it, the same way a classic
SQLAlchemy declarative `Base` works. `base.py` is where you configure that
metadata once and define any shared non-table SQLModel base, so `models/` files
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

**2. A reusable non-table base** for fields that every table genuinely shares.
It inherits `SQLModel` but omits `table=True`, so concrete table models can
inherit its fields reliably without creating another table:

```python
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, SQLModel


class TableBase(SQLModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )
```

Use a database `server_default`, not an application-side `datetime.now()`
default, for creation timestamps. Update `updated_at` explicitly in repository
writes, or create and migrate a database trigger when the database must own that
behavior. SQLAlchemy's `onupdate=` is client-side SQL generation; it is not a
database trigger or server-side update default.

A fieldless `class Base(SQLModel): pass` adds nothing: `SQLModel.metadata`
already provides the shared registry. Add a non-table base only when it owns
real shared fields or behavior, and avoid a lattice of overlapping mixins.

## `models/`: one file per table

```python
# models/user.py
from sqlmodel import Field, Relationship

from myservice.db.base import TableBase


class User(TableBase, table=True):
    __tablename__ = "users"

    email: str = Field(unique=True, index=True)
    reports: list["Report"] = Relationship(back_populates="owner")
```

- One domain entity per file, named after the table.
- `models/__init__.py` re-exports every model class:

  ```python
  from myservice.db.models.report import Report
  from myservice.db.models.user import User

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
