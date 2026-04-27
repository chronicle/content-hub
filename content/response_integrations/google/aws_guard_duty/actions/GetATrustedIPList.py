from __future__ import annotations
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import construct_csv
from ..core.AWSGuardDutyManager import AWSGuardDutyManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from ..core.consts import INTEGRATION_NAME
from ..core import utils

SCRIPT_NAME = "Get a Trusted IP List"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    aws_access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Access Key ID",
        is_mandatory=True,
    )

    aws_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Secret Key",
        is_mandatory=True,
    )

    aws_default_region = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Default Region",
        is_mandatory=True,
    )

    detector_id = extract_action_param(
        siemplify, param_name="Detector ID", is_mandatory=True, print_value=True
    )
    ip_lists_ids = extract_action_param(
        siemplify, param_name="Trusted IP List IDs", is_mandatory=True, print_value=True
    )

    # Split the ip lists IDs
    ip_lists_ids = utils.load_csv_to_list(ip_lists_ids, "Trusted IP List IDs")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = "true"
    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    successful_ids = []
    failed_ids = []

    json_results = {}

    try:
        siemplify.LOGGER.info("Connecting to AWS GuardDuty Service")
        manager = AWSGuardDutyManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_default_region,
        )
        manager.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to AWS GuardDuty service")

        manager.get_detector(
            detector_id=detector_id
        )  # Validate that the detector exists

        found_ip_sets = []

        for ip_list_id in ip_lists_ids:
            try:
                siemplify.LOGGER.info(
                    f"Fetching IP list {ip_list_id} details (detector {detector_id})"
                )
                ip_set = manager.get_ip_set_by_id(
                    detector_id=detector_id, ip_set_id=ip_list_id
                )
                found_ip_sets.append(ip_set)
                successful_ids.append(ip_list_id)
                json_results[ip_list_id] = ip_set.as_json()

            except Exception as e:
                failed_ids.append(ip_list_id)
                siemplify.LOGGER.error(f"An error occurred on IP list {ip_list_id}")
                siemplify.LOGGER.exception(e)

        if found_ip_sets:
            siemplify.LOGGER.info(f"Found {len(found_ip_sets)} IP lists details.")
            siemplify.result.add_data_table(
                "Trusted IP Lists Details",
                construct_csv([ip_set.as_csv() for ip_set in found_ip_sets]),
            )

            if successful_ids:
                output_message += "Successfully retrieved details about the following Trusted IP Lists from AWS GuardDuty:\n{}\n\n".format(
                    "\n".join(successful_ids)
                )

            if failed_ids:
                output_message += "Action wasn’t able to  retrieve details about the following Trusted IP Lists from AWS GuardDuty:\n{}".format(
                    "\n".join(failed_ids)
                )

        else:
            siemplify.LOGGER.info(
                f"No details were retrieved about the provided Trusted IP Lists."
            )
            output_message += (
                "No details were retrieved about the provided Trusted IP Lists."
            )
            result_value = "false"

    except Exception as error:  # action failed
        siemplify.LOGGER.error(
            f"Error executing action '{SCRIPT_NAME}'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Error executing action '{SCRIPT_NAME}'. Reason: {error}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
