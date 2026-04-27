from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.ZendeskManager import ZendeskManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param

INTEGRATION_NAME = "Zendesk"
UPDATE_TICKET = "Update Ticket"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_TICKET
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    user_email = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="User Email Address",
        is_mandatory=True,
        print_value=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Token",
        print_value=False,
        is_mandatory=True,
    )
    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Server Address",
        is_mandatory=True,
        print_value=True,
    )

    ticket_id = extract_action_param(
        siemplify,
        param_name="Ticket ID",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )
    subject = extract_action_param(
        siemplify,
        param_name="Subject",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )
    assigned_user = extract_action_param(
        siemplify,
        param_name="Assigned User",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )
    assignment_group = extract_action_param(
        siemplify,
        param_name="Assignment Group",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )
    priority = extract_action_param(
        siemplify,
        param_name="Priority",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )
    ticket_type = extract_action_param(
        siemplify,
        param_name="Ticket Type",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )
    ticket_tag = extract_action_param(
        siemplify,
        param_name="Tag",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )
    ticket_status = extract_action_param(
        siemplify,
        param_name="Status",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    additional_comment = extract_action_param(
        siemplify,
        param_name="Additional Comment",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )
    internal_note = extract_action_param(
        siemplify,
        param_name="Internal Note",
        is_mandatory=False,
        print_value=True,
        input_type=bool,
    )
    internal_note = not internal_note

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        zendesk = ZendeskManager(user_email, api_token, server_address)
        updated_ticket = zendesk.update_ticket(
            ticket_id=ticket_id,
            subject=subject,
            assigned_to=assigned_user,
            assignment_group=assignment_group,
            priority=priority,
            ticket_type=ticket_type,
            tag=ticket_tag,
            status=ticket_status,
        )
        if additional_comment:
            _response = zendesk.add_comment_to_ticket(
                ticket_id=ticket_id,
                comment_body=additional_comment,
                internal_note=internal_note,
            )

        if updated_ticket:
            output_message = f"Ticket with id {ticket_id} was updated successfully"

        else:
            output_message = (
                f"There was a problem updating ticket with id: {ticket_id}."
            )
            result_value = False

    except Exception as e:
        output_message = f"Error executing action {UPDATE_TICKET}. Reason: {e}"
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
