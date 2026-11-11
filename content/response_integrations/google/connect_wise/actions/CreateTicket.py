from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# Imports
from soar_sdk.SiemplifyAction import SiemplifyAction
from connect_wise.core.ConnectWiseManager import ConnectWiseManager, SUMMARY_CHAR_COUNT


@output_handler
def main():

    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    # Configuration.
    configuration_settings = siemplify.get_configuration("ConnectWise")
    company_url = configuration_settings["Api Root"]
    company_name = configuration_settings["Company Name"]
    public_key = configuration_settings["Public Key"]
    private_key = configuration_settings["Private Key"]
    client_id = configuration_settings["Client Id"]
    connectwise_manager = ConnectWiseManager(
        company_url, company_name, public_key, private_key, client_id
    )
    result_value = False

    # Parameters.
    company = siemplify.parameters["Company"]
    owner_name = siemplify.parameters.get("Owner Name")
    board = siemplify.parameters["Board"]
    summary = siemplify.parameters["Summary"]
    status = siemplify.parameters["Status"]
    priority_id = siemplify.parameters["Priority"]
    email_cc = siemplify.parameters.get("Email Note CC", "")
    email_cc = [
        single_value.strip()
        for single_value in email_cc.split(",")
        if single_value.strip()
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    output_message = ""

    # Truncate summary input parameter if the character length exceeds 100 character limit
    if len(summary) > SUMMARY_CHAR_COUNT:
        summary = f"{summary[:SUMMARY_CHAR_COUNT - 2]}.."
        output_message = (
            'Value for "Summary" action input parameter '
            "is larger than 100 characters supported by the API, "
            "exceeding characters will be truncated.\n"
        )

    # Execute Create Ticket.
    ticket_id = connectwise_manager.create_ticket(
        summary, company, board, status, priority_id, owner_name, email_cc
    )

    if ticket_id:
        output_message += f"Created ticket with id: {ticket_id}"
        result_value = ticket_id
    else:
        output_message += "There was a problem creating ticket."

    siemplify.LOGGER.info(output_message)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\nresult_value: {result_value}"
        f"\noutput_message: {output_message}"
    )
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
