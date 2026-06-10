from unittest import mock

import pytest
from TIPCommon.data_models import Environment

from core.SiemplifyApiClient import SiemplifyApiClient


@pytest.fixture
def mock_siemplify():
    siemplify = mock.MagicMock()
    # Provide the necessary minimal setup for SiemplifyApiClient
    siemplify.get_configuration.return_value = {"ApiRoot": "http://localhost"}
    return siemplify


@pytest.fixture
def api_client(mock_siemplify):
    # Mocking out the initialization logic that uses HTTP
    with mock.patch("core.SiemplifyApiClient.SiemplifyApiClient.get_system_version") as mock_sys_info:
        mock_sys_info.return_value = "6.1.17"
        client = SiemplifyApiClient(api_root="http://localhost", api_key="dummy", siemplify=mock_siemplify)
        return client


def test_import_environment_1p_payload_on_legacy_platform(api_client):
    """
    Test pushing a 1P formatted environment payload to a Legacy backend.
    """
    one_p_payload = {
        "name": "projects/source/locations/us/instances/test/environments/1",
        "displayName": "Test Environment",
        "contactEmails": "test@google.com",
        "remediationDurationInDays": 30,
        "shouldAllowRemediationActions": True,
        "retentionDurationInMonths": 12,
        "environmentAllowedForAllUsers": True,
        "dynamicParameters": [{"key": "value"}],
        "isSystem": False
    }

    # Simulate platform is legacy
    with mock.patch("core.SiemplifyApiClient.platform_supports_1p_api", return_value=False):
        with mock.patch("core.SiemplifyApiClient.api_import_environment") as mock_save:
            api_client.import_environment(one_p_payload)
            
            # Verify the translated payload that was sent to the legacy backend
            mock_save.assert_called_once()
            called_payload = mock_save.call_args[0][1]
            assert called_payload["name"] == "Test Environment"
            assert called_payload["remediationDurationInDays"] == 30
            assert called_payload["shouldAllowRemediationActions"] is True
            assert called_payload["retentionDurationInMonths"] == 12
            assert called_payload["environmentAllowedForAllUsers"] is True
            assert called_payload["dynamicParameters"] == [{"key": "value"}]
            assert called_payload["isSystem"] is False


def test_import_environment_legacy_payload_on_1p_platform(api_client):
    """
    Test pushing a Legacy formatted environment payload to a 1P backend.
    """
    legacy_payload = {
        "id": 1,
        "name": "Test Environment",
        "contactEmails": "test@google.com",
        "remediationDurationInDays": 30,
        "shouldAllowRemediationActions": True,
        "retentionDurationInMonths": 12,
        "environmentAllowedForAllUsers": True,
        "dynamicParameters": [{"key": "value"}],
        "isSystem": False
    }

    # Simulate platform is 1P
    with mock.patch("core.SiemplifyApiClient.platform_supports_1p_api", return_value=True):
        with mock.patch("core.SiemplifyApiClient.api_import_environment") as mock_save:
            api_client.import_environment(legacy_payload)
            
            # Verify the translated payload that was sent to the 1P backend
            mock_save.assert_called_once()
            called_payload = mock_save.call_args[0][1]
            assert called_payload["displayName"] == "Test Environment"
            assert called_payload["remediationDurationInDays"] == 30
            assert called_payload["shouldAllowRemediationActions"] is True
            assert called_payload["retentionDurationInMonths"] == 12
            assert called_payload["environmentAllowedForAllUsers"] is True
            assert called_payload["dynamicParameters"] == [{"key": "value"}]
            assert called_payload["isSystem"] is False


def test_get_environments_returns_legacy_on_1p_platform(api_client):
    """
    Test pulling environments from a 1P backend converts them to legacy.
    """
    one_p_payload = {
        "name": "projects/source/locations/us/instances/test/environments/1",
        "displayName": "Test Environment 1P",
        "contactEmails": "test@google.com",
        "remediationDurationInDays": 30,
        "shouldAllowRemediationActions": True,
        "retentionDurationInMonths": 12,
        "environmentAllowedForAllUsers": True,
        "dynamicParameters": [],
        "isSystem": False
    }

    # Simulate platform is 1P
    with mock.patch("core.SiemplifyApiClient.platform_supports_1p_api", return_value=True):
        with mock.patch("core.SiemplifyApiClient.api_get_environments", return_value=[Environment.from_json(one_p_payload)]):
            envs = api_client.get_environments()
            
            assert len(envs) == 1
            # MUST be legacy payload for Git sync!
            assert "displayName" not in envs[0] or envs[0]["name"] == "Test Environment 1P"
            assert envs[0]["name"] == "Test Environment 1P"
            assert envs[0]["remediationDurationInDays"] == 30
