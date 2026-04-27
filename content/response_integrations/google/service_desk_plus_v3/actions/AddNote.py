from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_configuration_param, extract_action_param

from ..core.constants import INTEGRATION_NAME, ADD_NOTE_ACTION
from ..core.ServiceDeskPlusManagerV3 import ServiceDeskPlusManagerV3


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_NOTE_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Key"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        print_value=True,
    )

    # Action Parameters
    note = extract_action_param(
        siemplify, param_name="Note", is_mandatory=True, input_type=str
    )
    request_id = extract_action_param(
        siemplify, param_name="Request ID", is_mandatory=True, input_type=str
    )
    show_to_requester = extract_action_param(
        siemplify,
        param_name="Show To Requester",
        default_value=False,
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )
    notify_technician = extract_action_param(
        siemplify,
        param_name="Notify Technician",
        default_value=False,
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )
    mark_first_response = extract_action_param(
        siemplify,
        param_name="Mark First Response",
        default_value=False,
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )
    add_to_linked_requests = extract_action_param(
        siemplify,
        param_name="Add To Linked Requests",
        default_value=False,
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        servicedesk_manager = ServiceDeskPlusManagerV3(
            api_root=api_root, api_key=api_key, verify_ssl=verify_ssl
        )
        result = servicedesk_manager.add_note(
            mark_first_response=mark_first_response,
            add_to_linked_requests=add_to_linked_requests,
            request_id=request_id,
            show_to_requester=show_to_requester,
            notify_technician=notify_technician,
            note=note,
        )
        output_message = f"Successfully added note to request with ID {request_id}"

        siemplify.result.add_result_json(result.to_json())

    except Exception as e:
        output_message = f"Error executing action {ADD_NOTE_ACTION}. Reason: {e}"
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
