from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param

from ..core.FreshworksFreshserviceManager import FreshworksFreshserviceManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import (
    INTEGRATION_IDENTIFIER,
    INTEGRATION_DISPLAY_NAME,
    DELETE_TICKET_TIME_ENTRY_SCRIPT_NAME,
)
from ..core.exceptions import (
    FreshworksFreshserviceNotFoundError,
    FreshworksFreshserviceNegativeValueException,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = (
        f"{INTEGRATION_IDENTIFIER} - {DELETE_TICKET_TIME_ENTRY_SCRIPT_NAME}"
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
        time_entry_id = extract_action_param(
            siemplify,
            param_name="Time Entry ID",
            print_value=True,
            input_type=int,
            is_mandatory=True,
        )
        if ticket_id < 0:
            raise FreshworksFreshserviceNegativeValueException(
                '"Ticket ID" should be a positive number.'
            )
        if time_entry_id < 0:
            raise FreshworksFreshserviceNegativeValueException(
                '"Time Entry ID" should be a positive number.'
            )

        manager = FreshworksFreshserviceManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
            force_test_connectivity=True,
        )

        try:
            manager.delete_ticket_time_entry(
                ticket_id=ticket_id, time_entry_id=time_entry_id
            )
            output_message = (
                f"Time entry {time_entry_id} is deleted for the ticket {ticket_id}."
            )
            result_value = True
        except FreshworksFreshserviceNotFoundError:
            output_message = (
                f"Provided ticket id {ticket_id} or time entry id {time_entry_id}"
                f" was not found in {INTEGRATION_DISPLAY_NAME}."
            )

    except Exception as error:
        output_message = (
            f"Error executing action '{DELETE_TICKET_TIME_ENTRY_SCRIPT_NAME}'."
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
