from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from actions.CreateObservables import (
    SCRIPT_NAME,
    CreateObservables,
    CreateObservablesParameters,
)
from core.opencti_client.client import OpenCTIClientError
from SiemplifyDataModel import EntityTypes


def _make_entity(identifier: str, entity_type: str) -> MagicMock:
    entity = MagicMock()
    entity.entity_type = entity_type
    entity.identifier = identifier
    entity.original_identifier = identifier
    entity.additional_properties = {}
    entity.is_enriched = False
    return entity


def _created_observable(observable_id: str = "obs-id-1") -> MagicMock:
    result = MagicMock()
    result.id = observable_id
    result.json.return_value = {
        "id": observable_id,
        "entity_type": "Stix-Cyber-Observable",
    }
    return result


class TestCreateObservablesParameters:
    def test_parse_labels_from_csv(self):
        params = CreateObservablesParameters(labels="label1, label2")
        assert params.labels == ["label1", "label2"]

    def test_defaults(self):
        params = CreateObservablesParameters()
        assert params.description is None
        assert params.score is None
        assert params.labels is None
        assert params.marking is None
        assert params.create_indicator is False

    def test_validate_score_upper_bound(self):
        with pytest.raises(ValueError):
            CreateObservablesParameters(score=101)

    def test_validate_score_lower_bound(self):
        with pytest.raises(ValueError):
            CreateObservablesParameters(score=-1)


class TestCreateObservablesAction:
    def test_validate_params_maps_soar_keys(self, mock_soar_enrich_action):
        mock_soar_enrich_action.parameters = {
            "Description": "malicious",
            "Score": 50,
            "Labels": "local,test",
            "Marking": "TLP:AMBER",
            "Create Indicator": True,
        }

        action = CreateObservables(SCRIPT_NAME)
        action._validate_params()

        assert action.params.description == "malicious"
        assert action.params.score == 50
        assert action.params.labels == ["local", "test"]
        assert action.params.marking == "TLP:AMBER"
        assert action.params.create_indicator is True

    def test_success_path_creates_observable(
        self, mock_soar_enrich_action, mock_api_client
    ):
        entity = _make_entity("1.2.3.4", EntityTypes.ADDRESS)
        mock_soar_enrich_action.parameters = {
            "Score": 42,
            "Labels": "local,test",
            "Marking": "TLP:AMBER",
            "Create Indicator": True,
        }
        mock_soar_enrich_action.target_entities = [entity]
        mock_api_client.create_observable.return_value = _created_observable()

        action = CreateObservables(SCRIPT_NAME)
        action.run()

        assert action.result_value is True
        assert "Successfully created the following entities" in action.output_message
        assert "1.2.3.4" in action.output_message

        observable_obj = mock_api_client.create_observable.call_args.args[0]
        assert observable_obj.type == "IPv4-Addr"
        assert observable_obj.value == "1.2.3.4"
        assert observable_obj.score == 42
        assert observable_obj.labels == ["local", "test"]
        assert observable_obj.markings == ["TLP:AMBER"]
        assert observable_obj.create_indicator is True

    @pytest.mark.parametrize(
        ("identifier", "entity_type", "expected_type"),
        [
            ("1.2.3.4", EntityTypes.ADDRESS, "IPv4-Addr"),
            ("2001:db8::1", EntityTypes.ADDRESS, "IPv6-Addr"),
            ("evil.com", EntityTypes.DOMAIN, "Domain-Name"),
            ("host01", EntityTypes.HOSTNAME, "Hostname"),
            ("http://evil.com", EntityTypes.URL, "Url"),
            ("d41d8cd98f00b204e9800998ecf8427e", EntityTypes.FILEHASH, "StixFile"),
            ("evil.exe", EntityTypes.FILENAME, "File-Name"),
            ("attacker@evil.com", EntityTypes.USER, "Email-Addr"),
            ("Phishing subject", EntityTypes.EMAILMESSAGE, "Email-Message"),
        ],
    )
    def test_observable_type_resolution(
        self,
        mock_soar_enrich_action,
        mock_api_client,
        identifier,
        entity_type,
        expected_type,
    ):
        entity = _make_entity(identifier, entity_type)
        mock_soar_enrich_action.parameters = {}
        mock_soar_enrich_action.target_entities = [entity]
        mock_api_client.create_observable.return_value = _created_observable()

        action = CreateObservables(SCRIPT_NAME)
        action.run()

        observable_obj = mock_api_client.create_observable.call_args.args[0]
        assert observable_obj.type == expected_type

    def test_unsupported_entities_are_skipped(
        self, mock_soar_enrich_action, mock_api_client
    ):
        mock_soar_enrich_action.parameters = {}
        mock_soar_enrich_action.target_entities = [
            _make_entity("CVE-2024-1234", EntityTypes.CVE),
            _make_entity("EvilGroup", EntityTypes.THREATACTOR),
        ]

        action = CreateObservables(SCRIPT_NAME)
        action.run()

        mock_api_client.create_observable.assert_not_called()
        assert action.result_value is False
        assert "No entities match the supported entity types" in action.output_message

    def test_mixed_supported_and_unsupported(
        self, mock_soar_enrich_action, mock_api_client
    ):
        supported = _make_entity("evil.com", EntityTypes.DOMAIN)
        unsupported = _make_entity("CVE-2024-1234", EntityTypes.CVE)
        mock_soar_enrich_action.parameters = {}
        mock_soar_enrich_action.target_entities = [supported, unsupported]
        mock_api_client.create_observable.return_value = _created_observable()

        action = CreateObservables(SCRIPT_NAME)
        action.run()

        assert mock_api_client.create_observable.call_count == 1
        assert action.result_value is True
        assert "evil.com" in action.output_message

    def test_partial_failure_reports_failed_entity(
        self, mock_soar_enrich_action, mock_api_client
    ):
        ok_entity = _make_entity("evil.com", EntityTypes.DOMAIN)
        ko_entity = _make_entity("1.2.3.4", EntityTypes.ADDRESS)
        mock_soar_enrich_action.parameters = {}
        mock_soar_enrich_action.target_entities = [ok_entity, ko_entity]

        def side_effect(observable):
            if observable.value == "1.2.3.4":
                raise OpenCTIClientError("API down")
            return _created_observable()

        mock_api_client.create_observable.side_effect = side_effect

        action = CreateObservables(SCRIPT_NAME)
        action.run()

        assert action.result_value is True
        assert "Successfully created the following entities" in action.output_message
        assert "wasn't able to create the following entities" in action.output_message
        assert "1.2.3.4" in action.output_message

    def test_all_failures_set_false_result(
        self, mock_soar_enrich_action, mock_api_client
    ):
        entity = _make_entity("1.2.3.4", EntityTypes.ADDRESS)
        mock_soar_enrich_action.parameters = {}
        mock_soar_enrich_action.target_entities = [entity]
        mock_api_client.create_observable.side_effect = OpenCTIClientError("API down")

        action = CreateObservables(SCRIPT_NAME)
        action.run()

        assert action.result_value is False
        assert "wasn't able to create the following entities" in action.output_message
        entity_result = next(r for r in action.json_results if r["Entity"] == "1.2.3.4")
        assert "API down" in entity_result["EntityResult"]["execution_status"]
