# pylint: disable=redefined-outer-name
from dataclasses import dataclass
from unittest.mock import Mock, patch

import pytest

from requests.exceptions import HTTPError

from palo_alto_ngfw.core.NGFWAuth import NGFWAuth
from palo_alto_ngfw.core.NGFWManager import NGFWManager


@dataclass
class Credentials:
    server_address: str
    username: str
    password: str


@pytest.fixture
def credentials() -> Credentials:
    return Credentials(
        server_address="https://mock.ngfw",
        username="user",
        password="pass"
    )


@pytest.fixture
def mock_siemplify() -> Mock:
    """Mock Siemplify object."""
    mock = Mock()
    mock.environment = "DefaultEnvironment"
    mock.integration_instance = "DefaultInstance"
    return mock


def _create_mock_response(status_code: int, content: bytes) -> Mock:
    mock = Mock()
    mock.status_code = status_code
    mock.content = content
    mock.text = content.decode()
    return mock


@pytest.fixture
def mock_response_keygen() -> Mock:
    return _create_mock_response(
        200,
        content=(
            b'<response status="success">'
            b"<result><key>new_key</key></result>"
            b"</response>"
        )
    )


@pytest.fixture
def mock_response_success() -> Mock:
    return _create_mock_response(
        200,
        content=b"<response status='success'></response>"
    )


@pytest.fixture
def mock_response_403() -> Mock:
    return _create_mock_response(403, content=b"Forbidden")


@patch("requests.Session.request")
def test_init_no_context(
    mock_request: Mock,
    credentials: Credentials,
    mock_siemplify: Mock,
    mock_response_keygen: Mock
) -> None:
    """Test initialization when no cached key exists."""
    mock_request.return_value = mock_response_keygen
    mock_siemplify.get_context_property.return_value = None

    manager = NGFWManager(
        credentials.server_address,
        credentials.username,
        credentials.password,
        logger=Mock(),
        siemplify=mock_siemplify,
    )

    assert manager.api_key == "new_key"
    mock_siemplify.set_context_property.assert_called_once()
    assert mock_request.called


@patch("NGFWAuth.NGFWAuth._decrypt")
@patch("requests.Session.request")
def test_init_with_context(
    mock_request: Mock,
    mock_decrypt: Mock,
    credentials: Credentials,
    mock_siemplify: Mock
) -> None:
    """Test initialization when a valid cached key exists."""
    mock_siemplify.get_context_property.return_value = "existing_key"
    mock_decrypt.return_value = "existing_key"

    manager = NGFWManager(
        credentials.server_address,
        credentials.username,
        credentials.password,
        logger=Mock(),
        siemplify=mock_siemplify,
    )

    assert manager.api_key == "existing_key"
    mock_request.assert_not_called()


@patch("NGFWAuth.NGFWAuth._decrypt")
@patch("requests.Session.request")
def test_session_reuse_and_403_refresh(
    mock_request: Mock,
    mock_decrypt: Mock,
    credentials: Credentials,
    mock_siemplify: Mock,
    mock_response_keygen: Mock,
    mock_response_success: Mock,
    mock_response_403: Mock
) -> None:
    """Test session reuse and key refresh on 403 Forbidden."""
    mock_siemplify.get_context_property.return_value = "existing_key"
    mock_decrypt.return_value = "existing_key"

    mock_request.side_effect = [
        mock_response_403,
        mock_response_keygen,
        mock_response_success,
    ]

    manager = NGFWManager(
        credentials.server_address,
        credentials.username,
        credentials.password,
        logger=Mock(),
        siemplify=mock_siemplify,
    )

    manager.GetCurrenCanidateConfig()

    assert manager.api_key == "new_key"
    mock_siemplify.set_context_property.assert_called()


@patch("requests.Session.request")
def test_init_with_stale_password_key(
    mock_request: Mock,
    credentials: Credentials,
    mock_siemplify: Mock,
    mock_response_keygen: Mock
) -> None:
    """Test initialization when cached key is encrypted with old password."""
    mock_manager_old = Mock()
    mock_manager_old.password = "old_pass"

    auth_old = NGFWAuth(mock_manager_old)

    encrypted_key = auth_old._encrypt("dummy_key")  # pylint: disable=protected-access
    assert auth_old._decrypt(encrypted_key) == "dummy_key"  # pylint: disable=protected-access

    mock_siemplify.get_context_property.return_value = encrypted_key
    mock_request.return_value = mock_response_keygen

    mock_logger = Mock()
    NGFWManager(
        credentials.server_address,
        credentials.username,
        "new_pass",
        logger=mock_logger,
        siemplify=mock_siemplify,
    )

    mock_siemplify.set_context_property.assert_called()

    error_calls = mock_logger.error.call_args_list
    assert any("Failed to decrypt initial key" in str(call) for call in error_calls)


@patch("requests.Session.request")
def test_validate_authentication_http_error(
    mock_request: Mock,
    credentials: Credentials,
    mock_siemplify: Mock,
    mock_response_403: Mock
) -> None:
    """Test that _validate_authentication raises safe HTTPError."""
    mock_siemplify.get_context_property.return_value = None

    def raise_http_post_error():
        raise HTTPError(
            "Original message without sensitive url https://mock.ngfw?type=keygen",
            response=mock_response_403
        )

    mock_response_403.raise_for_status.side_effect = raise_http_post_error
    mock_response_403.reason = "Forbidden"

    mock_response_403_fallback = _create_mock_response(403, content=b"Forbidden")

    def raise_http_get_error():
        raise HTTPError(
            "Original message with sensitive url https://mock.ngfw?password=secret",
            response=mock_response_403_fallback
        )

    mock_response_403_fallback.raise_for_status.side_effect = raise_http_get_error
    mock_response_403_fallback.reason = "Forbidden"

    mock_request.side_effect = [
        mock_response_403,
        mock_response_403_fallback,
    ]

    with pytest.raises(HTTPError) as exc_info:
        NGFWManager(
            credentials.server_address,
            credentials.username,
            credentials.password,
            logger=Mock(),
            siemplify=mock_siemplify,
        )

    assert "Client error: Forbidden" == str(exc_info.value)
    assert "secret" not in str(exc_info.value)
