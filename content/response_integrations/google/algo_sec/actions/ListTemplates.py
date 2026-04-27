from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.AlgoSecManager import AlgoSecManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import (
    INTEGRATION_NAME,
    LIST_TEMPLATES_SCRIPT_NAME,
    EQUAL_FILTER,
    CONTAINS_FILTER,
    DEFAULT_TEMPLATES_LIMIT,
)

TABLE_NAME = "Available Templates"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_TEMPLATES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
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
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    filter_logic = extract_action_param(
        siemplify, param_name="Filter Logic", print_value=True
    )
    filter_value = extract_action_param(
        siemplify, param_name="Filter Value", print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Templates To Return",
        input_type=int,
        print_value=True,
        default_value=DEFAULT_TEMPLATES_LIMIT,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        if limit < 1:
            raise Exception('"Max Templates To Return" must be greater than 0.')

        manager = AlgoSecManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        siemplify.LOGGER.info("Retrieving information about available templates...")
        templates = manager.list_templates()
        if filter_value:
            if filter_logic == EQUAL_FILTER:
                templates = [
                    template for template in templates if template.name == filter_value
                ]
            elif filter_logic == CONTAINS_FILTER:
                templates = [
                    template for template in templates if filter_value in template.name
                ]

        templates = templates[:limit] if limit else templates

        if templates:
            siemplify.result.add_data_table(
                TABLE_NAME, construct_csv([template.to_csv() for template in templates])
            )
            siemplify.result.add_result_json(
                [template.to_json() for template in templates]
            )
            output_message = (
                f"Successfully found templates for the provided criteria in"
                f" {INTEGRATION_NAME}."
            )
        else:
            result_value = False
            output_message = f"No templates were found for the provided criteria in {INTEGRATION_NAME}."

    except Exception as e:
        output_message = (
            f"Error executing action {LIST_TEMPLATES_SCRIPT_NAME}. Reason: {e}"
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
