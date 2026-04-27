from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param

from ..core.FreshworksFreshserviceManager import FreshworksFreshserviceManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import (
    INTEGRATION_IDENTIFIER,
    INTEGRATION_DISPLAY_NAME,
    ADD_TICKET_TIME_ENTRY_SCRIPT_NAME,
    TIME_SPENT_FIELD,
)
from ..core.exceptions import (
    FreshworksFreshserviceNotFoundError,
    FreshworksFreshserviceValidationError,
    FreshworksFreshserviceMissingAgentError,
    FreshworksFreshserviceNegativeValueException,
)
from ..core.utils import load_json_string_to_dict


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = (
        f"{INTEGRATION_IDENTIFIER} - {ADD_TICKET_TIME_ENTRY_SCRIPT_NAME}"
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
    note = extract_action_param(
        siemplify, param_name="Note", print_value=True, is_mandatory=False
    )
    time_spent = extract_action_param(
        siemplify, param_name="Time Spent", print_value=True, is_mandatory=True
    )
    billable = extract_action_param(
        siemplify,
        param_name="Billable",
        print_value=True,
        default_value=False,
        input_type=bool,
        is_mandatory=False,
    )
    custom_fields = extract_action_param(
        siemplify, param_name="Custom Fields", print_value=True, is_mandatory=False
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
        custom_fields = (
            load_json_string_to_dict(custom_fields, "Custom Fields")
            if custom_fields
            else None
        )

        manager = FreshworksFreshserviceManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        agents = {agent.email: agent.agent_id for agent in manager.get_agents()}
        if agent_email not in agents:
            raise FreshworksFreshserviceMissingAgentError(
                f"Agent with email {agent_email} was not found"
                f" in {INTEGRATION_DISPLAY_NAME}."
            )
        agent_id = agents[agent_email]

        try:
            time_entry = manager.add_ticket_time_entry(
                ticket_id=ticket_id,
                agent_id=agent_id,
                time_spent=time_spent,
                billable=billable,
                note=note,
                custom_fields=custom_fields,
            )
            siemplify.result.add_result_json({"time_entry": time_entry.to_json()})
            output_message = f"New time entry is added to ticket {ticket_id}."
            result_value = True
        except FreshworksFreshserviceValidationError as error:
            if TIME_SPENT_FIELD in f"{error}":
                output_message = (
                    f"Specified time spent value {time_spent} is in incorrect format, "
                    "it should be in the 'hh:mm' format."
                )
            else:
                output_message = f"{error}"
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.exception(error)

        except FreshworksFreshserviceNotFoundError:
            output_message = (
                f"Ticket {ticket_id} was not found in {INTEGRATION_DISPLAY_NAME}."
            )

    except FreshworksFreshserviceMissingAgentError as error:
        output_message = f"{error}"

    except FreshworksFreshserviceValidationError as error:
        output_message = (
            "Failed to add ticket time entry with the provided parameters!"
            f"Error is: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    except Exception as error:
        output_message = (
            f"Error executing action '{ADD_TICKET_TIME_ENTRY_SCRIPT_NAME}'."
            f"Reason: {error}"
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
