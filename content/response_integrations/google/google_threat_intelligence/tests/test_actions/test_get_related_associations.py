from __future__ import annotations

from itertools import chain

from unittest.mock import MagicMock

from TIPCommon.base.action import EntityTypesEnum, ExecutionState

from google_threat_intelligence.actions import (
    get_related_associations,
)
from google_threat_intelligence.core.constants import (
    GET_RELATED_ASSOCIATIONS_SCRIPT_NAME,
    INTEGRATION_DISPLAY_NAME,
)

from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.requests.response import MockResponse
from integration_testing.set_meta import set_metadata

from google_threat_intelligence.tests.common import CONFIG_PATH
from google_threat_intelligence.tests.core.session import (
    GoogleThreatIntelligenceSession,
    GoogleThreatIntelligenceSdkSession
)
from google_threat_intelligence.tests.responses.api import common_responses


TEST_CASE_ID = 1

supported_entities = {
    EntityTypesEnum.URL: "https://example.com",
    EntityTypesEnum.ADDRESS: "8.8.8.8",
    EntityTypesEnum.HOST_NAME: "example",
    EntityTypesEnum.DOMAIN: "example.com",
    EntityTypesEnum.FILE_HASH: "filehash",
}

association_groups = {"collection", "report", "threat-actor", "malware-family"}


@set_metadata(
    input_context={"case_id": TEST_CASE_ID},
    integration_config_file_path=CONFIG_PATH,
    parameters={"Create Entity": True},
    entities=[create_entity(_id, _type) for _type, _id in supported_entities.items()]
)
def test_get_related_associations_create_entity_true(
    script_session: GoogleThreatIntelligenceSession,
    sdk_session: GoogleThreatIntelligenceSdkSession,
    action_output: MockActionOutput,
):
    """Test the action runs correctly when 'Create Entity' is True."""
    get_related_associations.main()

    create_entity_requests = [
        r for r in sdk_session.request_history
        if r.request.url.path == "/api/external/v1/sdk/CreateEntity"
    ]
    assert len(create_entity_requests) == 1

    create_relation_requests = [
        r for r in sdk_session.request_history
        if r.request.url.path == "/api/external/v1/investigator/ExtendCaseGraph"
    ]
    assert len(create_relation_requests) == 5

    associations_requests = [
        r for r in script_session.request_history
        if "associations" in r.request.url.path
    ]
    assert len(associations_requests) == 5

    reports_requests = [
        r
        for r in script_session.request_history
        if "reports" in r.request.url.path
    ]
    assert len(reports_requests) == 5

    assert action_output.results.output_message == (
        "Successfully found associations for the following entities "
        f"in {INTEGRATION_DISPLAY_NAME}:\n"
        f"{', '.join(supported_entities.values())}"
    )

    json_result = action_output.results.json_output.json_result
    assert len(json_result) == len(supported_entities)

    expected_entities = set(supported_entities.values())
    for entity in json_result:
        assert entity["Entity"] in expected_entities
        assert set(entity["EntityResult"].keys()) == association_groups

    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED

@set_metadata(
    input_context={"case_id": TEST_CASE_ID},
    integration_config_file_path=CONFIG_PATH,
    parameters={"Create Entity": False},
    entities=[
        create_entity(
            supported_entities[EntityTypesEnum.ADDRESS], EntityTypesEnum.ADDRESS
        ),
    ],
)
def test_get_related_associations_create_entity_false(
    sdk_session: GoogleThreatIntelligenceSdkSession,
    action_output: MockActionOutput,
):
    """Test the action runs correctly when 'Create Entity' is False."""
    get_related_associations.main()

    post_requests = [
        r for r in sdk_session.request_history
        if r.request.url.path in {
            "/api/external/v1/sdk/CreateEntity",
            "/api/external/v1/investigator/ExtendCaseGraph",
        }
    ]
    assert not post_requests, "No entities or relationships should be created."

    assert action_output.results.output_message == (
        "Successfully found associations for the following entities "
        f"in {INTEGRATION_DISPLAY_NAME}:\n{supported_entities[EntityTypesEnum.ADDRESS]}"
    )

    json_result = action_output.results.json_output.json_result
    assert len(json_result) == 1
    assert json_result[0]["Entity"] == supported_entities[EntityTypesEnum.ADDRESS]
    assert set(json_result[0]["EntityResult"].keys()) == association_groups

    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    input_context={"case_id": TEST_CASE_ID},
    integration_config_file_path=CONFIG_PATH,
    parameters={"Create Entity": False, "Association Types": "Threat Actor, Campaign"},
    entities=[
        create_entity(
            supported_entities[EntityTypesEnum.ADDRESS], EntityTypesEnum.ADDRESS
        ),
    ],
)
def test_get_related_associations_filter_association_types(
    action_output: MockActionOutput,
    script_session: GoogleThreatIntelligenceSession,
):
    """Test that association types are correctly filtered based on parameters."""
    content = {
        **common_responses.RELATED_ASSOCIATIONS_RESPONSE,
        "data": [
            item for item in common_responses.RELATED_ASSOCIATIONS_RESPONSE["data"]
            if item["attributes"]["collection_type"] in ["threat-actor", "campaign"]
        ],
    }

    handler = MagicMock()
    handler.side_effect = [MockResponse(content=content, status_code=200)]
    script_session.routes["GET"]["/api/v3/ip_addresses/[0-9.]+/associations"] = handler

    get_related_associations.main()

    reports_requests = [
        r for r in script_session.request_history if "reports" in r.request.url.path
    ]
    assert len(reports_requests) == 0

    assert action_output.results.output_message == (
        "Successfully found associations for the following entities "
        f"in {INTEGRATION_DISPLAY_NAME}:\n{supported_entities[EntityTypesEnum.ADDRESS]}"
    )

    associations_requests = [
        r
        for r in script_session.request_history
        if "associations" in r.request.url.path
    ]
    assert len(associations_requests) == 1
    assert associations_requests[0].request.kwargs["params"]["filter"] == (
        '(collection_type:"threat-actor" OR collection_type:"campaign")'
    )

    reports_requests = [
        r for r in script_session.request_history if "reports" in r.request.url.path
    ]
    assert len(reports_requests) == 0

    json_result = action_output.results.json_output.json_result
    assert len(json_result) == 1
    assert json_result[0]["Entity"] == supported_entities[EntityTypesEnum.ADDRESS]
    assert set(json_result[0]["EntityResult"].keys()) == {"threat-actor"}

    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    input_context={"case_id": TEST_CASE_ID},
    integration_config_file_path=CONFIG_PATH,
    parameters={"Create Entity": False, "Association Types": "Campaign"},
    entities=[
        create_entity(
            supported_entities[EntityTypesEnum.ADDRESS], EntityTypesEnum.ADDRESS
        ),
    ],
)
def test_get_related_associations_filter_association_types_no_suitable_types(
    action_output: MockActionOutput,
    script_session: GoogleThreatIntelligenceSession,
):
    """Test behavior when association filters result in no matches."""
    content = {
        **common_responses.RELATED_ASSOCIATIONS_RESPONSE,
        "data": [
            item
            for item in common_responses.RELATED_ASSOCIATIONS_RESPONSE["data"]
            if item["attributes"]["collection_type"] == "campaign"
        ],
    }

    handler = MagicMock()
    handler.side_effect = [MockResponse(content=content, status_code=200)]
    script_session.routes["GET"]["/api/v3/ip_addresses/[0-9.]+/associations"] = handler

    get_related_associations.main()

    reports_requests = [
        r for r in script_session.request_history if "reports" in r.request.url.path
    ]
    assert len(reports_requests) == 0

    assert action_output.results.output_message == (
        "No related associations were found for the provided entities "
        f"in {INTEGRATION_DISPLAY_NAME}."
    )

    assert action_output.results.json_output is None
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    input_context={"case_id": TEST_CASE_ID},
    integration_config_file_path=CONFIG_PATH,
    parameters={"Create Entity": True},
    entities=[create_entity("unsupported_user", EntityTypesEnum.USER)],
)
def test_get_related_associations_no_supported_entities(
    script_session: GoogleThreatIntelligenceSession,
    sdk_session: GoogleThreatIntelligenceSdkSession,
    action_output: MockActionOutput,
):
    """Test graceful exit when no supported entities are provided."""
    get_related_associations.main()

    post_requests = [
        r
        for r in sdk_session.request_history
        if r.request.url.path in {
            "/api/external/v1/sdk/CreateEntity",
            "/api/external/v1/investigator/ExtendCaseGraph",
        }
    ]
    assert not post_requests, "No entities or relationships should be created."

    associations_requests = [
        r for r in script_session.request_history
        if "associations" in r.request.url.path
    ]
    assert not associations_requests, "API should not be called for associations."

    assert action_output.results.output_message == (
        f"No supported entities were found to process in {INTEGRATION_DISPLAY_NAME}."
    )
    assert action_output.results.json_output is None
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    input_context={"case_id": TEST_CASE_ID},
    integration_config_file_path=CONFIG_PATH,
    parameters={"Create Entity": False},
    entities=[
        create_entity(
            supported_entities[EntityTypesEnum.ADDRESS], EntityTypesEnum.ADDRESS
        ),
        create_entity("1.1.1.1", EntityTypesEnum.ADDRESS),
    ],
)
def test_get_related_associations_api_error_for_one_entity(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
):
    """Test error handling when the API fails for one of multiple entities."""
    handler = MagicMock()
    handler.side_effect = [
        MockResponse(
            content=common_responses.RELATED_ASSOCIATIONS_RESPONSE,
            status_code=200,
        ),
        MockResponse(status_code=400),
    ]
    script_session.routes["GET"]["/api/v3/ip_addresses/[0-9.]+/associations"] = handler

    get_related_associations.main()

    success_message_part = (
        "Successfully found associations for the following entities "
        f"in {INTEGRATION_DISPLAY_NAME}:\n{supported_entities[EntityTypesEnum.ADDRESS]}"
    )
    assert success_message_part in action_output.results.output_message

    failure_message_part = (
        "No related associations were found for the following entities "
        f"in {INTEGRATION_DISPLAY_NAME}:\n1.1.1.1"
    )
    assert failure_message_part in action_output.results.output_message

    json_result = action_output.results.json_output.json_result
    assert len(json_result) == 1
    assert json_result[0]["Entity"] == supported_entities[EntityTypesEnum.ADDRESS]

    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    input_context={"case_id": TEST_CASE_ID},
    integration_config_file_path=CONFIG_PATH,
    parameters={"Association Types": "Invalid Type"},
    entities=[
        create_entity(
            supported_entities[EntityTypesEnum.ADDRESS], EntityTypesEnum.ADDRESS
        ),],
)
def test_get_related_associations_invalid_association_type_raises_error(
    action_output: MockActionOutput,
):
    """Test that an invalid 'Association Type' raises a ParameterValidationError."""
    get_related_associations.main()

    available_options = ", ".join(
        f"'{key}'" for key in get_related_associations.COLLECTION_TYPE_TO_IOC_MAPPING
    )
    assert action_output.results.output_message == (
        f"Error executing action \"{GET_RELATED_ASSOCIATIONS_SCRIPT_NAME}\"\n"
        "Reason: Invalid parameter \"Association Types\". "
        f"Available options are: [{available_options}]. Wrong value provided: "
        "['Invalid Type']"
    )

    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(
    input_context={"case_id": TEST_CASE_ID},
    integration_config_file_path=CONFIG_PATH,
    parameters={"Create Entity": False, "Max Associations To Return": 1},
    entities=[
        create_entity(
            supported_entities[EntityTypesEnum.ADDRESS], EntityTypesEnum.ADDRESS
        ),
    ],
)
def test_get_related_associations_max_associations_limit(
    action_output: MockActionOutput,
    script_session: GoogleThreatIntelligenceSession,
):
    """Test that 'Max Associations To Return' correctly limits the results."""
    get_related_associations.main()

    reports_requests = [
        r for r in script_session.request_history if "reports" in r.request.url.path
    ]
    assert len(reports_requests) == 0

    json_result = action_output.results.json_output.json_result
    entity_result_values = list(
        chain.from_iterable(json_result[0]["EntityResult"].values())
    )
    assert len(entity_result_values) == 1

    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    input_context={"case_id": TEST_CASE_ID},
    integration_config_file_path=CONFIG_PATH,
    parameters={"Create Entity": False, "Max Associations To Return": 5},
    entities=[
        create_entity(
            supported_entities[EntityTypesEnum.ADDRESS], EntityTypesEnum.ADDRESS
        ),
    ],
)
def test_get_related_associations_with_reports_max_associations_limit(
    action_output: MockActionOutput,
    script_session: GoogleThreatIntelligenceSession,
):
    """Test that 'Max Associations To Return' correctly limits the results."""
    get_related_associations.main()

    reports_requests = [
        r for r in script_session.request_history if "reports" in r.request.url.path
    ]
    assert len(reports_requests) == 1

    json_result = action_output.results.json_output.json_result
    entity_result_values = list(
        chain.from_iterable(json_result[0]["EntityResult"].values())
    )
    assert len(entity_result_values) == 5

    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    input_context={"case_id": TEST_CASE_ID},
    integration_config_file_path=CONFIG_PATH,
    parameters={"Create Entity": False, "Max Associations To Return": 100},
    entities=[
        create_entity(
            supported_entities[EntityTypesEnum.ADDRESS], EntityTypesEnum.ADDRESS
        ),
    ],
)
def test_get_related_associations_max_associations_limit_more_than_default_value(
    action_output: MockActionOutput,
):
    """Test that 'Max Associations To Return' correctly limits the results."""
    get_related_associations.main()

    json_result = action_output.results.json_output.json_result
    entity_result_values = list(
        chain.from_iterable(json_result[0]["EntityResult"].values())
    )
    assert len(entity_result_values) == 6

    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    input_context={"case_id": TEST_CASE_ID},
    integration_config_file_path=CONFIG_PATH,
    parameters={"Create Entity": False, "Max Associations To Return": 1001},
    entities=[
        create_entity(
            supported_entities[EntityTypesEnum.ADDRESS], EntityTypesEnum.ADDRESS
        ),
    ],
)
def test_get_related_associations_max_associations_limit_more_than_max_value(
    action_output: MockActionOutput,
):
    """Test that 'Max Associations To Return' correctly limits the results."""
    get_related_associations.main()

    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED

    assert action_output.results.output_message == (
        f"Error executing action \"{GET_RELATED_ASSOCIATIONS_SCRIPT_NAME}\"\n"
        "Reason: Invalid parameter \"Max Associations To Return\". "
        "The value must be between 1 and 1000. Wrong value provided: 1001"
    )
