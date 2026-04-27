from __future__ import annotations
import json
import sys
from ..core.InternetStormCenterManager import InternetStormCenterManager
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_dict_to_json_result_dict
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    ENRICH_ENTITIES_SCRIPT_NAME,
    DEFAULT_TIMEOUT,
)
from ..core.UtilsManager import (
    is_approaching_timeout,
    is_async_action_global_timeout_approaching,
)

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS]
ENRICHMENT_PREFIX = "IntStormCentr"


def start_operation(siemplify, manager, suitable_entities, create_insight):
    status = EXECUTION_STATE_INPROGRESS
    result_value = {
        "json_results": {},
        "table_results": {},
        "enrichments": {},
        "insights": {},
        "target_entities": [],
        "successful": [],
        "pending": [],
        "failed": [],
    }

    if suitable_entities:
        for entity in suitable_entities:
            result_value["target_entities"].append(entity.identifier)
            result_value["pending"].append(entity.identifier)

    if result_value["pending"]:
        entity_identifier = result_value["pending"].pop(0)
        try:
            device = manager.get_device(ip_address=entity_identifier)
            if device:
                result_value["json_results"][entity_identifier] = device.to_json()
                result_value["table_results"][entity_identifier] = device.to_csv()
                if create_insight:
                    result_value["insights"][entity_identifier] = device.to_insight()
                result_value["enrichments"][entity_identifier] = (
                    device.to_enrichment_data(prefix=ENRICHMENT_PREFIX)
                )
                result_value["successful"].append(entity_identifier)
            else:
                siemplify.LOGGER.info(
                    f"Device was not found for entity {entity_identifier}. Skipping."
                )
                result_value["failed"].append(entity_identifier)
        except Exception as e:
            result_value["failed"].append(entity_identifier)
            siemplify.LOGGER.error(
                f"An error occurred on entity {entity_identifier}"
            )
            siemplify.LOGGER.exception(e)

    if result_value["pending"]:
        output_message = (
            "Waiting for enrichment to finish on the following entities:"
            f' {", ".join(result_value["pending"])}'
        )
        result_value = json.dumps(result_value)
        return output_message, result_value, status

    output_message, result_value, status = finish_operation(
        siemplify=siemplify,
        result_data=result_value,
        timeout_approaching=False,
        suitable_entities=suitable_entities,
        create_insight=create_insight,
    )

    return output_message, result_value, status


def query_operation_status(
    siemplify,
    manager,
    action_start_time,
    result_data,
    create_insight,
    suitable_entities,
):
    timeout_approaching = False

    if is_async_action_global_timeout_approaching(
        siemplify, action_start_time
    ) or is_approaching_timeout(action_start_time, DEFAULT_TIMEOUT):
        siemplify.LOGGER.info("Timeout is approaching. Action will gracefully exit")
        timeout_approaching = True
    else:
        if result_data["pending"]:
            entity_identifier = result_data["pending"].pop(0)
            try:
                device = manager.get_device(ip_address=entity_identifier)
                if device:
                    result_data["json_results"][entity_identifier] = device.to_json()
                    result_data["table_results"][entity_identifier] = device.to_csv()
                    if create_insight:
                        result_data["insights"][entity_identifier] = device.to_insight()
                    result_data["enrichments"][entity_identifier] = (
                        device.to_enrichment_data(prefix=ENRICHMENT_PREFIX)
                    )
                    result_data["successful"].append(entity_identifier)
                else:
                    siemplify.LOGGER.info(
                        f"Device was not found for entity {entity_identifier}. Skipping."
                    )
                    result_data["failed"].append(entity_identifier)
            except Exception as e:
                result_data["failed"].append(entity_identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity_identifier}"
                )
                siemplify.LOGGER.exception(e)

        if result_data["pending"]:
            output_message = (
                "Waiting for enrichment to finish on the following entities:"
                f' {", ".join(result_data["pending"])}'
            )
            result_value = json.dumps(result_data)
            return output_message, result_value, EXECUTION_STATE_INPROGRESS

    output_message, result_value, status = finish_operation(
        siemplify=siemplify,
        result_data=result_data,
        timeout_approaching=timeout_approaching,
        suitable_entities=suitable_entities,
        create_insight=create_insight,
    )

    return output_message, result_value, status


def finish_operation(
    siemplify, result_data, timeout_approaching, suitable_entities, create_insight
):
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_entities = result_data["successful"]
    failed_entities = result_data["failed"]
    pending_entities = result_data["pending"]

    if successful_entities:
        output_message += (
            "Successfully enriched the following entities using information"
            f" from {INTEGRATION_DISPLAY_NAME}:"
            f'{", ".join(list(successful_entities))}\n'
            
        )
        for identifier in successful_entities:
            enriched_entity = next(
                (
                    entity
                    for entity in suitable_entities
                    if entity.identifier == identifier
                ),
                None,
            )
            if enriched_entity:
                enriched_entity.is_enriched = True
                enriched_entity.additional_properties.update(
                    result_data["enrichments"][identifier]
                )
                siemplify.update_entities([enriched_entity])
                if create_insight:
                    siemplify.add_entity_insight(
                        enriched_entity, result_data["insights"][identifier]
                    )
            siemplify.result.add_entity_table(
                identifier, construct_csv([result_data["table_results"][identifier]])
            )
        siemplify.result.add_result_json(
            convert_dict_to_json_result_dict(result_data["json_results"])
        )

    if failed_entities:
        output_message += (
            "Action wasn't able to enrich the following entities using"
            f" information from {INTEGRATION_DISPLAY_NAME}:"
            f'{", ".join(list(failed_entities))}\n'
        )

    if timeout_approaching and pending_entities:
        err = (
            "action ran into a timeout. Pending entities: "
            f'{", ".join(list(pending_entities))}'
            "\nPlease increase the timeout in IDE."
        )

        error_message = f"Error executing action {ENRICH_ENTITIES_SCRIPT_NAME}. Reason: {err}"
        siemplify.LOGGER.error(error_message)
        output_message = f"{error_message}\n{output_message}"
        result_value = False
        status = EXECUTION_STATE_FAILED

        return output_message, result_value, status

    if not successful_entities:
        result_value = False
        if not failed_entities:
            output_message = "No supported entities were found in the scope."
        else:
            output_message = "None of the provided entities were enriched."

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = ENRICH_ENTITIES_SCRIPT_NAME
    mode = "Main" if is_first_run else "Enrich Entities"
    siemplify.LOGGER.info(
        f"----------------- {mode} - Param Init -----------------"
    )

    email_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Email Address",
        is_mandatory=True,
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Action parameters
    create_insight = extract_action_param(
        siemplify,
        param_name="Create Insight",
        default_value=True,
        print_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info(
        f"----------------- {mode} - Started -----------------"
    )

    result_value = False
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        manager = InternetStormCenterManager(
            email_address=email_address,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify=siemplify,
                manager=manager,
                suitable_entities=suitable_entities,
                create_insight=create_insight,
            )
        else:
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
                action_start_time=action_start_time,
                result_data=json.loads(result_data),
                create_insight=create_insight,
                suitable_entities=suitable_entities,
            )

    except Exception as err:
        output_message = f"Error executing action {ENRICH_ENTITIES_SCRIPT_NAME}. Reason: {err}"
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info(
        "----------------- {} - Finished -----------------".format(mode)
    )
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
