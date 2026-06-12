from unittest.mock import MagicMock, patch

import pytest
from core.datamodels.incident import Incident
from core.datamodels.request_for_information import RequestForInformation
from core.opencti_client.client import OpenCTIClient, OpenCTIClientError
from core.opencti_client.json_results import (
    IncidentJSONResult,
    RequestForInformationJSONResult,
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
def fake_rfi_api_response():
    return {
        "id": "a313ee4d-c786-494b-b053-24b140344956",
        "standard_id": "case-rfi--1775d682-9e1b-441a-8577-a875bf44d148",
        "entity_type": "Case-Rfi",
        "parent_types": ["Basic-Object", "Stix-Object", "Stix-Core-Object"],
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
