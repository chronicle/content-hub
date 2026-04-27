from __future__ import annotations
from ..core.MandiantASMManager import MandiantASMManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import (
    INTEGRATION_NAME,
    UPDATE_ISSUE_SCRIPT_NAME,
    INTEGRATION_DISPLAY_NAME,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_ISSUE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Integration parameters
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Access Key",
        remove_whitespaces=False,
    )
    secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret Key",
        remove_whitespaces=False,
    )
    gti_api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="GTI API Key",
        remove_whitespaces=False,
    )
    project_name = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Project Name"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    issue_id = extract_action_param(
        siemplify, param_name="Issue ID", print_value=True, input_type=str
    )
    issue_status = extract_action_param(
        siemplify,
        param_name="Status",
        print_value=True,
        is_mandatory=True,
        input_type=str,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = f"Successfully updated issue  with ID “{issue_id}” in {INTEGRATION_DISPLAY_NAME}."

    try:
        if issue_status == "Select One":
            raise ValueError(f'you need to select a field from the "Status" parameter.')

        manager = MandiantASMManager(
            api_root=api_root,
            access_key=access_key,
            secret_key=secret_key,
            gti_api_key=gti_api_key,
            project_name=project_name,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        manager.update_issue(issue_id, issue_status)

        issue = manager.get_issue_by_id(issue_id)
        siemplify.result.add_result_json(issue.to_json())

    except Exception as e:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {UPDATE_ISSUE_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}"
        f"\n  is_success: {result_value}"
        f"\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
