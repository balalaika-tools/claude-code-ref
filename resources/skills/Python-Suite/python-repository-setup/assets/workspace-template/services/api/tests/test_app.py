from sample_api.app import health, root


def test_health() -> None:
    assert health() == {"status": "ok"}


def test_root_uses_shared_library() -> None:
    assert root() == {"message": "hello from the workspace"}
