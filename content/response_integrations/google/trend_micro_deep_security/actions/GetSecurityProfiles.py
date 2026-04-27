from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, construct_csv

from ..core.constants import INTEGRATION_NAME
from ..core.TrendmicroDeepSecurityManager import TrendmicroManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Secret Key",
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    api_version = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Version",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    output_message = "No security profiles were found."
    try:
        trendmicro_manager = TrendmicroManager(
            api_root=api_root,
            api_secret_key=api_key,
            api_version=api_version,
            verify_ssl=verify_ssl,
        )

        result_value = False

        policies_list = trendmicro_manager.get_all_security_profiles()

        if policies_list:
            # Build csv table
            csv_results = trendmicro_manager.build_csv(policies_list)
            if csv_results:
                siemplify.result.add_data_table(
                    "Security Profiles", construct_csv(csv_results)
                )
                result_value = True
                output_message = (
                    f"Successfully retrieved "
                    f"{len(policies_list)} security profiles."
                )
    except Exception as e:
        output_message = f"Error executing action. Reason: {e}"
        result_value = False
        siemplify.LOGGER.error(f"Error executing action. Reason: {e}")
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
