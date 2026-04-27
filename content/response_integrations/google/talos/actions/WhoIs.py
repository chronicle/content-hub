from __future__ import annotations
import json
import sys
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import INTEGRATION_NAME, INTEGRATION_DISPLAY_NAME, WHOIS_SCRIPT_NAME
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from ..core.TalosManager import TalosManager
from ..core.UtilsManager import get_domain_from_entity


SUPPORTED_ENTITY_TYPES = [EntityTypes.HOSTNAME, EntityTypes.ADDRESS, EntityTypes.URL]


def query_entity_report(
    siemplify, manager, entity, successful_entity_identifiers, failed_entity_identifiers
):
    """
    Query entity report
    :param siemplify: SiemplifyAction object
    :param manager: TalosManager manager object
    :param entity: SiemplifyEntity object
    :param successful_entity_identifiers: {list} list of successful entity identifiers
    :param failed_entity_identifiers: {list} list of failed entity identifiers
    :return: {tuple} report, successful_entity_identifiers, failed_entity_identifiers
    """
    siemplify.LOGGER.info(f"\nStarted processing entity: {entity.identifier}")
    report = None

    try:
        # Fetch whois report
        report = manager.get_whois_report(
            get_domain_from_entity(entity.identifier)
            if entity.entity_type == EntityTypes.URL
            else entity.identifier
        )

        successful_entity_identifiers.append(entity.identifier)

    except Exception as e:
        siemplify.LOGGER.error(
            f"Failed processing entities: {entity.identifier}: Error is: {e}"
        )
        failed_entity_identifiers.append(entity.identifier)

    siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}\n")

    return report, successful_entity_identifiers, failed_entity_identifiers


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = WHOIS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use SSL",
        is_mandatory=True,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    additional_data = json.loads(
        extract_action_param(
            siemplify=siemplify, param_name="additional_data", default_value="{}"
        )
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    json_results = additional_data.get("json_results", {})
    successful_entity_identifiers = additional_data.get(
        "successful_entity_identifiers", []
    )
    failed_entity_identifiers = additional_data.get("failed_entity_identifiers", [])
    initial_suitable_entity_identifiers = additional_data.get(
        "initial_suitable_entity_identifiers", []
    )

    if is_first_run:
        suitable_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        ]
    else:
        suitable_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.identifier in initial_suitable_entity_identifiers
        ]

    try:
        talos_manager = TalosManager(use_ssl=use_ssl)
        talos_manager.test_connectivity()
        not_processed_entities = [
            entity
            for entity in suitable_entities
            if entity.identifier
            not in successful_entity_identifiers + failed_entity_identifiers
        ]

        if not_processed_entities:
            current_entity = not_processed_entities[0]
            report, successful_entity_identifiers, failed_entity_identifiers = (
                query_entity_report(
                    siemplify,
                    talos_manager,
                    current_entity,
                    successful_entity_identifiers,
                    failed_entity_identifiers,
                )
            )

            if report:
                json_results[current_entity.identifier] = report.to_json()

        if successful_entity_identifiers:
            output_message += (
                "Successfully returned Whois information about the following entities using "
                "information from {}: \n{}".format(
                    INTEGRATION_DISPLAY_NAME, "\n".join(successful_entity_identifiers)
                )
            )
        if failed_entity_identifiers:
            output_message += (
                "\nAction wasn't able to return Whois information about the following entities "
                "using information from {}: \n{}".format(
                    INTEGRATION_DISPLAY_NAME, "\n".join(failed_entity_identifiers)
                )
            )

        if len(suitable_entities) == len(successful_entity_identifiers) + len(
            failed_entity_identifiers
        ):
            if successful_entity_identifiers:
                siemplify.result.add_result_json(
                    convert_dict_to_json_result_dict(json_results)
                )
            else:
                result = False
                output_message = (
                    "No Whois information was found for the provided entities."
                )
        else:
            status = EXECUTION_STATE_INPROGRESS
            result = json.dumps(
                {
                    "successful_entity_identifiers": successful_entity_identifiers,
                    "failed_entity_identifiers": failed_entity_identifiers,
                    "json_results": json_results,
                    "initial_suitable_entity_identifiers": [
                        entity.identifier for entity in suitable_entities
                    ],
                }
            )

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {WHOIS_SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action {WHOIS_SCRIPT_NAME}. Reason: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
