from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CaSoapManager import CaSoapManager

# Consts
ACTION_SCRIPT_NAME = "Assign Incident To User"


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
    username = siemplify.parameters.get("Username")

    result_value = ca_manager.assign_incident_to_user(ticket_id, username)

    if result_value:
        output_message = f'Ticket with id "{ticket_id}" assigned to "{str(username).encode("utf-8")}"'
    else:
        output_message = f'Ticket with id "{ticket_id}" was not assigned to "{str(username).encode("utf-8")}"'

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
