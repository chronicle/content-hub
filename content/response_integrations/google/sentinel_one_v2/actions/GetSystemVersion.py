from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon.extraction import extract_configuration_param
from sentinel_one_v2.core.constants import (
    INTEGRATION_NAME,
    GET_SYSTEM_VERSION_SCRIPT_NAME,
    SYSTEM_VERSION_TABLE_NAME,
)
from sentinel_one_v2.core.SentinelOneV2Factory import SentinelOneV2ManagerFactory


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_SYSTEM_VERSION_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        sentinel_one_manager = SentinelOneV2ManagerFactory().get_manager(
            api_root=api_root, api_token=api_token, verify_ssl=verify_ssl
        )

        siemplify.LOGGER.info("Fetching system version")
        system_version = sentinel_one_manager.get_system_info()

        if system_version:
            siemplify.result.add_data_table(
                SYSTEM_VERSION_TABLE_NAME, system_version.to_csv()
            )
            output_message = "System version Found"
        else:
            output_message = "System version was not found."

    except Exception as e:
        output_message = (
            f"Error executing action '{GET_SYSTEM_VERSION_SCRIPT_NAME}'. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
