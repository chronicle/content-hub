# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for AsyncCredentialSyncApi."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from pytest_mock import MockerFixture

from TIPCommon.rest.async_soar_platform_clients.async_credential_sync_api import (
    AsyncCredentialSyncApi,
)


@pytest.fixture
def mock_async_client(mocker: MockerFixture) -> MagicMock:
    """Fixture to mock BaseAsyncSoarApi HTTP methods."""
    api_client = AsyncCredentialSyncApi(MagicMock())
    # Mock the request methods from BaseAsyncSoarApi
    api_client.get = AsyncMock()
    api_client.put = AsyncMock()
    api_client.patch = AsyncMock()
    return api_client


@pytest.mark.anyio
async def test_get_installed_integrations_of_environment_success(
    mock_async_client: MagicMock,
) -> None:
    """Test get_installed_integrations_of_environment successfully returns JSON data."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"integrationInstances": [{"id": "inst1"}]}
    mock_async_client.get.return_value = mock_response

    result = await mock_async_client.get_installed_integrations_of_environment(
        integration_identifier="test_integration",
        environment="Default Environment",
    )

    assert result == {"integrationInstances": [{"id": "inst1"}]}
    mock_async_client.get.assert_called_once_with(
        "/integrations/test_integration/integrationInstances",
        params={"$filter": "environment eq 'Default Environment'"},
    )


@pytest.mark.anyio
async def test_get_installed_integrations_of_environment_shared_instances(
    mock_async_client: MagicMock,
) -> None:
    """Test get_installed_integrations_of_environment maps 'Shared Instances' to '*' filter."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"integrationInstances": [{"id": "inst1"}]}
    mock_async_client.get.return_value = mock_response

    result = await mock_async_client.get_installed_integrations_of_environment(
        integration_identifier="test_integration",
        environment="Shared Instances",
    )

    assert result == {"integrationInstances": [{"id": "inst1"}]}
    mock_async_client.get.assert_called_once_with(
        "/integrations/test_integration/integrationInstances",
        params={"$filter": "environment eq '*'"},
    )


@pytest.mark.anyio
async def test_get_installed_integrations_of_environment_no_content(
    mock_async_client: MagicMock,
) -> None:
    """Test get_installed_integrations_of_environment handles 204 No Content response."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 204
    mock_async_client.get.return_value = mock_response

    result = await mock_async_client.get_installed_integrations_of_environment(
        integration_identifier="test_integration",
        environment="Default Environment",
    )

    assert result == {"integrationInstances": []}


@pytest.mark.anyio
async def test_get_connector_cards_success(mock_async_client: MagicMock) -> None:
    """Test get_connector_cards successfully retrieves connector cards."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"connectorInstances": [{"id": "conn1"}]}
    mock_async_client.get.return_value = mock_response

    result = await mock_async_client.get_connector_cards("test_integration")

    assert result == {"connectorInstances": [{"id": "conn1"}]}
    mock_async_client.get.assert_called_once_with(
        "/integrations/test_integration/connectors/-/connectorInstances"
    )


@pytest.mark.anyio
async def test_get_connector_cards_no_content(mock_async_client: MagicMock) -> None:
    """Test get_connector_cards handles 204 No Content response."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 204
    mock_async_client.get.return_value = mock_response

    result = await mock_async_client.get_connector_cards("test_integration")

    assert result == {"connectorInstances": []}


@pytest.mark.anyio
async def test_get_installed_jobs_all(mock_async_client: MagicMock) -> None:
    """Test get_installed_jobs without specific ID fetches all jobs."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"job_instances": [{"id": "job1"}]}
    mock_async_client.get.return_value = mock_response

    result = await mock_async_client.get_installed_jobs()

    assert result == {"job_instances": [{"id": "job1"}]}
    mock_async_client.get.assert_called_once_with(
        "/integrations/-/jobs/-/jobInstances/"
    )


@pytest.mark.anyio
async def test_get_installed_jobs_specific(mock_async_client: MagicMock) -> None:
    """Test get_installed_jobs with ID fetches the specific job."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "job1"}
    mock_async_client.get.return_value = mock_response

    result = await mock_async_client.get_installed_jobs("job1")

    assert result == {"id": "job1"}
    mock_async_client.get.assert_called_once_with(
        "/integrations/-/jobs/-/jobInstances/job1"
    )


@pytest.mark.anyio
async def test_get_installed_jobs_no_content(mock_async_client: MagicMock) -> None:
    """Test get_installed_jobs handles 204 No Content response."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 204
    mock_async_client.get.return_value = mock_response

    result = await mock_async_client.get_installed_jobs()

    assert result == {"job_instances": []}


@pytest.mark.anyio
async def test_set_configuration_property(mock_async_client: MagicMock) -> None:
    """Test set_configuration_property correctly formats and executes PUT request."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    mock_async_client.put.return_value = mock_response

    result = await mock_async_client.set_configuration_property(
        integration_instance_identifier="inst1",
        property_name="apiKey",
        property_value="secret",
    )

    assert result == {"status": "success"}
    mock_async_client.put.assert_called_once_with(
        "/legacySdk:legacyUpdateConfigurationProperty",
        payload={"property_value": "secret"},
        params={
            "identifier": "inst1",
            "propertyName": "apiKey",
            "format": "snake",
        },
    )


@pytest.mark.anyio
async def test_set_connector_parameter(mock_async_client: MagicMock) -> None:
    """Test set_connector_parameter correctly formats and executes PUT request."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    mock_async_client.put.return_value = mock_response

    result = await mock_async_client.set_connector_parameter(
        connector_instance_identifier="conn1",
        parameter_name="password",
        parameter_value="secret_password",
    )

    assert result == {"status": "success"}
    mock_async_client.put.assert_called_once_with(
        "/legacySdk:legacyUpdateConnectorParameter",
        payload={"parameter_value": "secret_password"},
        params={
            "identifier": "conn1",
            "parameterName": "password",
            "format": "snake",
        },
    )


@pytest.mark.anyio
async def test_save_or_update_job_success(mock_async_client: MagicMock) -> None:
    """Test save_or_update_job correctly parses path and PATCHes data."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "job1"}
    mock_async_client.patch.return_value = mock_response

    job_data = {
        "name": "projects/p1/integrations/int1/jobs/job1/jobInstances/ji1",
        "parameters": [{"name": "p1", "value": "v1"}],
    }

    result = await mock_async_client.save_or_update_job(job_data)

    assert result == {"id": "job1"}
    mock_async_client.patch.assert_called_once_with(
        "/integrations/int1/jobs/job1/jobInstances/ji1",
        payload={"parameters": [{"name": "p1", "value": "v1"}]},
        params={"updateMask": "parameters"},
    )


@pytest.mark.anyio
async def test_save_or_update_job_no_content(mock_async_client: MagicMock) -> None:
    """Test save_or_update_job handles 204 No Content correctly by returning empty dict."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 204
    mock_async_client.patch.return_value = mock_response

    job_data = {
        "name": "projects/p1/integrations/int1/jobs/job1/jobInstances/ji1",
        "parameters": [{"name": "p1", "value": "v1"}],
    }

    result = await mock_async_client.save_or_update_job(job_data)

    assert result == {}


@pytest.mark.anyio
async def test_save_or_update_job_invalid_data(mock_async_client: MagicMock) -> None:
    """Test save_or_update_job raises ValueError on missing/invalid keys."""
    # Missing 'name'
    with pytest.raises(ValueError, match="must include a 'name' field"):
        await mock_async_client.save_or_update_job(
            {"parameters": []}
        )

    # Missing 'parameters'
    with pytest.raises(ValueError, match="missing 'parameters' field"):
        await mock_async_client.save_or_update_job(
            {"name": "n1"}
        )

    # Path missing 'integrations/'
    with pytest.raises(ValueError, match="Cannot parse resource path"):
        await mock_async_client.save_or_update_job(
            {"name": "projects/p1/jobs/job1", "parameters": []}
        )
