from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.FireEyeHXManager import FireEyeHXManager, FireEyeHXNotFoundError
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    flat_dict_to_csv,
)


INTEGRATION_NAME = "FireEyeHX"
SCRIPT_NAME = "Get Indicator"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        input_type=str,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        input_type=str,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    category = extract_action_param(
        siemplify,
        param_name="Indicator Category",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )
    indicator_name = extract_action_param(
        siemplify,
        param_name="Indicator Name",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_results = {}
    status = EXECUTION_STATE_COMPLETED

    try:
        hx_manager = FireEyeHXManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )
        indicator = hx_manager.get_indicator(category, indicator_name)

        json_results = indicator.raw_data
        siemplify.result.add_data_table(
            f"Indicator {indicator_name}", flat_dict_to_csv(indicator.as_csv())
        )
        output_message = f"Found the following FireEye HX indicator: {indicator_name}"
        result_value = "true"

        hx_manager.logout()

    except FireEyeHXNotFoundError:
        siemplify.LOGGER.error("Indicator was not found for given parameters.")
        output_message = (
            f"The following indicator was not found in FireEye HX: {indicator_name}"
        )
        result_value = "false"

    except Exception as e:
        siemplify.LOGGER.error(f"Failed to execute action! Error is {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Failed to execute action! Error is {e}"

    siemplify.result.add_result_json(json_results)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
