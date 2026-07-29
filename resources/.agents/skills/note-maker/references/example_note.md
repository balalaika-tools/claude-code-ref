# Example Note File

This is a complete, filled-in note following all conventions. Use it as a reference when writing new files.

The example below would live at `python/02_context_managers.md` in a Python notes repo.

---

## Example: `python/02_context_managers.md`

```markdown
# Context Managers and the `with` Statement

> **Who this is for**: Python developers who know classes and exceptions but haven't built
> their own context managers. Assumes you've read [01_decorators.md](01_decorators.md).

---

## 1. What Problem They Solve

Every resource that must be released — file handles, database connections, locks, network
sockets — follows the same pattern: acquire, use, release. Without a guaranteed release
step, exceptions leave resources dangling.

```python
# ❌ Wrong — an exception between open() and close() leaks the file descriptor
f = open("data.csv")
records = parse(f)   # raises ValueError on malformed input
f.close()            # never reached

# ✅ Correct — __exit__ is called even if parse() raises
with open("data.csv") as f:
    records = parse(f)
```

> **Key insight**: `with` is a protocol, not syntax sugar. Any object that implements
> `__enter__` and `__exit__` works — the standard library uses this for locks, decimal
> contexts, mock patches, and more.

---

## 2. The `__enter__` / `__exit__` Protocol

```python
import psycopg2
from typing import Generator

class ManagedConnection:
    """Wraps a psycopg2 connection so callers never call .close() manually."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._conn: psycopg2.extensions.connection | None = None

    def __enter__(self) -> psycopg2.extensions.connection:
        self._conn = psycopg2.connect(self._dsn)
        return self._conn  # bound to the `as` variable

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if self._conn:
            if exc_type is None:
                self._conn.commit()   # only commit on clean exit
            else:
                self._conn.rollback() # roll back on any exception
            self._conn.close()
        return False  # don't suppress the exception — re-raise it
```

| Return value of `__exit__` | Effect                                      |
|---------------------------|---------------------------------------------|
| `False` / `None`          | Exception propagates normally               |
| `True`                    | Exception is suppressed (use intentionally) |

⚠️ Returning `True` is almost always wrong outside of very specific retry logic.

---

## 3. The `@contextmanager` Shortcut

For simple cases, a generator decorated with `@contextmanager` is cleaner than a class:

```python
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

@contextmanager
def timed_block(label: str) -> Generator[None, None, None]:
    """Log how long a block of code takes. Works even if the block raises."""
    import time
    start = time.perf_counter()
    try:
        yield              # execution enters the `with` block here
    finally:
        elapsed = time.perf_counter() - start
        # finally runs on both clean exit and exception — same guarantee as __exit__
        logger.info("%s completed in %.3fs", label, elapsed)

# Usage
with timed_block("index rebuild"):
    rebuild_search_index(db)
```

> **Rule**: everything before `yield` is `__enter__`; everything after (in `finally`) is
> `__exit__`. The `try/finally` is required — without it, an exception in the block skips
> your cleanup.

---

## 4. Execution Flow

```
caller                   context manager
  │                            │
  │─── __enter__() ───────────>│
  │<── returns value ──────────│
  │                            │
  │  [with block executes]     │
  │                            │
  │─── __exit__(exc_info) ────>│  ← called even if block raised
  │<── bool (suppress?) ───────│
  │                            │
  ▼
continues (or re-raises)
```

---

## 5. Real-World Failure Modes

**Forgetting `try/finally` in `@contextmanager`**

```python
# ❌ Cleanup skipped if the with-block raises
@contextmanager
def bad_lock(resource):
    resource.acquire()
    yield
    resource.release()  # not reached on exception — deadlock

# ✅ Always wrap yield in try/finally
@contextmanager
def good_lock(resource):
    resource.acquire()
    try:
        yield
    finally:
        resource.release()
```

**Swallowing exceptions accidentally**

```python
# ❌ __exit__ accidentally returns a truthy value (the string "ok")
def __exit__(self, *args):
    self._conn.close()
    return "ok"   # truthy — all exceptions silently disappear

# ✅ Be explicit
def __exit__(self, *args):
    self._conn.close()
    return False
```

---

**Next**: [03_generators.md — Iterators and Generator Pipelines](03_generators.md)
```
