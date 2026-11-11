from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# Imports
from soar_sdk.SiemplifyAction import SiemplifyAction
from connect_wise.core.ConnectWiseManager import ConnectWiseManager
import base64
import json

# Consts
ATTACHED_FILE_TITLE = "Attached Result File."
RESULT_FILE_NAME_FORMAT = "ticket_{0}.json"  # {0} - Ticket Id.


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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    connectwise_manager = ConnectWiseManager(
        company_url, company_name, public_key, private_key, client_id
    )

    # Parameters.
    ticket_id = siemplify.parameters["Ticket Id"]

    # Execute Test Connectivity.
    result = connectwise_manager.get_ticket(ticket_id)

    json_results = {}

    if result:
        json_results[ticket_id] = result
        ticket_json = json.dumps(result, indent=4, sort_keys=True)
        siemplify.result.add_json("Ticket Data", ticket_json)
        # Add result file to action result.
        encoded_base64_result = base64.b64encode(ticket_json.encode("utf-8")).decode(
            "utf-8"
        )
        siemplify.result.add_entity_attachment(
            ATTACHED_FILE_TITLE,
            RESULT_FILE_NAME_FORMAT.format(ticket_id),
            encoded_base64_result,
        )
        # Form output message.
        output_message = f"Ticket with id {ticket_id} received."
        result_value = ticket_json
    else:
        # Form output message.
        output_message = "Ticket with id {0} was not received."
        result_value = "{}"

    # add json
    siemplify.result.add_result_json(json_results)
    siemplify.LOGGER.info(output_message)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\nresult_value: {result_value}"
        f"\noutput_message: {output_message}"
    )
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
