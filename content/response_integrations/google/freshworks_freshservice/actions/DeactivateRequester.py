from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param

from ..core.FreshworksFreshserviceManager import FreshworksFreshserviceManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import (
    INTEGRATION_IDENTIFIER,
    INTEGRATION_DISPLAY_NAME,
    DEACTIVATE_REQUESTER_SCRIPT_NAME,
)
from ..core.exceptions import (
    FreshworksFreshserviceNotFoundError,
    FreshworksFreshserviceMethodNotAllowedError,
    FreshworksFreshserviceNegativeValueException,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = (
        f"{INTEGRATION_IDENTIFIER} - {DEACTIVATE_REQUESTER_SCRIPT_NAME}"
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
        requester_id = extract_action_param(
            siemplify,
            param_name="Requester ID",
            print_value=True,
            input_type=int,
            is_mandatory=True,
        )
        if requester_id < 0:
            raise FreshworksFreshserviceNegativeValueException(
                '"Requester ID" should be a positive number.'
            )

        manager = FreshworksFreshserviceManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
            force_test_connectivity=True,
        )

        try:
            manager.deactivate_requester(requester_id=requester_id)
            output_message = (
                f"{INTEGRATION_DISPLAY_NAME} requester {requester_id} is deactivated."
            )
            result_value = True

        except FreshworksFreshserviceNotFoundError as error:
            output_message = (
                f"Failed to find freshservice requester {requester_id} to deactivate."
            )
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.exception(error)

        except FreshworksFreshserviceMethodNotAllowedError as error:
            output_message = (
                f"Failed to deactivate freshservice requester {requester_id},"
                f"may be it was already deactivated? API response: {error}"
            )
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.exception(error)

    except Exception as error:
        output_message = (
            f"Error executing action '{DEACTIVATE_REQUESTER_SCRIPT_NAME}'."
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
