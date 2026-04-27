from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.FireEyeHXManager import FireEyeHXManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

INTEGRATION_NAME = "FireEyeHX"
SCRIPT_NAME = "Get Indicators"


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
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    search_term = extract_action_param(
        siemplify,
        param_name="Search Term",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    limit = extract_action_param(
        siemplify,
        param_name="Limit",
        is_mandatory=False,
        input_type=int,
        print_value=True,
        default_value=100,
    )
    share_mode = extract_action_param(
        siemplify,
        param_name="Share Mode",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    sort_by_field = extract_action_param(
        siemplify,
        param_name="Sort By Field",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    created_by = extract_action_param(
        siemplify,
        param_name="Created by",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    is_alerted = extract_action_param(
        siemplify,
        param_name="Has associated alerts",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    if share_mode == "any":
        share_mode = None

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_results = []
    status = EXECUTION_STATE_COMPLETED

    try:
        hx_manager = FireEyeHXManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )
        indicators = hx_manager.get_indicators(
            category=category,
            search=search_term,
            limit=limit,
            share_mode=share_mode,
            sort=sort_by_field,
            created_by=created_by,
            alerted=is_alerted,
        )

        json_results = [indicator.raw_data for indicator in indicators]

        siemplify.LOGGER.info(f"Found {len(indicators)} indicators.")

        if indicators:
            siemplify.result.add_data_table(
                "Indicators",
                construct_csv([indicator.as_csv() for indicator in indicators]),
            )
            output_message = "FireEye HX indicators found."
            result_value = "true"

        else:
            output_message = "No FireEye HX indicators found."
            result_value = "false"

        hx_manager.logout()

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
