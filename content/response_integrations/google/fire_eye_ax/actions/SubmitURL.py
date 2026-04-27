from __future__ import annotations
import json
import sys
from ..core.FireEyeAXManager import FireEyeAXManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.Siemplify import InsightSeverity, InsightType
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_dict_to_json_result_dict
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    flat_dict_to_csv,
)
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    SUBMIT_URL_SCRIPT_NAME,
    PRIORITY_MAPPING,
    ANALYSIS_TYPE_MAPPING,
    SUBMISSION_DONE,
    DEFAULT_TIMEOUT,
)
from ..core.UtilsManager import (
    get_entity_original_identifier,
    is_approaching_timeout,
    is_async_action_global_timeout_approaching,
)


SUPPORTED_ENTITY_TYPES = [EntityTypes.URL]
ENRICHMENT_PREFIX = "FEYEAX"


def start_operation(
    siemplify,
    manager,
    suitable_entities,
    vm_profile,
    app_id,
    priority,
    force_rescan,
    analysis_type,
    create_insight,
):
    status = EXECUTION_STATE_INPROGRESS
    result_value = {
        "json_results": {},
        "table_results": {},
        "enrichment_results": {},
        "insights": {},
        "submission_ids": {},
        "completed": [],
        "failed": [],
    }

    if suitable_entities:
        for entity in suitable_entities:
            try:
                submission = manager.get_data(
                    priority=PRIORITY_MAPPING.get(priority),
                    profile=vm_profile,
                    application=app_id,
                    force_rescan=force_rescan,
                    analysis_type=ANALYSIS_TYPE_MAPPING.get(analysis_type),
                    url=entity.identifier,
                )
                result_value["submission_ids"][entity.identifier] = submission.id
            except Exception:
                result_value["failed"].append(entity.identifier)

    if result_value["submission_ids"]:
        for key, value in result_value["submission_ids"].items():
            submission = manager.get_submission_status(value)
            if submission.status == SUBMISSION_DONE:
                submission_result = manager.get_submission_details(submission.result_id)
                result_value["json_results"][key] = submission_result.to_json()
                result_value["table_results"][key] = submission_result.to_table()
                result_value["enrichment_results"][key] = (
                    submission_result.to_enrichment_data(prefix=ENRICHMENT_PREFIX)
                )
                result_value["insights"][key] = submission_result.to_insight()
                result_value["completed"].append(key)

        for entity_id, _ in result_value["json_results"].items():
            if entity_id in result_value["submission_ids"]:
                result_value["submission_ids"].pop(entity_id, None)

        if result_value["submission_ids"]:
            output_message = (
                f"Waiting for the following files to be processed: "
                f"{', '.join([key for key, _ in result_value['submission_ids'].items()])}"
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
    suitable_entities,
    create_insight,
):
    timeout_approaching = False

    if is_async_action_global_timeout_approaching(
        siemplify, action_start_time
    ) or is_approaching_timeout(action_start_time, DEFAULT_TIMEOUT):
        siemplify.LOGGER.info("Timeout is approaching. Action will gracefully exit")
        timeout_approaching = True
    else:
        for key, value in result_data["submission_ids"].items():
            submission = manager.get_submission_status(value)
            if submission.status == SUBMISSION_DONE:
                submission_result = manager.get_submission_details(submission.result_id)
                result_data["json_results"][key] = submission_result.to_json()
                result_data["table_results"][key] = submission_result.to_table()
                result_data["enrichment_results"][key] = (
                    submission_result.to_enrichment_data(prefix=ENRICHMENT_PREFIX)
                )
                result_data["insights"][key] = submission_result.to_insight()
                result_data["completed"].append(key)

        for entity_id, _ in result_data["json_results"].items():
            if entity_id in result_data["submission_ids"]:
                result_data["submission_ids"].pop(entity_id, None)

        if result_data["submission_ids"]:
            output_message = (
                f"Waiting for the following files to be processed: "
                f"{', '.join([key for key, _ in result_data['submission_ids'].items()])}"
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
    successful_entities = []
    failed_entities = []
    pending_entities = []
    json_results = result_data.get("json_results", {})
    table_results = result_data.get("table_results", {})
    enrichment_results = result_data.get("enrichment_results", {})
    insights = result_data.get("insights", {})

    for entity in suitable_entities:
        if entity.identifier in result_data["completed"]:
            successful_entities.append(entity)
        elif entity.identifier in result_data["failed"]:
            failed_entities.append(entity)
        else:
            pending_entities.append(entity)

    if timeout_approaching and pending_entities:
        raise Exception(
            f"action ran into a timeout. The following files are still "
            f"processing: {', '.join([entity.identifier for entity in pending_entities])}\n"
            f"Please increase the timeout in IDE. Note: adding the same files will create a separate "
            f"analysis job in FireEye AX."
        )

    if successful_entities:
        for entity in successful_entities:
            entity_identifier = get_entity_original_identifier(entity)
            entity.additional_properties.update(
                enrichment_results.get(entity_identifier)
            )
            entity.is_enriched = True
            siemplify.result.add_entity_table(
                f"{entity_identifier}",
                flat_dict_to_csv(table_results.get(entity_identifier)),
            )
            if create_insight:
                siemplify.create_case_insight(
                    triggered_by=INTEGRATION_NAME,
                    title=entity_identifier,
                    content=insights.get(entity_identifier),
                    entity_identifier=entity_identifier,
                    severity=InsightSeverity.INFO,
                    insight_type=InsightType.General,
                )

        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
        siemplify.update_entities(successful_entities)
        output_message += (
            f"Successfully enriched the following entities using information from "
            f"{INTEGRATION_DISPLAY_NAME}: "
            f"{', '.join([entity.identifier for entity in successful_entities])}\n"
        )

    if failed_entities:
        output_message += (
            f"Action wasn't able to enrich the following entities using information from "
            f"{INTEGRATION_DISPLAY_NAME}: "
            f"{', '.join([entity.identifier for entity in failed_entities])}\n"
        )

    if not successful_entities:
        result_value = False
        output_message = f"None of the provided entities were enriched."

    if not successful_entities and not failed_entities:
        result_value = False
        output_message = f"No supported entities were found in the scope."

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = SUBMIT_URL_SCRIPT_NAME
    mode = "Main" if is_first_run else "Submit URL"
    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )

    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        print_value=False,
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
    vm_profile = extract_action_param(
        siemplify, param_name="VM Profile", is_mandatory=True, print_value=True
    )
    app_id = extract_action_param(
        siemplify, param_name="Application ID", is_mandatory=False, print_value=True
    )
    priority = extract_action_param(
        siemplify, param_name="Priority", is_mandatory=False, print_value=True
    )
    force_rescan = extract_action_param(
        siemplify, param_name="Force Rescan", input_type=bool, print_value=True
    )
    analysis_type = extract_action_param(
        siemplify, param_name="Analysis Type", is_mandatory=False, print_value=True
    )
    create_insight = extract_action_param(
        siemplify, param_name="Create Insight", input_type=bool, print_value=True
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    output_message = ""
    status = EXECUTION_STATE_INPROGRESS
    result_value = False
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        manager = FireEyeAXManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify,
                manager=manager,
                suitable_entities=suitable_entities,
                vm_profile=vm_profile,
                app_id=app_id,
                priority=priority,
                force_rescan=force_rescan,
                analysis_type=analysis_type,
                create_insight=create_insight,
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
                action_start_time=action_start_time,
                result_data=json.loads(result_data),
                suitable_entities=suitable_entities,
                create_insight=create_insight,
            )

    except Exception as err:
        output_message = (
            f"Error executing action {SUBMIT_URL_SCRIPT_NAME}. Reason: {err}"
        )
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
