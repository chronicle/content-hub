from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import dict_to_flat, flat_dict_to_csv
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_INPROGRESS
from ..core.CuckooManager import CuckooManager
import sys
import json
from TIPCommon import extract_configuration_param, extract_action_param

SCRIPT_NAME = "Cuckoo - DetonateFile"
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

    file_paths = extract_action_param(
        siemplify,
        param_name="File Paths",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )
    file_paths = file_paths.split(",")

    cuckoo_manager = CuckooManager(
        server_address, web_interface_address, ca_certificate, verify_ssl, api_token
    )
    siemplify.LOGGER.info(f"Connected to Cuckoo {server_address}")

    task_ids = []

    for file_path in file_paths:
        task_ids.append((file_path, cuckoo_manager.submit_file(file_path)))

    siemplify.LOGGER.info(f"Submitted {len(task_ids)} tasks.")
    siemplify.end(
        f"Initiated tasks {', '.join([str(task_id) for file_path, task_id in task_ids])}.",
        json.dumps(task_ids),
        EXECUTION_STATE_INPROGRESS,
    )


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
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=False,
    )

    cuckoo_manager = CuckooManager(
        server_address, web_interface_address, ca_certificate, verify_ssl, api_token
    )

    task_ids = json.loads(siemplify.parameters["additional_data"])

    siemplify.LOGGER.info(f"Connected to Cuckoo {server_address}")

    if all(
        [cuckoo_manager.is_task_reported(task_id) for file_path, task_id in task_ids]
    ):
        siemplify.LOGGER.info("All tasks completed.")
        max_score = 0
        results_json = {}

        for file_path, task_id in task_ids:
            try:
                siemplify.LOGGER.info(f"Fetching report for task {task_id}")
                report = cuckoo_manager.get_report(task_id)
                max_score = max(max_score, report.get("info", {}).get("score", 0))

                if web_interface_address:
                    siemplify.result.add_entity_link(
                        f"Report Link For Task With ID: {task_id}",
                        cuckoo_manager.construct_report_url(task_id),
                    )

                siemplify.result.add_data_table(
                    f"Result For Task With ID: {task_id}, File Path: {file_path}",
                    flat_dict_to_csv(construct_flat_dict_from_report(report)),
                )

                results_json[file_path] = report

            except Exception as e:
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on file: {file_path}.\n{str(e)}."
                )
                siemplify.LOGGER.exception(e)

        siemplify.result.add_result_json(json.dumps(results_json))
        siemplify.end(
            "All tasks were completed.",
            json.dumps(max_score),
            EXECUTION_STATE_COMPLETED,
        )

    else:
        siemplify.LOGGER.info("NOT all tasks completed.")
        siemplify.end(
            "Tasks are in progress.", json.dumps(task_ids), EXECUTION_STATE_INPROGRESS
        )


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] == "True":
        main()
    else:
        async_analysis()
