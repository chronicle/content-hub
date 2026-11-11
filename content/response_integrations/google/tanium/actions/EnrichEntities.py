from __future__ import annotations
import json
import sys
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    flat_dict_to_csv,
)
from tanium.core.TaniumManager import TaniumManager
from tanium.core.TaniumParser import TaniumParser
from soar_sdk.SiemplifyDataModel import EntityTypes
from tanium.core.constants import INTEGRATION_NAME, ENRICH_ENTITIES_SCRIPT_NAME
from tanium.core.exceptions import TaniumBadRequestException
from tanium.core.utils import get_entity_original_identifier, string_to_multi_value


SUPPORTED_ENTITY_TYPES = [EntityTypes.HOSTNAME, EntityTypes.ADDRESS]


def start_operation(siemplify, manager, suitable_entities):
    additional_fields = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="Additional Fields", print_value=True
        )
    )

    successful_entities, failed_entities = [], []
    result_value = {
        "in_progress": {},
        "completed": {},
        "failed": [],
        "data_loads_count": {},
    }
    status = EXECUTION_STATE_INPROGRESS

    for entity in suitable_entities:
        entity_identifier = get_entity_original_identifier(entity)
        siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")

        try:
            question = manager.create_question_for_machine(
                entity_identifier, entity.entity_type, additional_fields
            )
            result_value["in_progress"][entity_identifier] = question.id
            result_value["data_loads_count"][entity_identifier] = 0
            successful_entities.append(entity_identifier)
        except Exception as err:
            if isinstance(err, TaniumBadRequestException):
                raise
            failed_entities.append(entity_identifier)
            result_value["failed"].append(entity_identifier)
            siemplify.LOGGER.error(f"An error occurred on entity {entity_identifier}")
            siemplify.LOGGER.exception(err)

    if successful_entities:
        result_value = json.dumps(result_value)
        output_message = f"Successfully created question for entities: {', '.join(successful_entities)}."
    else:
        output_message = f"None of the provided entities were enriched."
        result_value = False
        status = EXECUTION_STATE_COMPLETED

    return output_message, result_value, status


def query_operation_status(siemplify, manager, result_data, suitable_entities):
    completed_entities = {}
    failed_entities = []

    for entity_identifier, question_id in result_data["in_progress"].items():
        try:
            question_data = manager.get_question_result(question_id)
            if question_data.rows:
                completed_entities[entity_identifier] = question_data.raw_data
            else:
                if result_data["data_loads_count"][entity_identifier] > 2:
                    failed_entities.append(entity_identifier)
                    siemplify.LOGGER.info(
                        f"Could not found data for question with id {question_id} in entity "
                        f"{entity_identifier} list."
                    )
            result_data["data_loads_count"][entity_identifier] += 1
        except Exception as err:
            siemplify.LOGGER.error(f"An error occurred on question_id {question_id}")
            siemplify.LOGGER.exception(err)

    for key in completed_entities.keys():
        result_data["in_progress"].pop(key)

    result_data["completed"].update(completed_entities)

    for entity in failed_entities:
        result_data["in_progress"].pop(entity)

    result_data["failed"].extend(failed_entities)

    if result_data["in_progress"]:
        status = EXECUTION_STATE_INPROGRESS
        result_value = json.dumps(result_data)
        output_message = (
            f"Waiting for question results to finish on the following entities: "
            f"{', '.join(result_data['in_progress'].keys())}"
        )
    else:
        output_message, result_value, status = finish_operation(
            siemplify, suitable_entities=suitable_entities, result_data=result_data
        )

    return output_message, result_value, status


def finish_operation(siemplify, suitable_entities, result_data):
    result_value = True
    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    failed_entities = result_data["failed"]
    successful_entities, json_results = [], {}
    parser = TaniumParser()

    for entity in suitable_entities:
        entity_identifier = get_entity_original_identifier(entity)
        try:
            if entity_identifier in result_data["completed"].keys():
                question_result = parser.build_question_result_obj(
                    result_data["completed"][entity_identifier]
                )

                json_results[entity_identifier] = question_result.to_enrichment_json()
                siemplify.result.add_entity_table(
                    entity_identifier,
                    flat_dict_to_csv(question_result.to_enrichment_csv()),
                )
                entity.additional_properties.update(question_result.to_enrichment())
                entity.is_enriched = True
                successful_entities.append(entity)

        except Exception as err:
            siemplify.LOGGER.error(f"An error occurred on entity {entity_identifier}")
            siemplify.LOGGER.exception(err)
            failed_entities.append(entity_identifier)

    if json_results:
        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

    if successful_entities:
        output_message = (
            f"Successfully enriched the following entities using information from {INTEGRATION_NAME}: "
            f"{', '.join([get_entity_original_identifier(entity) for entity in successful_entities])}"
        )
        siemplify.update_entities(successful_entities)

        if failed_entities:
            output_message += (
                f"\nAction wasn't able to enrich the following entities using information from "
                f"{INTEGRATION_NAME}: {', '.join(failed_entities)}"
            )

    else:
        output_message = "None of the provided entities were enriched."
        result_value = False

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENTITIES_SCRIPT_NAME
    mode = "Main" if is_first_run else "Get Report"
    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    output_message = ""
    status = EXECUTION_STATE_INPROGRESS
    result_value = False
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = TaniumManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
            logger=siemplify.LOGGER,
        )

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify, manager=manager, suitable_entities=suitable_entities
            )
        if status == EXECUTION_STATE_INPROGRESS:
            result_data = (
                result_value
                if result_value
                else extract_action_param(
                    siemplify, param_name="additional_data", default_value="{}"
                )
            )
            output_message, result_value, status = query_operation_status(
                siemplify=siemplify,
                manager=manager,
                result_data=json.loads(result_data),
                suitable_entities=suitable_entities,
            )

    except Exception as err:
        output_message = (
            f"Error executing action {ENRICH_ENTITIES_SCRIPT_NAME}. Reason: {err}"
        )
        if isinstance(err, TaniumBadRequestException):
            output_message = (
                f"Error executing action {ENRICH_ENTITIES_SCRIPT_NAME} because provided question "
                "text is invalid. "
            )
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
