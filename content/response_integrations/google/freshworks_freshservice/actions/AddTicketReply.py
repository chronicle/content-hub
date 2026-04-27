from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param

from ..core.FreshworksFreshserviceManager import FreshworksFreshserviceManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import (
    INTEGRATION_IDENTIFIER,
    INTEGRATION_DISPLAY_NAME,
    ADD_TICKET_REPLY_SCRIPT_NAME,
)
from ..core.exceptions import (
    FreshworksFreshserviceNotFoundError,
    FreshworksFreshserviceNegativeValueException,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_IDENTIFIER} - {ADD_TICKET_REPLY_SCRIPT_NAME}"
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
    reply_text = extract_action_param(
        siemplify, param_name="Reply Text", print_value=True, is_mandatory=True
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

        manager = FreshworksFreshserviceManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
            force_test_connectivity=True,
        )

        try:
            conversation = manager.add_ticket_reply(
                ticket_id=ticket_id, reply_text=reply_text
            )
            siemplify.result.add_result_json({"conversation": conversation.to_json()})
            output_message = f"New reply is added to ticket {ticket_id}."
            result_value = True
        except FreshworksFreshserviceNotFoundError:
            output_message = (
                f"Ticket {ticket_id} was not found in {INTEGRATION_DISPLAY_NAME}."
            )

    except Exception as error:
        output_message = (
            f'Error executing action "{ADD_TICKET_REPLY_SCRIPT_NAME}". Reason: {error}'
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
