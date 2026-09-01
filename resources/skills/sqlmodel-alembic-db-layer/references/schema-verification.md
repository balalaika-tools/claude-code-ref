# Schema Verification: Making "Migrations Match Models" a Guarantee

Autogenerate review (`references/alembic-migrations.md`) catches drift at the
moment a revision is written. Everything in this file exists because drift
also happens *between* those moments — a model edited without a migration, a
migration hand-tweaked without the model, a trigger added that nothing tracks.
Left unverified, the failure mode is a database that `alembic upgrade head`
builds *almost* like the models describe, discovered by a worker crashing on
a column that isn't there.

## The standing harness: a database-contract CI job

One CI job, running on every PR, against a disposable Postgres service
container (same major version as production — reflection output differs
across versions):

1. **Apply the real history**: `alembic upgrade head` against the empty
   scratch database. Not `metadata.create_all()` — the point is to exercise
   the migrations, and `create_all()` is exactly the shortcut that lets them
   rot.
2. **Diff models against the result**: `alembic check` — it exits non-zero
   and prints the pending operations when `target_metadata` and the migrated
   database disagree. This one step is what turns "upgrade head produces
   exactly what the models describe" from a hope into an invariant.
3. **Run the DB-touching test tiers** against that same migrated database, in
   a declared order when fixtures disagree about who owns the schema.

Alongside the CI diff, keep one integration test module that asserts parity
structurally, so a failure names the exact table/column/constraint instead of
dumping an autogenerate op list:

```python
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

def test_no_model_to_database_drift(sync_connection) -> None:
    diffs = compare_metadata(
        MigrationContext.configure(
            sync_connection,
            opts={"compare_type": True, "compare_server_default": True},
        ),
        SQLModel.metadata,
    )
    assert diffs == []
```

plus reflection-based assertions (via `sqlalchemy.inspect`) that the
database contains **only** the expected tables (`alembic_version` included),
and that names of PKs/FKs/uniques/checks/indexes — and the `postgresql_where`
predicates of partial indexes — match the metadata. Reflection catches what
`compare_metadata` is configured to ignore.

## Schema objects that live outside the metadata

Anything a revision creates via `op.execute` — triggers, functions,
extensions, row-level-security policies, grants — is invisible to
autogenerate **and** to `alembic check`. From the moment such an object is
written, nothing above verifies it exists. So the rule is: the same change
that adds an `op.execute` object also adds its pin —

- a behavioral integration test (e.g. an UPDATE that the trigger must
  reject), and/or
- a reflection/catalog assertion (query `pg_trigger`/`pg_proc`, or a
  normalized `pg_dump --schema-only` comparison) that the object is present
  after `upgrade head`.

This is also why squashing history requires a dump diff, not just
`alembic check` (`references/alembic-migrations.md`) — the metadata-based
tools would happily bless a baseline that silently dropped every trigger.

## Runtime schema-version guard

A service can assert at startup (or in its health check) that the database it
connected to is at the revision its code was built against:

```python
EXPECTED_SCHEMA_VERSION = "a1b2c3d4e5f6"  # the Alembic revision this code expects

async def schema_compatible(session) -> bool:
    current = await session.scalar(text("SELECT version_num FROM alembic_version"))
    return current == EXPECTED_SCHEMA_VERSION
```

It fails fast and legibly on deployment skew — an old image against a
migrated database, or a new image racing the migration task — instead of
failing later on a missing column. The cost is real and must be owned: every
new revision means bumping the constant in **every** service that pins it, in
the same change as the migration. Grep for the old revision id before
merging; a stale pin turns a healthy deploy into a refusing one. (This is the
same "pinned revision ids outside `alembic/`" sweep the squash procedure
requires — the guard is simply the most common pin.)

## The disposable-database convention for tests

DB-touching tests that rebuild the schema (`DROP SCHEMA public CASCADE` →
`upgrade head`) must be structurally unable to aim that at a real database.
The convention: they read their target from a **separate** variable —
`INTEGRATION_DATABASE_URL` — and skip when it is unset. Setting that variable
*is* the authorization to destroy the target; the services' own
`DATABASE_URL` is never consulted by these fixtures, so no CI misconfiguration
or local shell leftover can point the wrecking ball at a database anyone
cares about. CI sets both to the same throwaway service container; a
developer sets `INTEGRATION_DATABASE_URL` to a local scratch database and
nothing else.
