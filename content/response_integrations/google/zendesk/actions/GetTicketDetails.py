from __future__ import annotations
import base64
import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyUtils import construct_csv

from TIPCommon import extract_configuration_param, extract_action_param
from ..core.ZendeskManager import ZendeskManager
from ..core.ZendeskManager import ZendeskManagerError

INTEGRATION_NAME = "Zendesk"
GET_TICKET_DETAILS = "Get Ticket Details"

@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_TICKET_DETAILS
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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED

    try:
        zendesk = ZendeskManager(user_email, api_token, server_address)
        json_result = {}

        ticket_details = zendesk.get_ticket_details(ticket_id)
        ticket_comments = zendesk.get_ticket_comments(ticket_id)
        ticket_attachments = zendesk.get_attachments_from_ticket(ticket_id)

        json_result["Comments"] = {}
        if ticket_comments is not None:
            ticket_comments_csv = construct_csv(ticket_comments["comments"])
            siemplify.result.add_data_table("Ticket Comments", ticket_comments_csv)
            json_result["Comments"] = ticket_comments["comments"]

        json_result["Attachments"] = {}
        if ticket_attachments is not None:
            attachments_names = []
            for attachment in ticket_attachments:
                for file_name, file_content in list(attachment.items()):
                    siemplify.result.add_attachment(
                        file_name, file_name, base64.b64encode(file_content)
                    )
                    attachments_names.append(file_name)
            json_result["Attachments"] = ticket_attachments

        output_message = f"Can not retrieve ticket with id {ticket_id}."
        result_value = False
        json_result["Details"] = {}
        if ticket_details is not None:
            ticket_json = json.dumps(ticket_details["ticket"], indent=4, sort_keys=True)
            siemplify.result.add_json("Ticket Data", ticket_json)
            output_message = f"Ticket with id {ticket_id} received."
            result_value = ticket_json
            json_result["Details"] = ticket_details

    except ZendeskManagerError as e:
        output_message = f"Error executing action {GET_TICKET_DETAILS}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("---------------- Main - Finished ----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
