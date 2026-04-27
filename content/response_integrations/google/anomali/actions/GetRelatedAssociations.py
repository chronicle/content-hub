from __future__ import annotations
import json
import sys
from ..core.AnomaliManager import AnomaliManager, ENDPOINTS_MAPPER
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import (
    INTEGRATION_NAME,
    GET_RELATED_ASSOCIATIONS_SCRIPT_NAME,
    ASSOCIATIONS_TABLE_NAME,
    ENTITY_CREATING_VALID_VALUES_MAPPER,
    ASSOCIATION_TYPE_TO_ENTITY,
    EMAIL_TYPE,
    VULNERABILITY_ASSOCIATION_TYPE,
    CAMPAIGN_ASSOCIATION_TYPE,
    ACTOR_ASSOCIATION_TYPE,
    SIGNATURE_ASSOCIATION_TYPE,
)
from ..core.utils import get_entity_original_identifier, get_entity_type

SUPPORTED_ENTITY_TYPES = [
    EntityTypes.FILEHASH,
    EntityTypes.ADDRESS,
    EntityTypes.URL,
    EMAIL_TYPE,
]
MAX_ASSOCIATIONS_TO_RETURN_DEFAULT = 5


def start_operation(siemplify, manager, suitable_entity_identifiers):
    # Action Parameters
    return_campaigns = extract_action_param(
        siemplify,
        param_name="Return Campaigns",
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    return_threat_bulletins = extract_action_param(
        siemplify,
        param_name="Return Threat Bulletins",
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    return_actors = extract_action_param(
        siemplify,
        param_name="Return Actors",
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    return_attack_patterns = extract_action_param(
        siemplify,
        param_name="Return Attack Patterns",
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    return_courses_of_action = extract_action_param(
        siemplify,
        param_name="Return Courses Of Action",
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    return_identities = extract_action_param(
        siemplify,
        param_name="Return Identities",
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    return_incidents = extract_action_param(
        siemplify,
        param_name="Return Incidents",
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    return_infrastructure = extract_action_param(
        siemplify,
        param_name="Return Infrastructure",
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    return_intrusion_sets = extract_action_param(
        siemplify,
        param_name="Return Intrusion Sets",
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    return_malware = extract_action_param(
        siemplify,
        param_name="Return Malware",
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    return_signatures = extract_action_param(
        siemplify,
        param_name="Return Signatures",
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    return_tools = extract_action_param(
        siemplify,
        param_name="Return Tools",
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    return_ttps = extract_action_param(
        siemplify,
        param_name="Return TTPs",
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    return_vulnerabilities = extract_action_param(
        siemplify,
        param_name="Return Vulnerabilities",
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    max_associations_to_return = extract_action_param(
        siemplify,
        param_name="Max Associations To Return",
        print_value=True,
        input_type=int,
        default_value=MAX_ASSOCIATIONS_TO_RETURN_DEFAULT,
    )

    status = EXECUTION_STATE_COMPLETED
    output_message = "No related associations were found."
    associations_to_process = 0
    # Result value structure in like
    # [{
    #   'association_type': association_type {str},
    #   'in_progress_associations': related_associations {list},
    #   'completed_associations': [] {list}
    # }]
    result_value = {
        "result": [],
        "csv_results": [],
        "entities": [],
        "json_results": {
            "campaign": [],
            "actor": [],
            "attackpattern": [],
            "courseofaction": [],
            "identity": [],
            "incident": [],
            "infrastructure": [],
            "intrusionset": [],
            "malware": [],
            "signature": [],
            "tool": [],
            "ttp": [],
            "vulnerability": [],
            "tipreport": [],
        },
    }
    search_association_types = {
        "Threat Bulletins": return_threat_bulletins,
        "Actors": return_actors,
        "Attack Patterns": return_attack_patterns,
        "Campaigns": return_campaigns,
        "Courses Of Action": return_courses_of_action,
        "Identities": return_identities,
        "Incidents": return_incidents,
        "Infrastructure": return_infrastructure,
        "Intrusion Sets": return_intrusion_sets,
        "Malware": return_malware,
        "Signatures": return_signatures,
        "Tools": return_tools,
        "TTPs": return_ttps,
        "Vulnerabilities": return_vulnerabilities,
    }

    siemplify.LOGGER.info(
        f"Retrieving indicators for entities {', '.join(suitable_entity_identifiers)}"
    )
    # Get indicators for entities
    indicators = manager.get_indicators(entities=suitable_entity_identifiers)

    if not indicators:
        siemplify.LOGGER.info(output_message)
        return output_message, False, status

    for key, value in search_association_types.items():
        # Skip getting for some association_types if property is false
        if not value:
            continue

        association_type = ENDPOINTS_MAPPER[key]
        siemplify.LOGGER.info(f"Getting related associations for association {key}")
        try:
            related_associations = manager.get_associations(
                association_type=association_type,
                indicator_ids=[indicator.id for indicator in indicators],
                limit=max_associations_to_return,
            )

            if related_associations:
                associations_to_process += len(related_associations)
                result_value["result"].append(
                    {
                        "association_type": association_type,
                        "in_progress_association_ids": [
                            association.id for association in related_associations
                        ],
                        "completed_association_ids": [],
                    }
                )

        except Exception as e:
            siemplify.LOGGER.error(
                f"Failed to get related associations for association type {key}"
            )
            siemplify.LOGGER.exception(e)

    if associations_to_process > 0:
        status = EXECUTION_STATE_INPROGRESS
        result_value = json.dumps(result_value)
        output_message = "Waiting for all of the association details to be retrieved"
    else:
        siemplify.LOGGER.info(output_message)
        result_value = False

    return output_message, result_value, status


def query_operation_status(siemplify, manager):
    results = json.loads(
        siemplify.extract_action_param("additional_data", default_value="{}")
    )

    for result_json in results["result"]:
        association_type = result_json["association_type"]
        completed_ids, failed_ids = [], []
        processing_ids = result_json["in_progress_association_ids"].copy()

        for association_id in processing_ids:
            try:
                association_details = manager.get_association_details(
                    association_type=association_type, association_id=association_id
                )
                results["json_results"][association_type].append(
                    association_details.to_json()
                )
                results["csv_results"].append(
                    association_details.to_table(association_type=association_type)
                )
                if association_type in ENTITY_CREATING_VALID_VALUES_MAPPER:
                    results["entities"].append(
                        (association_type, association_details.name)
                    )
                completed_ids.append(association_id)
            except Exception as e:
                failed_ids.append(association_id)
                siemplify.LOGGER.error(
                    f"Failed to get association details for association {association_id}"
                )
                siemplify.LOGGER.exception(e)

        # Remove completed ids from in progress ids
        result_json["in_progress_association_ids"] = [
            in_progress_id
            for in_progress_id in result_json["in_progress_association_ids"]
            if in_progress_id not in completed_ids
        ]
        # Remove failed ids from in progress ids for run away from limitless cycle
        result_json["in_progress_association_ids"] = [
            in_progress_id
            for in_progress_id in result_json["in_progress_association_ids"]
            if in_progress_id not in failed_ids
        ]
        # Update completed ids
        result_json["completed_association_ids"].extend(completed_ids)

    if not all_association_details_ready(siemplify=siemplify, results=results):
        status = EXECUTION_STATE_INPROGRESS
        result_value = json.dumps(results)
        output_message = "Waiting for all of the association details to be retrieved"
    else:
        output_message, result_value, status = finish_operation(siemplify, results)

    return output_message, result_value, status


def finish_operation(siemplify, results):
    create_campaign_entity = extract_action_param(
        siemplify,
        param_name="Create Campaign Entity",
        input_type=bool,
        print_value=True,
        default_value=False,
    )
    create_actors_entity = extract_action_param(
        siemplify,
        param_name="Create Actors Entity",
        input_type=bool,
        print_value=True,
        default_value=False,
    )
    create_signature_entity = extract_action_param(
        siemplify,
        param_name="Create Signature Entity",
        input_type=bool,
        print_value=True,
        default_value=False,
    )
    create_vulnerability_entity = extract_action_param(
        siemplify,
        param_name="Create Vulnerability Entity",
        input_type=bool,
        print_value=True,
        default_value=False,
    )
    supported_association_types_mapper = {
        VULNERABILITY_ASSOCIATION_TYPE: create_vulnerability_entity,
        CAMPAIGN_ASSOCIATION_TYPE: create_campaign_entity,
        ACTOR_ASSOCIATION_TYPE: create_actors_entity,
        SIGNATURE_ASSOCIATION_TYPE: create_signature_entity,
    }

    output_message = "No related associations were found."
    result_value = False
    status = EXECUTION_STATE_COMPLETED

    # Check if exists any type of association with result
    not_empty_json_result = bool(
        [data for data in results["json_results"].values() if data]
    )

    if not_empty_json_result:
        # If exists any type of association with result add json result
        siemplify.result.add_result_json(
            {key: value for key, value in results["json_results"].items() if value}
        )
        # If exists any type of association with result add csv table
        siemplify.result.add_data_table(
            ASSOCIATIONS_TABLE_NAME, construct_csv(results["csv_results"])
        )
        output_message = (
            f"Successfully retrieved related associations from {INTEGRATION_NAME}"
        )
        result_value = True

    creating_entities_list = []
    for entity_data in results["entities"]:
        if supported_association_types_mapper[entity_data[0]]:
            # Collect creating entity list by type and provided property for that type
            creating_entities_list.append(
                (ASSOCIATION_TYPE_TO_ENTITY[entity_data[0]], entity_data[1])
            )

    # Create Siemplify entity with provided type and value
    for entity_data in creating_entities_list:
        siemplify.add_entity_to_case(
            entity_data[1],
            entity_data[0],
            is_internal=False,
            is_suspicous=False,
            is_enriched=False,
            is_vulnerable=True,
            properties={"is_new_entity": True},
        )

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_RELATED_ASSOCIATIONS_SCRIPT_NAME
    mode = "Main" if is_first_run else "Check changes"

    siemplify.LOGGER.info(f"-------------- {mode} - Param Init ---------------")

    api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Root"
    )
    username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Username"
    )
    api_key = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Key"
    )

    siemplify.LOGGER.info(f"-------------- {mode} - Started --------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = False
    output_message = "No related associations were found."
    suitable_entity_identifiers = [
        get_entity_original_identifier(entity)
        for entity in siemplify.target_entities
        if get_entity_type(entity) in SUPPORTED_ENTITY_TYPES
    ]

    try:
        manager = AnomaliManager(
            api_root=api_root,
            username=username,
            api_key=api_key,
            force_check_connectivity=True,
            logger=siemplify.LOGGER,
        )

        if is_first_run:
            if suitable_entity_identifiers:
                output_message, result_value, status = start_operation(
                    siemplify=siemplify,
                    manager=manager,
                    suitable_entity_identifiers=suitable_entity_identifiers,
                )
        else:
            output_message, result_value, status = query_operation_status(
                siemplify=siemplify, manager=manager
            )

    except Exception as e:
        output_message = f"Error executing action '{GET_RELATED_ASSOCIATIONS_SCRIPT_NAME}'. Reason: {e}"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    siemplify.LOGGER.info(f"-------------- {mode} - Finished --------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


def all_association_details_ready(siemplify, results):
    for result in results["result"]:
        # If there in any result with in_progress_association_ids that means it should still be in progress
        if len(result["in_progress_association_ids"]):
            siemplify.LOGGER.info(
                f"{result['association_type']} still have not completed records."
            )
            return False

    return True


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
