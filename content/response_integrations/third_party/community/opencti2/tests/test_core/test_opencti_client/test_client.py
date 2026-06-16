from unittest.mock import MagicMock, patch

import pytest
from core.datamodels.incident import Incident
from core.datamodels.incident_response import IncidentResponse
from core.datamodels.observable import Observable
from core.datamodels.request_for_information import RequestForInformation
from core.datamodels.request_for_takedown import RequestForTakedown
from core.opencti_client.client import OpenCTIClient, OpenCTIClientError
from core.opencti_client.json_results import (
    AddObjectToContainerJSONResult,
    IncidentJSONResult,
    IncidentResponseJSONResult,
    ObservableJSONResult,
    RequestForInformationJSONResult,
    RequestForTakedownJSONResult,
)


@pytest.fixture
def fake_incident_api_response():
    return {
        "id": "20f7568f-e6f4-4bcc-8cc8-d6d5ba366622",
        "standard_id": "incident--79249898-aaf5-5843-8080-1cab8511771d",
        "entity_type": "Incident",
        "parent_types": ["Basic-Object", "Stix-Object", "Stix-Core-Object"],
        "createdById": None,
    }


@pytest.fixture
def fake_incident_response_api_response():
    return {
        "id": "20f7568f-e6f4-4bcc-8cc8-d6d5ba366622",
        "standard_id": "case-incident--79249898-aaf5-5843-8080-1cab8511771d",
        "entity_type": "Case-Incident",
        "parent_types": ["Basic-Object", "Stix-Object", "Stix-Core-Object"],
        "createdById": None,
    }


@pytest.fixture
def fake_rfi_api_response():
    return {
        "id": "a313ee4d-c786-494b-b053-24b140344956",
        "standard_id": "case-rfi--1775d682-9e1b-441a-8577-a875bf44d148",
        "entity_type": "Case-Rfi",
        "parent_types": ["Basic-Object", "Stix-Object", "Stix-Core-Object"],
        "createdById": None,
    }


@pytest.fixture
def fake_rft_api_response():
    return {
        "id": "c41abbd3-4e60-47db-9137-6eb8713f9715",
        "standard_id": "case-rft--f65a5182-a019-4bfc-b341-f5dae79352dd",
        "entity_type": "Case-Rft",
        "parent_types": ["Basic-Object", "Stix-Object", "Stix-Core-Object"],
        "createdById": None,
    }


@pytest.fixture
def fake_observable_api_response():
    return {
        "id": "f0a4d1e0-02ad-4de4-af73-2f54aa07fdba",
        "standard_id": "domain-name--f5d26a47-6f1c-5d61-a24f-9f6f8f5fbf36",
        "entity_type": "Stix-Cyber-Observable",
        "parent_types": ["Basic-Object", "Stix-Object", "Stix-Cyber-Observable"],
        "createdById": None,
    }


@pytest.fixture
def mock_pycti_client():
    """Return a MagicMock replacing pycti.OpenCTIApiClient."""
    with patch("core.opencti_client.client.OpenCTIApiClient") as mock_cls:
        instance = MagicMock()
        mock_cls.return_value = instance
        yield instance


@pytest.fixture
def client(mock_pycti_client):
    return OpenCTIClient(
        base_url="https://opencti.example.com",
        api_token="token",
    )


@pytest.fixture
def incident():
    return Incident(name="Test Incident")


@pytest.fixture
def request_for_information():
    return RequestForInformation(name="Test RFI")


@pytest.fixture
def incident_response():
    return IncidentResponse(name="Test IRC")


@pytest.fixture
def request_for_takedown():
    return RequestForTakedown(name="Test RFT")


@pytest.fixture
def observable():
    return Observable(type="Domain-Name", value="google.com")


class TestOpenCTIClientInit:
    def test_health_check_called_on_successful_connection(self):
        with patch("pycti.OpenCTIApiClient.health_check") as mock_health_check:
            mock_health_check.return_value = True

            OpenCTIClient(base_url="https://opencti.example.com", api_token="token")

            mock_health_check.assert_called_once()

    def test_raises_on_invalid_connection(self):
        with patch("core.opencti_client.client.OpenCTIApiClient") as mock_cls:
            mock_cls.side_effect = ValueError("bad url")

            with pytest.raises(
                OpenCTIClientError, match="Failed to establish connection"
            ):
                OpenCTIClient(base_url="bad", api_token="token")


class TestCreateIncident:
    def test_returns_incident_json_result(
        self, client, mock_pycti_client, incident, fake_incident_api_response
    ):
        mock_pycti_client.incident.create.return_value = fake_incident_api_response

        with patch.object(
            client, "_upsert_labels", wraps=client._upsert_labels
        ) as mock_upsert_labels:
            result = client.create_incident(incident)

        mock_pycti_client.incident.create.assert_called_once_with(
            **incident.to_input_variables()
        )
        mock_upsert_labels.assert_called_once_with(
            incident.to_input_variables().get("objectLabel")
        )
        assert isinstance(result, IncidentJSONResult)

    def test_raises_when_api_returns_none(self, client, mock_pycti_client, incident):
        mock_pycti_client.incident.create.return_value = None

        with pytest.raises(OpenCTIClientError, match="Failed to create Incident"):
            client.create_incident(incident)

    def test_raises_on_invalid_response(self, client, mock_pycti_client, incident):
        mock_pycti_client.incident.create.return_value = {"unexpected": "data"}

        with pytest.raises(
            OpenCTIClientError, match="Unexpected OpenCTI response for Incident"
        ):
            client.create_incident(incident)

    def test_raises_on_api_exception(self, client, mock_pycti_client, incident):
        mock_pycti_client.incident.create.side_effect = RuntimeError("network error")

        with pytest.raises(OpenCTIClientError, match="Failed to create Incident"):
            client.create_incident(incident)


class TestCreateRequestForInformation:
    def test_returns_rfi_json_result(
        self, client, mock_pycti_client, request_for_information, fake_rfi_api_response
    ):
        mock_pycti_client.case_rfi.create.return_value = fake_rfi_api_response

        with patch.object(
            client, "_upsert_labels", wraps=client._upsert_labels
        ) as mock_upsert_labels:
            result = client.create_request_for_information(request_for_information)

        mock_pycti_client.case_rfi.create.assert_called_once_with(
            **request_for_information.to_input_variables()
        )
        mock_upsert_labels.assert_called_once_with(
            request_for_information.to_input_variables().get("objectLabel")
        )
        assert isinstance(result, RequestForInformationJSONResult)

    def test_raises_when_api_returns_none(
        self, client, mock_pycti_client, request_for_information
    ):
        mock_pycti_client.case_rfi.create.return_value = None

        with pytest.raises(
            OpenCTIClientError, match="Failed to create Request for Information"
        ):
            client.create_request_for_information(request_for_information)

    def test_raises_on_invalid_response(
        self, client, mock_pycti_client, request_for_information
    ):
        mock_pycti_client.case_rfi.create.return_value = {"unexpected": "data"}

        with pytest.raises(
            OpenCTIClientError, match="Unexpected OpenCTI response for RFI"
        ):
            client.create_request_for_information(request_for_information)

    def test_raises_on_api_exception(
        self, client, mock_pycti_client, request_for_information
    ):
        mock_pycti_client.case_rfi.create.side_effect = RuntimeError("network error")

        with pytest.raises(
            OpenCTIClientError, match="Failed to create Request for Information"
        ):
            client.create_request_for_information(request_for_information)


class TestCreateIncidentResponse:
    def test_returns_incident_response_json_result(
        self,
        client,
        mock_pycti_client,
        incident_response,
        fake_incident_response_api_response,
    ):
        mock_pycti_client.case_incident.create.return_value = (
            fake_incident_response_api_response
        )

        with patch.object(
            client, "_upsert_labels", wraps=client._upsert_labels
        ) as mock_upsert_labels:
            result = client.create_incident_response(incident_response)

        mock_pycti_client.case_incident.create.assert_called_once_with(
            **incident_response.to_input_variables()
        )
        mock_upsert_labels.assert_called_once_with(
            incident_response.to_input_variables().get("objectLabel")
        )
        assert isinstance(result, IncidentResponseJSONResult)

    def test_raises_when_api_returns_none(
        self, client, mock_pycti_client, incident_response
    ):
        mock_pycti_client.case_incident.create.return_value = None

        with pytest.raises(
            OpenCTIClientError, match="Failed to create IncidentResponse"
        ):
            client.create_incident_response(incident_response)

    def test_raises_on_invalid_response(
        self, client, mock_pycti_client, incident_response
    ):
        mock_pycti_client.case_incident.create.return_value = {"unexpected": "data"}

        with pytest.raises(
            OpenCTIClientError,
            match="Unexpected OpenCTI response for IncidentResponse",
        ):
            client.create_incident_response(incident_response)

    def test_raises_on_api_exception(
        self, client, mock_pycti_client, incident_response
    ):
        mock_pycti_client.case_incident.create.side_effect = RuntimeError(
            "network error"
        )

        with pytest.raises(
            OpenCTIClientError, match="Failed to create IncidentResponse"
        ):
            client.create_incident_response(incident_response)


class TestCreateRequestForTakedown:
    def test_returns_rft_json_result(
        self, client, mock_pycti_client, request_for_takedown, fake_rft_api_response
    ):
        mock_pycti_client.case_rft.create.return_value = fake_rft_api_response

        with patch.object(
            client, "_upsert_labels", wraps=client._upsert_labels
        ) as mock_upsert_labels:
            result = client.create_request_for_takedown(request_for_takedown)

        mock_pycti_client.case_rft.create.assert_called_once_with(
            **request_for_takedown.to_input_variables()
        )
        mock_upsert_labels.assert_called_once_with(
            request_for_takedown.to_input_variables().get("objectLabel")
        )
        assert isinstance(result, RequestForTakedownJSONResult)

    def test_raises_when_api_returns_none(
        self, client, mock_pycti_client, request_for_takedown
    ):
        mock_pycti_client.case_rft.create.return_value = None

        with pytest.raises(
            OpenCTIClientError, match="Failed to create Request for Takedown"
        ):
            client.create_request_for_takedown(request_for_takedown)


class TestCreateObservable:
    def test_returns_observable_json_result(
        self, client, mock_pycti_client, observable, fake_observable_api_response
    ):
        mock_pycti_client.stix_cyber_observable.create.return_value = (
            fake_observable_api_response
        )

        with patch.object(
            client, "_upsert_labels", wraps=client._upsert_labels
        ) as mock_upsert_labels:
            result = client.create_observable(observable)

        mock_pycti_client.stix_cyber_observable.create.assert_called_once_with(
            **observable.to_input_variables()
        )
        mock_upsert_labels.assert_called_once_with(
            observable.to_input_variables().get("objectLabel")
        )
        assert isinstance(result, ObservableJSONResult)

    def test_raises_when_api_returns_none(self, client, mock_pycti_client, observable):
        mock_pycti_client.stix_cyber_observable.create.return_value = None

        with pytest.raises(OpenCTIClientError, match="Failed to create Observable"):
            client.create_observable(observable)

    def test_raises_on_invalid_response(self, client, mock_pycti_client, observable):
        mock_pycti_client.stix_cyber_observable.create.return_value = {"id": "only"}

        with pytest.raises(
            OpenCTIClientError, match="Unexpected OpenCTI response for Observable"
        ):
            client.create_observable(observable)

    def test_raises_on_api_exception(self, client, mock_pycti_client, observable):
        mock_pycti_client.stix_cyber_observable.create.side_effect = RuntimeError(
            "network error"
        )

        with pytest.raises(OpenCTIClientError, match="Failed to create Observable"):
            client.create_observable(observable)


class TestAddObjectToContainer:
    @pytest.mark.parametrize(
        ("container_type", "attr_name"),
        [
            ("Report", "report"),
            ("Case-Incident", "case_incident"),
            ("Case-Rfi", "case_rfi"),
            ("Case-Rft", "case_rft"),
            ("Grouping", "grouping"),
        ],
    )
    def test_dispatches_to_expected_container_api(
        self,
        client,
        mock_pycti_client,
        container_type,
        attr_name,
    ):
        container_api = getattr(mock_pycti_client, attr_name)
        container_api.add_stix_object_or_stix_relationship.return_value = True

        result = client.add_object_to_container(
            container_type=container_type,
            container_id="container-1",
            object_id="object-1",
        )

        container_api.add_stix_object_or_stix_relationship.assert_called_once_with(
            id="container-1",
            stixObjectOrStixRelationshipId="object-1",
        )
        assert isinstance(result, AddObjectToContainerJSONResult)
        assert result.container_entity_type == container_type
        assert result.container_id == "container-1"
        assert result.object_id == "object-1"

    def test_raises_when_pycti_returns_false(self, client, mock_pycti_client):
        mock_pycti_client.report.add_stix_object_or_stix_relationship.return_value = (
            False
        )

        with pytest.raises(OpenCTIClientError, match="Failed to add object to Report"):
            client.add_object_to_container(
                container_type="Report",
                container_id="container-1",
                object_id="object-1",
            )

    def test_raises_on_unsupported_container_type(self, client):
        with pytest.raises(OpenCTIClientError, match="Unsupported container type"):
            client.add_object_to_container(
                container_type="unsupported",
                container_id="container-1",
                object_id="object-1",
            )

    def test_raises_on_api_exception(self, client, mock_pycti_client):
        mock_pycti_client.report.add_stix_object_or_stix_relationship.side_effect = (
            RuntimeError("network error")
        )

        with pytest.raises(
            OpenCTIClientError, match="Failed to add object to Report in OpenCTI"
        ):
            client.add_object_to_container(
                container_type="Report",
                container_id="container-1",
                object_id="object-1",
            )


class TestUpsertLabels:
    def test_creates_each_label(self, client, mock_pycti_client):
        client._upsert_labels(["local", "test"])

        assert mock_pycti_client.label.create.call_args_list == [
            ((), {"value": "local"}),
            ((), {"value": "test"}),
        ]

    def test_noop_when_labels_none(self, client, mock_pycti_client):
        client._upsert_labels(None)

        mock_pycti_client.label.create.assert_not_called()

    def test_noop_when_labels_empty(self, client, mock_pycti_client):
        client._upsert_labels([])

        mock_pycti_client.label.create.assert_not_called()

    def test_raises_opencti_client_error_on_failure(self, client, mock_pycti_client):
        mock_pycti_client.label.create.side_effect = RuntimeError("network error")

        with pytest.raises(OpenCTIClientError, match="Failed to upsert labels"):
            client._upsert_labels(["local"])
