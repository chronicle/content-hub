from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.CybereasonManager import CybereasonManager
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import INTEGRATION_NAME, GET_MALOP_SCRIPT_NAME, MALOP_CASE_WALL_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_MALOP_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    output_message = (
        f"Successfully retrieved details for the malop with ID {malop_guid}"
    )
    status = EXECUTION_STATE_COMPLETED

    try:
        manager = CybereasonManager(
            api_root,
            username,
            password,
            verify_ssl,
            ca_certificate,
            siemplify.LOGGER,
            force_check_connectivity=True,
        )
        malop = manager.get_malop_or_raise(malop_guid)

        siemplify.result.add_data_table(
            MALOP_CASE_WALL_NAME.format(malop_guid), malop.to_csv()
        )
        siemplify.result.add_result_json(malop.as_json())
    except Exception as e:
        output_message = f"Error executing action {GET_MALOP_SCRIPT_NAME}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
