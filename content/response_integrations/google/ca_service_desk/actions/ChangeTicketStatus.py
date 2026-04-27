from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CaSoapManager import CaSoapManager

# Consts
ACTION_SCRIPT_NAME = "Change Ticket Status"


@output_handler
def main():

    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_SCRIPT_NAME

    conf = siemplify.get_configuration("CaServiceDesk")

    api_root = conf["Api Root"]
    username = conf["Username"]
    password = conf["Password"]

    ca_manager = CaSoapManager(api_root, username, password)

    # Parameters
    ticket_id = siemplify.parameters.get("Ticket ID")
    status = siemplify.parameters.get("Status").encode("utf-8")

    result_value = ca_manager.change_ticket_status(ticket_id, status)
    output_message = f'Ticket with id "{ticket_id}" status changed to "{status}"'

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
