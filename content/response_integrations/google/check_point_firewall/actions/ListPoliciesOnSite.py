from __future__ import annotations
from ..core.CheckpointManager import CheckpointManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import INTEGRATION_NAME, LIST_POLICIES_ON_SITE_SCRIPT_NAME
from soar_sdk.SiemplifyUtils import dict_to_flat, flat_dict_to_csv


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_POLICIES_ON_SITE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Server Address",
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
    domain_name = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Domain",
        is_mandatory=False,
        default_value="",
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Layers To Return",
        input_type=int,
        default_value=50,
        print_value=True,
    )

    output_message = ""
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = CheckpointManager(
            server_address=server_address,
            username=username,
            password=password,
            domain=domain_name,
            verify_ssl=verify_ssl,
        )
        # Get policies
        policies = manager.get_policies(limit=limit)
        policies_parsed = manager.get_policies_parsed(policies=policies)

        # Add data table
        flat_report = dict_to_flat(policies)
        csv_output = flat_dict_to_csv(flat_report)
        siemplify.result.add_data_table("CheckPoint Policies Data Table", csv_output)
        # Add json result
        siemplify.result.add_result_json(
            [policy.to_json() for policy in policies_parsed]
        )
        # Set output success message
        output_message = "Successfully listed available policies."
        manager.log_out()
    except Exception as err:
        output_message = f"No policies were found. Reason: {err}"
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
