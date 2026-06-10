import json
from unittest import mock

import pytest
from TIPCommon.data_models import JobInstance

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
    with mock.patch("core.SiemplifyApiClient.SiemplifyApiClient.update_session_token"):
        with mock.patch("core.SiemplifyApiClient.SiemplifyApiClient.get_system_info") as mock_sys_info:
            mock_sys_info.return_value = {"version": "6.1.17"}
            client = SiemplifyApiClient(mock_siemplify)
            return client


def test_add_job_1p_payload_on_legacy_platform(api_client):
    """
    Test pushing a 1P formatted job payload to a Legacy backend.
    """
    one_p_payload = {
        "name": "projects/source/locations/us/instances/test/integrations/Siemplify/jobs/1/jobInstances/1",
        "displayName": "Actions Monitor",
        "author": "Siemplify System",
        "intervalSeconds": 10800,
        "enabled": True,
        "custom": False,
        "script": "import json",
        "description": "Test job",
        "uniqueIdentifier": "123",
        "parameters": []
    }

    # Simulate platform is legacy
    with mock.patch("core.SiemplifyApiClient.platform_supports_1p_api", return_value=False):
        with mock.patch("core.SiemplifyApiClient.api_save_or_update_job") as mock_save:
            api_client.add_job(one_p_payload)
            
            # Verify the translated payload that was sent to the legacy backend
            mock_save.assert_called_once()
            called_payload = mock_save.call_args[0][1]
            assert called_payload["name"] == "Actions Monitor"
            assert called_payload["creator"] == "Siemplify System"
            assert called_payload["runIntervalInSeconds"] == 10800
            assert called_payload["isEnabled"] is True
            assert called_payload["isCustom"] is False


def test_add_job_legacy_payload_on_1p_platform(api_client):
    """
    Test pushing a Legacy formatted job payload to a 1P backend.
    """
    legacy_payload = {
        "name": "Actions Monitor",
        "creator": "Siemplify System",
        "runIntervalInSeconds": 10800,
        "isEnabled": True,
        "isCustom": False,
        "script": "import json",
        "description": "Test job",
        "uniqueIdentifier": "123",
        "parameters": []
    }

    # Simulate platform is 1P
    with mock.patch("core.SiemplifyApiClient.platform_supports_1p_api", return_value=True):
        with mock.patch("core.SiemplifyApiClient.api_save_or_update_job") as mock_save:
            api_client.add_job(legacy_payload)
            
            # Verify the translated payload that was sent to the 1P backend
            mock_save.assert_called_once()
            called_payload = mock_save.call_args[0][1]
            assert called_payload["displayName"] == "Actions Monitor"
            assert called_payload["name"] == "Actions Monitor" # Default fallback for missing GCP name
            assert called_payload["author"] == "Siemplify System"
            assert called_payload["intervalSeconds"] == 10800
            assert called_payload["enabled"] is True
            assert called_payload["custom"] is False


def test_definitions_job_class_extraction():
    """
    Test that the core.definitions.Job class correctly extracts fields from both schemas.
    """
    from core.definitions import Job
    
    # Legacy payload
    legacy_job = Job({"name": "Legacy Job", "runIntervalInSeconds": 5000})
    assert legacy_job.name == "Legacy Job"
    assert legacy_job.runIntervalInSeconds == 5000

    # 1P payload
    one_p_job = Job({"name": "projects/123", "displayName": "1P Job", "intervalSeconds": 6000})
    assert one_p_job.name == "1P Job"
    assert one_p_job.runIntervalInSeconds == 6000
