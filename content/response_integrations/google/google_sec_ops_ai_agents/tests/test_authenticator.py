from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from google_sec_ops_ai_agents.core import exceptions
from google_sec_ops_ai_agents.core.authenticator import (
    Authenticator,
    _create_auth_credentials,
    _create_auth_request,
)
from google_sec_ops_ai_agents.core.data_models import (
    SessionAuthenticationParameters,
)


@patch(
    "google_sec_ops_ai_agents.core.authenticator.get_secops_siem_tenant_credentials"
)
def test_create_auth_credentials_success(mock_get_credentials):
    """Test creating auth credentials successfully."""
    auth_params = SessionAuthenticationParameters(
        api_root="https://test.chronicle.security",
        chronicle_soar=MagicMock(),
        verify_ssl=True,
    )
    mock_get_credentials.return_value = "credentials"

    credentials = _create_auth_credentials(auth_params)

    assert credentials == "credentials"
    mock_get_credentials.assert_called_once()


def test_create_auth_credentials_invalid_api_root():
    """Test creating auth credentials with an invalid API root."""
    auth_params = SessionAuthenticationParameters(
        api_root="https://test.backstory.chronicle.security",
        chronicle_soar=MagicMock(),
        verify_ssl=True,
    )

    with pytest.raises(Exception, match=exceptions.INVALID_API_ROOT_ERROR):
        _create_auth_credentials(auth_params)


@patch("google_sec_ops_ai_agents.core.authenticator.Request")
@patch("TIPCommon.base.utils.CreateSession.create_session")
def test_create_auth_request(mock_create_session, mock_request):
    """Test creating an auth request."""
    _create_auth_request(verify_ssl=True)
    mock_create_session.return_value.mount.assert_called_once()
    mock_request.assert_called_once()


@patch("google_sec_ops_ai_agents.core.authenticator._create_auth_credentials")
@patch("google_sec_ops_ai_agents.core.authenticator.AuthorizedSession")
def test_authenticator_authenticate_session(mock_authorized_session, mock_create_credentials):
    """Test the Authenticator's authenticate_session method."""
    authenticator = Authenticator()
    auth_params = SessionAuthenticationParameters(
        api_root="https://test.chronicle.security",
        chronicle_soar=MagicMock(),
        verify_ssl=True,
    )
    mock_create_credentials.return_value = "credentials"

    authenticator.authenticate_session(auth_params)

    mock_create_credentials.assert_called_once_with(auth_params)
    mock_authorized_session.assert_called_once()
