from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.CybereasonManager import CybereasonManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import INTEGRATION_NAME, LIST_MALOP_PROCESSES_SCRIPT_NAME
from ..core.utils import validate_positive_integer


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_MALOP_PROCESSES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate Base64",
    )

    malop_guid = extract_action_param(
        siemplify, param_name="Malop ID", is_mandatory=True, print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Results Limit",
        default_value=100,
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    csv_output, json_results = [], {}
    result_value = 0
    try:
        manager = CybereasonManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            ca_certificate_b64=ca_certificate,
            force_check_connectivity=True,
        )
        validate_positive_integer(limit)

        processes = manager.get_malop_processes_or_raise(
            malop_guid=malop_guid, limit=limit
        )
        if processes:
            csv_output = [process.to_csv() for process in processes]
            output_message = (
                f"Successfully retrieved related processes for the malop with ID {malop_guid} in "
                f"{INTEGRATION_NAME}."
            )
            json_results = [process.to_json() for process in processes]
        else:
            output_message = f"No processes were related to the malop with ID {malop_guid} in {INTEGRATION_NAME}."

        status = EXECUTION_STATE_COMPLETED
        result_value = len(processes)
        if csv_output:
            siemplify.result.add_data_table("Processes", construct_csv(csv_output))
        if json_results:
            siemplify.result.add_result_json(json_results)
    except Exception as e:
        output_message = (
            f"Error executing action {LIST_MALOP_PROCESSES_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  num_of_processes: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
