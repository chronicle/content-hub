from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.ZendeskManager import ZendeskManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param
import re

INTEGRATION_NAME = "Zendesk"
CREATE_TICKET = "Create Ticket"
VALID_EMAIL_REGEXP = "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_TICKET
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

    subject = extract_action_param(
        siemplify,
        param_name="Subject",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )
    description = extract_action_param(
        siemplify,
        param_name="Description",
        is_mandatory=True,
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
    internal_note = extract_action_param(
        siemplify,
        param_name="Internal Note",
        is_mandatory=False,
        print_value=True,
        input_type=bool,
    )
    email_ccs = extract_action_param(
        siemplify,
        param_name="Email CCs",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )
    validate_email_ccs = extract_action_param(
        siemplify,
        param_name="Validate Email CCs",
        is_mandatory=False,
        print_value=True,
        input_type=bool,
    )
    tag = [ticket_tag]
    internal_note = not internal_note
    email_ccs = (
        [item.strip() for item in email_ccs.rstrip(",").split(",")] if email_ccs else []
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        zendesk = ZendeskManager(user_email, api_token, server_address)
        invalid_emails = []
        for email in email_ccs:
            if not bool(re.search(VALID_EMAIL_REGEXP, email)):
                invalid_emails.append(email)

        if invalid_emails:
            raise Exception(
                f"the following emails are not valid: {', '.join(str(v) for v in invalid_emails)}. Please check the spelling."
            )

        if validate_email_ccs:
            existing_emails = zendesk.get_users_email_addresses()
            for email in email_ccs:
                if email not in existing_emails:
                    raise Exception(
                        "users with the following emails were not found: {}. Please check the spelling "
                        'or disable "Validate Email CCs" parameter.'.format(email)
                    )

        new_ticket = zendesk.create_ticket(
            subject=subject,
            description=description,
            assigned_to=assigned_user,
            assignment_group=assignment_group,
            priority=priority,
            ticket_type=ticket_type,
            tags=tag,
            internal_note=internal_note,
            email_ccs=email_ccs,
        )

        if new_ticket:
            ticket_id = new_ticket["ticket"]["id"]
            output_message = f"Successfully created ticket with id: {str(ticket_id)}"
            result_value = ticket_id
        else:
            output_message = "There was a problem creating ticket."
            result_value = False

    except Exception as e:
        output_message = f"Error executing action {CREATE_TICKET}. Reason: {e}"
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
