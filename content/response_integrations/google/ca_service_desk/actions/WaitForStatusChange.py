from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CaSoapManager import CaSoapManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_INPROGRESS
import sys


# Consts
ACTION_SCRIPT_NAME = "CA Service Desk_Wait_For_Status_Change"


@output_handler
def main():

    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_SCRIPT_NAME
    conf = siemplify.get_configuration("CaServiceDesk")

    api_root = conf["Api Root"]
    username = conf["Username"]
    password = conf["Password"]
    ticket_fields_str = conf.get("Ticket Fields", "")

    ticket_fields = ticket_fields_str.split(",")

    ca_manager = CaSoapManager(api_root, username, password)
    ticket_id = siemplify.parameters.get("Ticket ID")
    expected_ticket_status = siemplify.parameters.get("Expected Ticket Status Name")

    siemplify.LOGGER.info(f"Fetching current status of ticket {ticket_id}")

    try:
        current_ticket_status = ca_manager.get_ticket_status(ticket_id)

        if isinstance(current_ticket_status, str):
            current_ticket_status = current_ticket_status.decode("utf8")

    except Exception as e:
        siemplify.LOGGER.error(f"Unable to get ticket {ticket_id} status.")
        siemplify.LOGGER.exception(e)
        raise

    if current_ticket_status == expected_ticket_status:
        siemplify.LOGGER.info(
            f"Ticket {ticket_id} reached status: {expected_ticket_status}"
        )
        output_message = f"Ticket status is already: {current_ticket_status}."
        ticket_data = ca_manager.get_incident_by_id(ticket_id, ticket_fields)
        siemplify.result.add_result_json(ticket_data)
        siemplify.end(output_message, "true")

    else:
        siemplify.LOGGER.info(
            f"Ticket {ticket_id} current status: {current_ticket_status}. Waiting."
        )
        output_message = f"Current ticket status is: {current_ticket_status}, keeping tracking ticket."
        siemplify.end(output_message, "false", EXECUTION_STATE_INPROGRESS)


def query_job():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_SCRIPT_NAME

    siemplify.LOGGER.info("Starting async action.")

    conf = siemplify.get_configuration("CaServiceDesk")
    api_root = conf["Api Root"]
    username = conf["Username"]
    password = conf["Password"]
    ticket_fields_str = conf.get("Ticket Fields", "")

    ticket_fields = ticket_fields_str.split(",")

    siemplify.LOGGER.info("Connecting to CA")
    ca_manager = CaSoapManager(api_root, username, password)
    ticket_id = siemplify.parameters.get("Ticket ID")

    expected_ticket_status = siemplify.parameters.get("Expected Ticket Status Name")

    try:
        current_ticket_status = ca_manager.get_ticket_status(ticket_id)

        if isinstance(current_ticket_status, str):
            current_ticket_status = current_ticket_status.decode("utf8")

    except Exception as e:
        siemplify.LOGGER.error(f"Unable to get ticket {ticket_id} status.")
        siemplify.LOGGER.exception(e)
        raise

    if current_ticket_status == expected_ticket_status:
        siemplify.LOGGER.info(
            f"Ticket {ticket_id} reached status: {expected_ticket_status}"
        )
        output_massage = (
            f"Ticket status was changed to expected status: {expected_ticket_status}."
        )
        ticket_data = ca_manager.get_incident_by_id(ticket_id, ticket_fields)
        siemplify.result.add_result_json(ticket_data)
        siemplify.end(output_massage, "true", EXECUTION_STATE_COMPLETED)

    else:
        siemplify.LOGGER.info(
            "Current ticket status is: {0}, keeping"
            " tracking ticket with ID: {1}, waiting for status: {2}".format(
                current_ticket_status, ticket_id, expected_ticket_status
            )
        )

        output_massage = f"Current ticket status is: {current_ticket_status}, keeping tracking ticket."
        siemplify.end(output_massage, "false", EXECUTION_STATE_INPROGRESS)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] == "True":
        main()
    else:
        query_job()
