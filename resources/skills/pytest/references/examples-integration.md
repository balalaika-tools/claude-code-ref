# Integration pytest examples

Adapt this pattern to the installed SQLAlchemy version and the actual ownership
of the application session. It applies to framework-neutral backends as well as
FastAPI services.

## SQLAlchemy same-connection transaction fixture

This SQLAlchemy 2.x pattern permits application code using the bound session to
commit while teardown rolls back the outer transaction.

```python
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session


@pytest.fixture
def db_session(test_engine: Engine) -> Iterator[Session]:
    connection = test_engine.connect()
    outer_transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()
```

Inject this exact session through the application boundary. Do not use this
fixture for a worker or concurrent second connection and assume its commits
roll back; use a unique committed database/schema and explicit cleanup there.
