from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import dict_to_flat, flat_dict_to_csv
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_INPROGRESS
from ..core.CuckooManager import CuckooManager
import sys
import json
from TIPCommon import extract_configuration_param

TASK_KEY = "Cuckoo_task_id"
SCRIPT_NAME = "Cuckoo - DetonateUrl"
INTEGRATION_NAME = "Cuckoo"


def construct_flat_dict_from_report(result_json):
    """
    Create flat JSON from chosen key.
    :param result_json: {dict} JSON result.
    :return: {dict} flat dict.
    """
    result_dict = {}
    if "info" in result_json:
        info = result_json.get("info")
        result_dict["added"] = info.get("added")
        result_dict["duration"] = info.get("duration")
        result_dict["score"] = info.get("score")
        result_dict["id"] = info.get("id")
    if "target" in result_json:
        result_dict.update(dict_to_flat(result_json.get("target")))

    return result_dict


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
    )
    web_interface_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Web Interface Address",
        is_mandatory=True,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File",
        is_mandatory=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=False,
    )

    cuckoo_manager = CuckooManager(
        server_address, web_interface_address, ca_certificate, verify_ssl, api_token
    )
    siemplify.LOGGER.info(f"Connected to Cuckoo {server_address}")

    enriched_entities = []

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.URL:
            task_id = cuckoo_manager.submit_url(entity.identifier)

            # Save a task ID to poll its status in async method
            entity.additional_properties.update({TASK_KEY: task_id})
            siemplify.LOGGER.info(f"Initiated analysis of {entity.identifier}")
            enriched_entities.append(entity)

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]

        output_message = (
            "Analysis was initiated for the following entities\n"
            + "\n".join(entities_names)
        )

        siemplify.update_entities(enriched_entities)

        siemplify.end(output_message, "false", EXECUTION_STATE_INPROGRESS)

    else:
        output_message = "No entities were enriched."
        # No entities found and action is completed - success is False
        siemplify.end(output_message, "false", EXECUTION_STATE_COMPLETED)


def async_analysis():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("Start async")
    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
    )
    web_interface_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Web Interface Address",
        is_mandatory=True,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File",
        is_mandatory=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
    )
    threshold = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Warning Threshold",
        default_value="5.0",
        input_type=str,
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=False,
    )

    cuckoo_manager = CuckooManager(
        server_address, web_interface_address, ca_certificate, verify_ssl, api_token
    )
    siemplify.LOGGER.info(f"Connected to Cuckoo {server_address}")

    uncompleted_entities = []
    completed_entities = []
    results_json = {}

    for entity in siemplify.target_entities:
        try:
            task_id = entity.additional_properties.get(TASK_KEY)
            if task_id:
                # check if report ready first
                if not cuckoo_manager.is_task_reported(task_id):
                    siemplify.LOGGER.info(
                        f"{entity.identifier} Analysis not reported yet"
                    )
                    uncompleted_entities.append(entity)
                else:
                    completed_entities.append(entity)
        except Exception as e:
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(
                f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
            )
            siemplify.LOGGER.exception(e)

    # all ready, get reports and link for all
    if not uncompleted_entities:
        siemplify.LOGGER.info("All completed")

        for entity in completed_entities:
            try:
                task_id = entity.additional_properties.get(TASK_KEY)
                siemplify.LOGGER.info(
                    f"{entity.identifier} Analysis completed. Fetching report for task {task_id}"
                )
                report = cuckoo_manager.get_report(task_id)

                score = report.get("info", {}).get("score", 0)
                siemplify.LOGGER.info(f"Score: {score}")
                entity.additional_properties.update({"Cuckoo_Score": score})
                entity.is_enriched = True
                if score >= float(threshold):
                    entity.is_suspicious = True

                if web_interface_address:
                    siemplify.result.add_entity_link(
                        f"Report Link For Task With ID: {task_id}, For URL: {entity.identifier}",
                        cuckoo_manager.construct_report_url(task_id),
                    )

                siemplify.result.add_data_table(
                    f"Result For Task With ID: {task_id}, For URL: {entity.identifier}",
                    flat_dict_to_csv(construct_flat_dict_from_report(report)),
                )

                results_json[entity.identifier] = report

            except Exception as e:
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                )
                siemplify.LOGGER.exception(e)

        siemplify.update_entities(completed_entities)
        siemplify.result.add_result_json(json.dumps(results_json))
        siemplify.end("Analysis completed", "true", EXECUTION_STATE_COMPLETED)

    else:
        # wait for completion of all
        siemplify.end("Analysis is in progress", "true", EXECUTION_STATE_INPROGRESS)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] == "True":
        main()
    else:
        async_analysis()
