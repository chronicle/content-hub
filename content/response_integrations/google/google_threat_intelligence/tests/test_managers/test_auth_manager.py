
from google_threat_intelligence.core.auth_manager import (
    AuthManager,
    AuthManagerParams,
)


def test_auth_manager_active_group_injection():
    params = AuthManagerParams(
        api_root="https://api.test",
        api_key="test_key",
        asm_project_name="proj1",
        verify_ssl=True,
        active_group="test-group-123",
    )
    manager = AuthManager(params=params)
    session = manager.prepare_session()

    assert session.headers.get("x-apikey") == "test_key"
    assert session.headers.get("X-Active-Group") == "test-group-123"


def test_auth_manager_no_active_group():
    params = AuthManagerParams(
        api_root="https://api.test",
        api_key="test_key",
        asm_project_name="proj1",
        verify_ssl=True,
        active_group=None,
    )
    manager = AuthManager(params=params)
    session = manager.prepare_session()

    assert session.headers.get("x-apikey") == "test_key"
    assert "X-Active-Group" not in session.headers
