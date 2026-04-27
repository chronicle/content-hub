from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.MitreAttckManager import MitreAttckManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param

INTEGRATION_NAME = "MitreAttck"
SCRIPT_NAME = "Mitre Att&ck - Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    result_value = "true"
    status = EXECUTION_STATE_COMPLETED
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        print_value=True,
    )

    manager = MitreAttckManager(api_root, verify_ssl)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        if manager.test_connectivity():
            output_message = "Connection Established"
        else:
            output_message = "Unable to connect to MitreAttack"
            status = EXECUTION_STATE_FAILED
            result_value = "false"
    except Exception as e:
        siemplify.LOGGER.error("Unable to connect to MitreAttack")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        output_message = "Unable to connect to MitreAttack"
        result_value = "false"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
