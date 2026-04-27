from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.AttivoManager import AttivoManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    UPDATE_EVENT_SCRIPT_NAME,
    SELECT_ONE,
)
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_EVENT_SCRIPT_NAME
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

    event_id = extract_action_param(
        siemplify, param_name="Event ID", is_mandatory=True, print_value=True
    )
    event_status = extract_action_param(
        siemplify, param_name="Status", print_value=True
    )
    comment = extract_action_param(siemplify, param_name="Comment", print_value=True)

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""

    try:
        siemplify.LOGGER.info("----------------- Main - Started -----------------")
        if event_status == SELECT_ONE and not comment:
            raise Exception(
                'at least one of the parameters "Status" or "Comment" should have a value.'
            )

        manager = AttivoManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        if comment:
            manager.update_comment(event_id=event_id, comment=comment)

        if event_status != SELECT_ONE:
            manager.update_status(event_id=event_id, status=event_status)

        output_message = f"Successfully updated the event with ID {event_id} in {INTEGRATION_DISPLAY_NAME}."

    except Exception as e:
        output_message += (
            f"Error executing action {UPDATE_EVENT_SCRIPT_NAME}. Reason: {e}"
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
