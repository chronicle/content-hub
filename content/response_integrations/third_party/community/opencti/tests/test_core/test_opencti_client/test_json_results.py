import pytest

from ....core.opencti_client.json_results import (
    BaseJSONResult,
    BaseObjectJSONResult,
    IncidentJSONResult,
    IncidentResponseJSONResult,
    ObservableJSONResult,
    RequestForInformationJSONResult,
    RequestForTakedownJSONResult,
)


@pytest.fixture
def fake_api_response():
    return {
        "id": "20f7568f-e6f4-4bcc-8cc8-d6d5ba366622",
        "standard_id": "incident--79249898-aaf5-5843-8080-1cab8511771d",
        "entity_type": "Incident",
        "parent_types": ["Basic-Object", "Stix-Object", "Stix-Core-Object"],
        "createdById": None,
    }


class TestBaseObjectJSONResultFields:
    def test_class_inherits_from_base(self):
        assert issubclass(BaseObjectJSONResult, BaseJSONResult)

    def test_instance_has_expected_fields(self, fake_api_response):
        result = BaseObjectJSONResult(**fake_api_response)

        assert result.id == fake_api_response["id"]
        assert result.standard_id == fake_api_response["standard_id"]
        assert result.entity_type == fake_api_response["entity_type"]
        assert result.parent_types == fake_api_response["parent_types"]
        assert result.created_by_id is None

    def test_extra_fields_are_ignored(self, fake_api_response):
        data = {**fake_api_response, "unexpected_field": "ignored"}
        result = BaseObjectJSONResult(**data)

        assert not hasattr(result, "unexpected_field")

    def test_json_serialization(self, fake_api_response):
        result = IncidentJSONResult(**fake_api_response)
        serialized = result.json()

        assert serialized["id"] == fake_api_response["id"]
        assert serialized["standard_id"] == fake_api_response["standard_id"]
        assert serialized["entity_type"] == fake_api_response["entity_type"]
        assert serialized["parent_types"] == fake_api_response["parent_types"]
        assert serialized["created_by_id"] is None


class TestBaseObjectJSONResultChildClasses:
    def test_incident_inherits_from_base(self):
        assert issubclass(IncidentJSONResult, BaseObjectJSONResult)

    def test_rfi_inherits_from_base(self):
        assert issubclass(RequestForInformationJSONResult, BaseObjectJSONResult)

    def test_incident_response_inherits_from_base(self):
        assert issubclass(IncidentResponseJSONResult, BaseObjectJSONResult)

    def test_rft_inherits_from_base(self):
        assert issubclass(RequestForTakedownJSONResult, BaseObjectJSONResult)

    def test_observable_inherits_from_base(self):
        assert issubclass(ObservableJSONResult, BaseObjectJSONResult)


class TestBaseJSONResultChildClasses:
    def test_add_object_to_container_inherits_from_base(self):
        assert issubclass(ObservableJSONResult, BaseJSONResult)
