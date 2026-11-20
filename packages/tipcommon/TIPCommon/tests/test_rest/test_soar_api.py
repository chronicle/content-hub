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

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from TIPCommon.data_models import InstalledIntegrationInstance, UserDetails
from TIPCommon.rest.soar_api import (
    attach_case_playbook_to_case,
    attach_workflow_to_case,
    create_integrations_instance,
    export_package,
    get_case_insights,
    get_enabled_workflow_cards,
    get_environment_group_names,
    get_installed_connectors,
    get_installed_integrations_of_environment,
    get_siemplify_user_details,
    get_sla_records,
    get_system_version,
    get_user_profile_cards,
    install_integration,
    save_or_update_job,
    search_cases_by_everything,
)

if TYPE_CHECKING:
    from TIPCommon.rest.soar_platform_clients.legacy_soar_api import LegacySoarApi
    from TIPCommon.rest.soar_platform_clients.one_platform_soar_api import OnePlatformSoarApi


@pytest.fixture
def mock_get_soar_client_one_platform(
    mocker: MockerFixture, mock_oneplatform_client: "OnePlatformSoarApi"
) -> MagicMock:
    mock_get_client = mocker.patch("TIPCommon.rest.soar_api.get_soar_client")
    mock_get_client.return_value = mock_oneplatform_client
    return mock_get_client


@pytest.fixture
def mock_get_soar_client_legacy(mocker: MockerFixture, mock_legacy_client: "LegacySoarApi") -> MagicMock:
    mock_get_client = mocker.patch("TIPCommon.rest.soar_api.get_soar_client")
    mock_get_client.return_value = mock_legacy_client
    return mock_get_client


def test_get_user_profile_cards_one_platform(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test get_user_profile_cards wrapper function formats output under One Platform API client."""
    mock_oneplatform_client.get_users_profile_cards = mocker.MagicMock(return_value=[{"username": "user1"}])

    res = get_user_profile_cards(mock_chronicle_soar)

    assert res == {"objectsList": [{"username": "user1"}]}
    params: Any = mock_oneplatform_client.params
    assert params.page_size == 20


def test_get_user_profile_cards_legacy(
    mocker: MockerFixture,
    mock_get_soar_client_legacy: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_legacy_client: "LegacySoarApi",
) -> None:
    """Test get_user_profile_cards wrapper function validates and returns JSON under Legacy client."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"objectsList": [{"username": "user1"}]}
    mock_legacy_client.get_users_profile_cards = mocker.MagicMock(return_value=mock_response)

    res = get_user_profile_cards(mock_chronicle_soar)

    assert res == {"objectsList": [{"username": "user1"}]}


def test_get_installed_integrations_of_environment_one_platform(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test get_installed_integrations_of_environment formats instances under One Platform client."""
    mock_oneplatform_client.get_installed_integrations_of_environment = mocker.MagicMock(
        return_value=[
            {
                "identifier": "id1",
                "integrationIdentifier": "intel_1",
                "environment": "Prod",
                "displayName": "Instance 1",
            }
        ]
    )

    res = get_installed_integrations_of_environment(mock_chronicle_soar, "Prod", "intel_1")

    assert len(res) == 1
    assert isinstance(res[0], InstalledIntegrationInstance)
    assert res[0].identifier == "id1"
    assert res[0].integration_identifier == "intel_1"
    assert res[0].environment_identifier == "Prod"
    assert res[0].instance_name == "Instance 1"


def test_get_installed_integrations_of_environment_legacy(
    mocker: MockerFixture,
    mock_get_soar_client_legacy: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_legacy_client: "LegacySoarApi",
) -> None:
    """Test get_installed_integrations_of_environment validates and handles 204 JSON under Legacy client."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "integrationInstances": [
            {
                "identifier": "id1",
                "integrationIdentifier": "intel_1",
                "environment": "Prod",
                "displayName": "Instance 1",
            }
        ]
    }
    mock_legacy_client.get_installed_integrations_of_environment = mocker.MagicMock(return_value=mock_response)

    res = get_installed_integrations_of_environment(mock_chronicle_soar, "Prod", "intel_1")

    assert len(res) == 1
    assert isinstance(res[0], InstalledIntegrationInstance)
    assert res[0].identifier == "id1"


def test_get_case_insights_one_platform(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test get_case_insights wrapper function formats list output under One Platform client."""
    mock_oneplatform_client.get_case_insights = mocker.MagicMock(return_value=[{"title": "Insight 1"}])

    res = get_case_insights(mock_chronicle_soar, 1)

    assert len(res) == 1
    assert res[0]["title"] == "Insight 1"


def test_get_case_insights_legacy(
    mocker: MockerFixture,
    mock_get_soar_client_legacy: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_legacy_client: "LegacySoarApi",
) -> None:
    """Test get_case_insights wrapper function validates and aggregates results under Legacy client."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"activities": [{"title": "Insight 1"}]}
    mock_legacy_client.get_case_insights = mocker.MagicMock(return_value=mock_response)

    res = get_case_insights(mock_chronicle_soar, 1)

    assert len(res) == 1
    assert res[0]["title"] == "Insight 1"


def test_get_siemplify_user_details_one_platform(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test get_siemplify_user_details formats user profile cards output under One Platform client."""
    mock_oneplatform_client.get_siemplify_user_details = mocker.MagicMock(
        return_value=[{"id": 42, "user_name": "test_user"}]
    )

    res = get_siemplify_user_details(mock_chronicle_soar, "some_search", False, 1, 10, "False")

    assert len(res) == 1
    assert isinstance(res[0], UserDetails)
    assert res[0].id_ == 42


def test_get_siemplify_user_details_legacy(
    mocker: MockerFixture,
    mock_get_soar_client_legacy: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_legacy_client: "LegacySoarApi",
) -> None:
    """Test get_siemplify_user_details validates and extracts objectsList under Legacy client."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"objectsList": [{"id": 42, "user_name": "test_user"}]}
    mock_legacy_client.get_siemplify_user_details = mocker.MagicMock(return_value=mock_response)

    res = get_siemplify_user_details(mock_chronicle_soar, "some_search", False, 1, 10, "False")

    assert len(res) == 1
    assert isinstance(res[0], UserDetails)
    assert res[0].id_ == 42


def test_search_cases_by_everything_one_platform(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test search_cases_by_everything formats aggregated search output under One Platform client."""
    mock_oneplatform_client.search_cases_by_everything = mocker.MagicMock(return_value=[{"id": 1}, {"id": 2}])

    res = search_cases_by_everything(mock_chronicle_soar, {"query": "something"})

    assert res == {"results": [{"id": 1}, {"id": 2}]}


def test_search_cases_by_everything_legacy(
    mocker: MockerFixture,
    mock_get_soar_client_legacy: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_legacy_client: "LegacySoarApi",
) -> None:
    """Test search_cases_by_everything validates and returns json output under Legacy client."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": [{"id": 1}, {"id": 2}]}
    mock_legacy_client.search_cases_by_everything = mocker.MagicMock(return_value=mock_response)

    res = search_cases_by_everything(mock_chronicle_soar, {"query": "something"})

    assert res == {"results": [{"id": 1}, {"id": 2}]}


def test_save_or_update_job_one_platform(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test save_or_update_job wrapper function validates and returns JSON under One Platform client."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    mock_oneplatform_client.save_or_update_job = mocker.MagicMock(return_value=mock_response)

    job_data = {"name": "projects/p/locations/l/instances/i/integrations/int/jobs/j/jobInstances/ji", "parameters": []}
    res = save_or_update_job(mock_chronicle_soar, job_data)

    assert res == {"status": "success"}
    params: Any = mock_oneplatform_client.params
    assert params.job_data == job_data


def test_save_or_update_job_legacy(
    mocker: MockerFixture,
    mock_get_soar_client_legacy: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_legacy_client: "LegacySoarApi",
) -> None:
    """Test save_or_update_job wrapper function validates and returns JSON under Legacy client."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    mock_legacy_client.save_or_update_job = mocker.MagicMock(return_value=mock_response)

    job_data = {"name": "projects/p/locations/l/instances/i/integrations/int/jobs/j/jobInstances/ji", "parameters": []}
    res = save_or_update_job(mock_chronicle_soar, job_data)

    assert res == {"status": "success"}
    params: Any = mock_legacy_client.params
    assert params.job_data == job_data


def test_attach_case_playbook_to_case_one_platform(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test attach_case_playbook_to_case wrapper function sets params and calls OnePlatform client."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_oneplatform_client.attach_case_playbook_to_case = mocker.MagicMock(return_value=mock_response)

    attach_case_playbook_to_case(
        mock_chronicle_soar,
        case_id=123,
        playbook_name="Playbook A",
        should_run_automatic=True,
        original_workflow_definition_identifier="wf_def_1",
    )

    params: Any = mock_oneplatform_client.params
    assert params.case_id == 123
    assert params.playbook_name == "Playbook A"
    assert params.should_run_automatic is True
    assert params.original_workflow_definition_identifier == "wf_def_1"
    mock_oneplatform_client.attach_case_playbook_to_case.assert_called_once()


def test_get_enabled_workflow_cards_one_platform_dict_payload(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test get_enabled_workflow_cards extracts payload from dict response under OnePlatform client."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"payload": [{"id": "card_1"}]}
    mock_oneplatform_client.get_enabled_workflow_cards = mocker.MagicMock(return_value=mock_response)

    res = get_enabled_workflow_cards(mock_chronicle_soar, "Production")

    assert res == [{"id": "card_1"}]
    params: Any = mock_oneplatform_client.params
    assert params.environment == "Production"


def test_get_enabled_workflow_cards_one_platform_list_response(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test get_enabled_workflow_cards returns list response directly if not wrapped in dict."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"id": "card_2"}]
    mock_oneplatform_client.get_enabled_workflow_cards = mocker.MagicMock(return_value=mock_response)

    res = get_enabled_workflow_cards(mock_chronicle_soar, "Production")

    assert res == [{"id": "card_2"}]


# ==================== Connectors ====================
def test_get_installed_connectors_list_response(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test get_installed_connectors returns list directly when client returns list of connectors."""
    mock_oneplatform_client.get_installed_connectors = mocker.MagicMock(
        return_value=[{"name": "conn1", "identifier": "c1"}]
    )

    res = get_installed_connectors(mock_chronicle_soar)

    assert res == [{"name": "conn1", "identifier": "c1"}]
    params: Any = mock_oneplatform_client.params
    assert params.connector_instance_id is None


def test_get_installed_connectors_response_object(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test get_installed_connectors validates and returns JSON when client returns a Response object."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"name": "conn1", "identifier": "c1"}
    mock_oneplatform_client.get_installed_connectors = mocker.MagicMock(return_value=mock_response)

    res = get_installed_connectors(mock_chronicle_soar, connector_instance_id=123)

    assert res == {"name": "conn1", "identifier": "c1"}
    params: Any = mock_oneplatform_client.params
    assert params.connector_instance_id == 123


# ==================== Integrations ====================
def test_install_integration(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test install_integration sets params, validates response, and returns JSON."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "installed"}
    mock_oneplatform_client.install_integration = mocker.MagicMock(return_value=mock_response)

    res = install_integration(
        mock_chronicle_soar,
        integration_identifier="custom_integ",
        integration_name="Custom Integration",
        version="1.0.0",
        is_certified="true",
        override_mapping=True,
        stage=False,
    )

    assert res == {"status": "installed"}
    params: Any = mock_oneplatform_client.params
    assert params.integration_identifier == "custom_integ"
    assert params.integration_name == "Custom Integration"
    assert params.version == "1.0.0"
    assert params.is_certified == "true"
    assert params.override_mapping is True
    assert params.stage is False


def test_export_package(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test export_package validates response without json check and returns binary content."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"PK\x03\x04mock_zip_content"
    mock_oneplatform_client.export_package = mocker.MagicMock(return_value=mock_response)

    res = export_package(mock_chronicle_soar, integration_identifier="custom_integ")

    assert res == b"PK\x03\x04mock_zip_content"
    params: Any = mock_oneplatform_client.params
    assert params.integration_identifier == "custom_integ"


def test_create_integrations_instance(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test create_integrations_instance validates response and returns instance JSON."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"instanceId": "inst_123", "environment": "Production"}
    mock_oneplatform_client.create_integrations_instance = mocker.MagicMock(return_value=mock_response)

    res = create_integrations_instance(
        mock_chronicle_soar,
        integration_identifier="integ_1",
        environment="Production",
    )

    assert res == {"instanceId": "inst_123", "environment": "Production"}
    params: Any = mock_oneplatform_client.params
    assert params.integration_identifier == "integ_1"
    assert params.environment == "Production"


# ==================== Jobs / SLA / Playbooks / Settings ====================
def test_get_sla_records_one_platform_list(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test get_sla_records returns list directly when OnePlatform returns a list."""
    mock_oneplatform_client.get_sla_records = mocker.MagicMock(
        return_value=[{"id": "sla_1", "name": "Critical SLA"}]
    )

    res = get_sla_records(mock_chronicle_soar)

    assert res == [{"id": "sla_1", "name": "Critical SLA"}]


def test_get_sla_records_legacy_dict_response(
    mocker: MockerFixture,
    mock_get_soar_client_legacy: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_legacy_client: "LegacySoarApi",
) -> None:
    """Test get_sla_records extracts slaDefinitions from response dict under Legacy client."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"slaDefinitions": [{"id": "sla_legacy_1"}]}
    mock_legacy_client.get_sla_records = mocker.MagicMock(return_value=mock_response)

    res = get_sla_records(mock_chronicle_soar)

    assert res == [{"id": "sla_legacy_1"}]


def test_attach_workflow_to_case(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test attach_workflow_to_case sets parameters and returns parsed JSON response."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "attached"}
    mock_oneplatform_client.attach_workflow_to_case = mocker.MagicMock(return_value=mock_response)

    res = attach_workflow_to_case(
        mock_chronicle_soar,
        case_id=1001,
        alert_group_identifier="ag_1",
        alert_identifier="alert_1",
        wf_name="Investigation Workflow",
        original_wf_identifier="orig_wf_1",
    )

    assert res == {"status": "attached"}
    params: Any = mock_oneplatform_client.params
    assert params.case_id == 1001
    assert params.alert_group_identifier == "ag_1"
    assert params.alert_identifier == "alert_1"
    assert params.wf_name == "Investigation Workflow"
    assert params.original_wf_identifier == "orig_wf_1"


def test_get_system_version(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test get_system_version validates and returns system version JSON."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"version": "6.3.0"}
    mock_oneplatform_client.get_system_version = mocker.MagicMock(return_value=mock_response)

    res = get_system_version(mock_chronicle_soar)

    assert res == {"version": "6.3.0"}


def test_get_environment_group_names(
    mocker: MockerFixture,
    mock_get_soar_client_one_platform: MagicMock,
    mock_chronicle_soar: MagicMock,
    mock_oneplatform_client: "OnePlatformSoarApi",
) -> None:
    """Test get_environment_group_names validates and returns environment group names JSON."""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"environmentGroups": ["Group1", "Group2"]}
    mock_oneplatform_client.get_environment_group_names = mocker.MagicMock(return_value=mock_response)

    res = get_environment_group_names(mock_chronicle_soar)

    assert res == {"environmentGroups": ["Group1", "Group2"]}
