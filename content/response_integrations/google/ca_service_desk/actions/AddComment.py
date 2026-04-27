from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CaSoapManager import CaSoapManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("CaServiceDesk")
    api_root = conf["Api Root"]
    username = conf["Username"]
    password = conf["Password"]

    ca_manager = CaSoapManager(api_root, username, password)

    ticket_id = siemplify.parameters["Ticket ID"]
    comment = siemplify.parameters["Comment"]

    add_comment_status = ca_manager.add_comment_to_incident(ticket_id, comment)

    if add_comment_status:
        output_message = f"Added comment to Incident {ticket_id}."
        result_value = "true"

    else:
        output_message = (
            f"There was a problem adding comment to ticket number {ticket_id}."
        )
        result_value = "false"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
