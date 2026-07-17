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

from unittest.mock import MagicMock, call

import httpx
import pytest
from pytest_mock import MockerFixture

from TIPCommon.exceptions import EmptyMandatoryValues, ParameterValidationError
from TIPCommon.rest.async_soar_platform_clients.soar_api_client import AsyncMarketplaceApi


@pytest.fixture
def mock_async_sdk(mocker: MockerFixture) -> MagicMock:
    """Fixture to provide a mocked AsyncChronicleSOAR SDK."""
    async_sdk = mocker.MagicMock()
    async_sdk.api_root = "https://mock-soar-api.com"
    async_sdk.logger = mocker.MagicMock()
    async_sdk.client = mocker.MagicMock(spec=httpx.AsyncClient)
    # Mock client.request as an AsyncMock
    async_sdk.client.request = mocker.AsyncMock()
    return async_sdk


@pytest.mark.anyio
async def test_get_installed_integrations_of_environment_success(
    mocker: MockerFixture, mock_async_sdk: MagicMock
) -> None:
    """Test get_installed_integrations_of_environment on success."""
    client = AsyncMarketplaceApi(mock_async_sdk)
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "integrationInstances": [{"id": 1}],
        "nextPageToken": None,
    }
    mock_async_sdk.client.request.return_value = mock_response

    res = await client.get_installed_integrations_of_environment(
        integration_identifier="intel_1",
        environment="Prod",
    )

    assert res == [{"id": 1}]
    mock_async_sdk.client.request.assert_called_once_with(
        "GET",
        "/integrations/intel_1/integrationInstances?$filter=environment eq 'Prod'&pageSize=1000",
        params=None,
        json=None,
        headers=None,
    )


@pytest.mark.anyio
async def test_get_installed_integrations_of_environment_shared(
    mocker: MockerFixture, mock_async_sdk: MagicMock
) -> None:
    """Test get_installed_integrations_of_environment with Shared Instances."""
    client = AsyncMarketplaceApi(mock_async_sdk)
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "integrationInstances": [{"id": 2}],
        "nextPageToken": None,
    }
    mock_async_sdk.client.request.return_value = mock_response

    res = await client.get_installed_integrations_of_environment(
        integration_identifier="intel_1",
        environment="Shared Instances",
    )

    assert res == [{"id": 2}]
    mock_async_sdk.client.request.assert_called_once_with(
        "GET",
        "/integrations/intel_1/integrationInstances?$filter=environment eq '*'&pageSize=1000",
        params=None,
        json=None,
        headers=None,
    )


@pytest.mark.anyio
async def test_get_installed_integrations_of_environment_no_content(
    mocker: MockerFixture, mock_async_sdk: MagicMock
) -> None:
    """Test get_installed_integrations_of_environment when returning 204 No Content."""
    client = AsyncMarketplaceApi(mock_async_sdk)
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 204
    mock_response.json.side_effect = ValueError("No JSON object could be decoded")
    mock_async_sdk.client.request.return_value = mock_response

    res = await client.get_installed_integrations_of_environment(
        integration_identifier="intel_1",
        environment="Prod",
    )

    assert res == []


@pytest.mark.anyio
async def test_get_installed_integrations_of_environment_multi_page(
    mocker: MockerFixture, mock_async_sdk: MagicMock
) -> None:
    """Test get_installed_integrations_of_environment aggregates results from multiple pages."""
    client = AsyncMarketplaceApi(mock_async_sdk)

    mock_response_1 = mocker.MagicMock(spec=httpx.Response)
    mock_response_1.status_code = 200
    mock_response_1.json.return_value = {
        "integrationInstances": [{"id": 1}],
        "nextPageToken": "token_123",
    }

    mock_response_2 = mocker.MagicMock(spec=httpx.Response)
    mock_response_2.status_code = 200
    mock_response_2.json.return_value = {
        "integrationInstances": [{"id": 2}],
        "nextPageToken": None,
    }

    mock_async_sdk.client.request.side_effect = [
        mock_response_1,
        mock_response_2,
    ]

    res = await client.get_installed_integrations_of_environment(
        integration_identifier="intel_1",
        environment="Prod",
    )

    assert res == [{"id": 1}, {"id": 2}]

    assert mock_async_sdk.client.request.call_count == 2
    mock_async_sdk.client.request.assert_has_calls([
        call(
            "GET",
            "/integrations/intel_1/integrationInstances?$filter=environment eq 'Prod'&pageSize=1000",
            params=None,
            json=None,
            headers=None,
        ),
        call(
            "GET",
            "/integrations/intel_1/integrationInstances?$filter=environment eq 'Prod'&pageSize=1000&pageToken=token_123",
            params=None,
            json=None,
            headers=None,
        ),
    ])


@pytest.mark.anyio
async def test_get_connector_cards_success(
    mocker: MockerFixture, mock_async_sdk: MagicMock
) -> None:
    """Test get_connector_cards on success."""
    client = AsyncMarketplaceApi(mock_async_sdk)
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"connectorInstances": [{"id": 1}]}
    mock_async_sdk.client.request.return_value = mock_response

    res = await client.get_connector_cards("int_name")

    assert res == {"connectorInstances": [{"id": 1}]}
    mock_async_sdk.client.request.assert_called_once_with(
        "GET",
        "/integrations/int_name/connectors/-/connectorInstances",
        params=None,
        json=None,
        headers=None,
    )


@pytest.mark.anyio
async def test_get_connector_cards_no_content(
    mocker: MockerFixture, mock_async_sdk: MagicMock
) -> None:
    """Test get_connector_cards when returning 204 No Content."""
    client = AsyncMarketplaceApi(mock_async_sdk)
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 204
    mock_async_sdk.client.request.return_value = mock_response

    res = await client.get_connector_cards("int_name")

    assert res == {"connectorInstances": []}


@pytest.mark.anyio
async def test_get_installed_jobs_all(
    mocker: MockerFixture, mock_async_sdk: MagicMock
) -> None:
    """Test get_installed_jobs when no job instance ID is provided."""
    client = AsyncMarketplaceApi(mock_async_sdk)
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"jobInstances": [{"id": 1}]}
    mock_async_sdk.client.request.return_value = mock_response

    res = await client.get_installed_jobs()

    assert res == {"jobInstances": [{"id": 1}]}
    mock_async_sdk.client.request.assert_called_once_with(
        "GET",
        "/integrations/-/jobs/-/jobInstances",
        params=None,
        json=None,
        headers=None,
    )


@pytest.mark.anyio
async def test_get_installed_jobs_single(
    mocker: MockerFixture, mock_async_sdk: MagicMock
) -> None:
    """Test get_installed_jobs when a job instance ID is provided."""
    client = AsyncMarketplaceApi(mock_async_sdk)
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "ji_1"}
    mock_async_sdk.client.request.return_value = mock_response

    res = await client.get_installed_jobs(job_instance_id="ji_1")

    assert res == {"id": "ji_1"}
    mock_async_sdk.client.request.assert_called_once_with(
        "GET",
        "/integrations/-/jobs/-/jobInstances/ji_1",
        params=None,
        json=None,
        headers=None,
    )


@pytest.mark.anyio
async def test_get_installed_jobs_no_content_all(
    mocker: MockerFixture, mock_async_sdk: MagicMock
) -> None:
    """Test get_installed_jobs returning 204 No Content with no ID."""
    client = AsyncMarketplaceApi(mock_async_sdk)
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 204
    mock_async_sdk.client.request.return_value = mock_response

    res = await client.get_installed_jobs()

    assert res == {"jobInstances": []}


@pytest.mark.anyio
async def test_get_installed_jobs_no_content_single(
    mocker: MockerFixture, mock_async_sdk: MagicMock
) -> None:
    """Test get_installed_jobs returning 204 No Content with a specific ID."""
    client = AsyncMarketplaceApi(mock_async_sdk)
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 204
    mock_async_sdk.client.request.return_value = mock_response

    res = await client.get_installed_jobs(job_instance_id="ji_1")

    assert res == {}


@pytest.mark.anyio
async def test_set_configuration_property(
    mocker: MockerFixture, mock_async_sdk: MagicMock
) -> None:
    """Test set_configuration_property correctly makes a PUT request."""
    client = AsyncMarketplaceApi(mock_async_sdk)
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "updated"}
    mock_async_sdk.client.request.return_value = mock_response

    res = await client.set_configuration_property(
        integration_instance_identifier="inst_1",
        property_name="prop1",
        property_value="val1",
    )

    assert res == {"status": "updated"}
    mock_async_sdk.client.request.assert_called_once_with(
        "PUT",
        "/legacySdk:legacyUpdateConfigurationProperty",
        params={"identifier": "inst_1", "propertyName": "prop1", "format": "snake"},
        json={"property_value": "val1"},
        headers=None,
    )


@pytest.mark.anyio
async def test_set_connector_parameter(
    mocker: MockerFixture, mock_async_sdk: MagicMock
) -> None:
    """Test set_connector_parameter correctly makes a PUT request."""
    client = AsyncMarketplaceApi(mock_async_sdk)
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "updated"}
    mock_async_sdk.client.request.return_value = mock_response

    res = await client.set_connector_parameter(
        connector_instance_identifier="conn_1",
        parameter_name="param1",
        parameter_value="val1",
    )

    assert res == {"status": "updated"}
    mock_async_sdk.client.request.assert_called_once_with(
        "PUT",
        "/legacySdk:legacyUpdateConnectorParameter",
        params={"identifier": "conn_1", "parameterName": "param1", "format": "snake"},
        json={"parameter_value": "val1"},
        headers=None,
    )


@pytest.mark.anyio
async def test_save_or_update_job_success(
    mocker: MockerFixture, mock_async_sdk: MagicMock
) -> None:
    """Test save_or_update_job correctly makes a PATCH request."""
    client = AsyncMarketplaceApi(mock_async_sdk)
    job_data = {
        "name": "projects/p/locations/l/instances/i/integrations/int_1/jobs/j/jobInstances/ji_1",
        "parameters": [{"name": "p1", "value": "v1"}],
    }

    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "saved"}
    mock_async_sdk.client.request.return_value = mock_response

    res = await client.save_or_update_job(job_data)

    assert res == {"status": "saved"}
    mock_async_sdk.client.request.assert_called_once_with(
        "PATCH",
        "/integrations/int_1/jobs/j/jobInstances/ji_1",
        params={"updateMask": "parameters"},
        json={"parameters": [{"name": "p1", "value": "v1"}]},
        headers=None,
    )


@pytest.mark.anyio
async def test_save_or_update_job_no_content(
    mocker: MockerFixture, mock_async_sdk: MagicMock
) -> None:
    """Test save_or_update_job handles 204 No Content correctly."""
    client = AsyncMarketplaceApi(mock_async_sdk)
    job_data = {
        "name": "projects/p/locations/l/instances/i/integrations/int_1/jobs/j/jobInstances/ji_1",
        "parameters": [{"name": "p1", "value": "v1"}],
    }

    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 204
    mock_async_sdk.client.request.return_value = mock_response

    res = await client.save_or_update_job(job_data)

    assert res == {}


@pytest.mark.anyio
async def test_save_or_update_job_missing_name(
    mock_async_sdk: MagicMock,
) -> None:
    """Test save_or_update_job raises EmptyMandatoryValues if name is missing."""
    client = AsyncMarketplaceApi(mock_async_sdk)
    job_data = {
        "parameters": [{"name": "p1", "value": "v1"}],
    }

    with pytest.raises(EmptyMandatoryValues) as exc_info:
        await client.save_or_update_job(job_data)

    assert "Job data must include a 'name' field" in str(exc_info.value)


@pytest.mark.anyio
async def test_save_or_update_job_missing_parameters(
    mock_async_sdk: MagicMock,
) -> None:
    """Test save_or_update_job raises EmptyMandatoryValues if parameters are missing."""
    client = AsyncMarketplaceApi(mock_async_sdk)
    job_data = {
        "name": "projects/p/locations/l/instances/i/integrations/int_1/jobs/j/jobInstances/ji_1",
    }

    with pytest.raises(EmptyMandatoryValues) as exc_info:
        await client.save_or_update_job(job_data)

    assert "Job data is missing 'parameters' field" in str(exc_info.value)


@pytest.mark.anyio
async def test_save_or_update_job_invalid_path(
    mock_async_sdk: MagicMock,
) -> None:
    """Test save_or_update_job raises ParameterValidationError if name is invalid."""
    client = AsyncMarketplaceApi(mock_async_sdk)
    job_data = {
        "name": "invalid_path",
        "parameters": [{"name": "p1", "value": "v1"}],
    }

    with pytest.raises(ParameterValidationError) as exc_info:
        await client.save_or_update_job(job_data)

    assert "Cannot parse resource path" in str(exc_info.value)
    assert 'Invalid parameter "name"' in str(exc_info.value)
