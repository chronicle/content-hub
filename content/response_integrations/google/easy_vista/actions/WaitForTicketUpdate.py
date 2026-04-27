from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.EasyVistaManager import EasyVistaManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from ..core.constants import INTEGRATION_NAME, WAIT_FOR_TICKET_UPDATE
import json
import sys

STATUS = "Status"
COMMENT = "Comment"
ACTIONS = "Actions"


def start_operation(
    siemplify, easyvista_manager, account_id, ticket_identifier, field_to_monitor
):
    """
    Main part of the action that gets the initial information for a ticket
    :param siemplify: SiemplifyAction object.
    :param easyvista_manager: EasyVista manager object.
    :param account_id: EasyVista Account ID
    :param ticket_identifier: ID of the ticket that we want to watch
    :param field_to_monitor: Which field should be monitored
    :return: {output message, json result, execution_state}
    """

    status = EXECUTION_STATE_INPROGRESS
    output_message = f"Successfully fetched ticket {ticket_identifier} details."

    try:
        if field_to_monitor == STATUS:
            ticket_info = easyvista_manager.get_ticket_general_info(
                account_id, ticket_identifier
            )
            ticket_info = {"status": ticket_info.status_en}

        if field_to_monitor == COMMENT:
            ticket_info = easyvista_manager.get_ticket_comment(
                account_id, ticket_identifier
            )
            ticket_info = ticket_info.to_json()
        if field_to_monitor == ACTIONS:
            ticket_info = easyvista_manager.get_ticket_actions_raw(
                account_id, ticket_identifier
            )
            total_record_count = ticket_info.to_json().get("total_record_count")

            if total_record_count == "0":
                raise Exception("Ticket with this ID wasn't found in EasyVista")

            ticket_info = ticket_info.to_json()

        result_value = json.dumps(ticket_info)

    except Exception as e:
        output_message = f"Error executing action {WAIT_FOR_TICKET_UPDATE}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    return output_message, result_value, status


def query_operation_status(
    siemplify, easyvista_manager, account_id, ticket_identifier, field_to_monitor
):
    """
    Part of the action that periodically fetches the ticket details and compare them with the initial state
    :param siemplify: SiemplifyAction object.
    :param easyvista_manager: EasyVista manager object.
    :param account_id: EasyVista Account ID
    :param ticket_identifier: ID of the ticket that we want to watch
    :param field_to_monitor: Which field should be monitored
    :return: {output message, json result, execution_state} or True when the ticket was updated
    """

    initial_ticket_info = json.loads(siemplify.extract_action_param("additional_data"))

    try:
        if field_to_monitor == STATUS:
            ticket_info_raw = easyvista_manager.get_ticket_general_info(
                account_id, ticket_identifier
            )
            ticket_info = {"status": ticket_info_raw.status_en}

        if field_to_monitor == COMMENT:
            ticket_info_raw = easyvista_manager.get_ticket_comment(
                account_id, ticket_identifier
            )
            ticket_info = ticket_info_raw.to_json()
        if field_to_monitor == ACTIONS:
            ticket_info_raw = easyvista_manager.get_ticket_actions_raw(
                account_id, ticket_identifier
            )
            ticket_info = ticket_info_raw.to_json()

        # Comparison of ticket after and before
        if initial_ticket_info == ticket_info:
            status = EXECUTION_STATE_INPROGRESS
            result_value = json.dumps(initial_ticket_info)
            output_message = f"Ticket:{ticket_identifier} was not updated. Will check again later...."
        else:
            status = EXECUTION_STATE_COMPLETED
            result_value = True
            output_message = (
                f"Successfully got a an update for ticket {ticket_identifier}."
            )
            siemplify.result.add_result_json(ticket_info_raw.to_json())

    except Exception as e:
        output_message = f"Error executing action {WAIT_FOR_TICKET_UPDATE}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = WAIT_FOR_TICKET_UPDATE
    mode = "Main" if is_first_run else "Check changes"
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="API Root"
    )
    account_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Account ID"
    )
    username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Username"
    )
    password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Password"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    # Action Parameters
    ticket_identifier = extract_action_param(
        siemplify, param_name="Ticket Identifier", is_mandatory=True, input_type=str
    )
    field_to_monitor = extract_action_param(
        siemplify, param_name="Field To Monitor", is_mandatory=False, input_type=str
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    try:
        easyvista_manager = EasyVistaManager(
            api_root=api_root,
            account_id=account_id,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify,
                easyvista_manager,
                account_id,
                ticket_identifier,
                field_to_monitor,
            )
        else:
            output_message, result_value, status = query_operation_status(
                siemplify,
                easyvista_manager,
                account_id,
                ticket_identifier,
                field_to_monitor,
            )

    except Exception as e:
        output_message = f"Error executing action {WAIT_FOR_TICKET_UPDATE}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
