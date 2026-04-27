from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from ..core.FreshworksFreshserviceManager import FreshworksFreshserviceManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import (
    INTEGRATION_IDENTIFIER,
    INTEGRATION_DISPLAY_NAME,
    LIST_TICKET_TIME_ENTRIES_SCRIPT_NAME,
    ROWS_PER_PAGE_PARAM_NAME,
    START_AT_PAGE_PARAM_NAME,
    MAX_ROWS_TO_RETURN_PARAM_NAME,
)
from ..core.exceptions import (
    FreshworksFreshserviceValidationError,
    FreshworksFreshserviceNotFoundError,
    FreshworksFreshserviceMissingAgentError,
    FreshworksFreshserviceNegativeValueException,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = (
        f"{INTEGRATION_IDENTIFIER} - {LIST_TICKET_TIME_ENTRIES_SCRIPT_NAME}"
    )
    siemplify.LOGGER.info("=================== Main - Param Init ===================")

    # Integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Key",
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        default_value=True,
        print_value=True,
    )

    # Action configuration
    agent_email = extract_action_param(
        siemplify, param_name="Agent Email", print_value=True, is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    # Action results
    status = EXECUTION_STATE_COMPLETED
    result_value = False

    try:
        ticket_id = extract_action_param(
            siemplify,
            param_name="Ticket ID",
            print_value=True,
            input_type=int,
            is_mandatory=True,
        )
        if ticket_id < 0:
            raise FreshworksFreshserviceNegativeValueException(
                '"Ticket ID" should be a positive number.'
            )
        rows_per_page = extract_action_param(
            siemplify,
            param_name=ROWS_PER_PAGE_PARAM_NAME,
            input_type=int,
            print_value=True,
            default_value=30,
            is_mandatory=False,
        )
        start_at_page = extract_action_param(
            siemplify,
            param_name=START_AT_PAGE_PARAM_NAME,
            input_type=int,
            print_value=True,
            default_value=1,
            is_mandatory=False,
        )
        max_rows_to_return = extract_action_param(
            siemplify,
            param_name=MAX_ROWS_TO_RETURN_PARAM_NAME,
            input_type=int,
            print_value=True,
            default_value=30,
            is_mandatory=False,
        )

        if rows_per_page <= 0:
            raise FreshworksFreshserviceValidationError(
                f'"{ROWS_PER_PAGE_PARAM_NAME}" parameter provided must be positive.'
            )
        if start_at_page <= 0:
            raise FreshworksFreshserviceValidationError(
                f'"{START_AT_PAGE_PARAM_NAME}" parameter provided must be positive.'
            )
        if max_rows_to_return <= 0:
            raise FreshworksFreshserviceValidationError(
                f"'{MAX_ROWS_TO_RETURN_PARAM_NAME}'"
                " parameter provided must be positive."
            )

        manager = FreshworksFreshserviceManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        ticket_time_entries = manager.get_ticket_time_entries(
            rows_per_page=rows_per_page,
            start_at_page=start_at_page,
            limit=max_rows_to_return,
            ticket_id=ticket_id,
        )

        agents = {agent.agent_id: agent.email for agent in manager.get_agents()}
        if agent_email not in agents.values():
            raise FreshworksFreshserviceMissingAgentError(
                f"Agent with email {agent_email} was not found"
                f" in {INTEGRATION_DISPLAY_NAME}."
            )

        ticket_time_entries = [
            time_entry
            for time_entry in ticket_time_entries
            if agents.get(time_entry.agent_id) == agent_email
        ]
        for time_entry in ticket_time_entries:
            time_entry.set_agent_email(agents.get(time_entry.agent_id))

        if ticket_time_entries:
            siemplify.result.add_result_json(
                {
                    "time_entries": [
                        time_entry.to_json() for time_entry in ticket_time_entries
                    ]
                }
            )
            siemplify.result.add_data_table(
                title=f"{INTEGRATION_DISPLAY_NAME} Ticket {ticket_id} Time Entries",
                data_table=construct_csv(
                    [time_entry.as_csv() for time_entry in ticket_time_entries]
                ),
            )
            output_message = f"Successfully fetched {INTEGRATION_DISPLAY_NAME} ticket {ticket_id} time entries."
            result_value = True
        else:
            output_message = (
                f"No ticket time entries were found for the ticket {ticket_id}."
            )

    except FreshworksFreshserviceMissingAgentError as error:
        output_message = f"{error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    except FreshworksFreshserviceNotFoundError as error:
        output_message = (
            f"Ticket {ticket_id} was not found in {INTEGRATION_DISPLAY_NAME}."
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    except FreshworksFreshserviceValidationError as error:
        output_message = (
            "Failed to list ticket time entries with the provided parameters!"
            f" Error is: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    except Exception as error:
        output_message = (
            f"Error executing action '{LIST_TICKET_TIME_ENTRIES_SCRIPT_NAME}'."
            f" Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
