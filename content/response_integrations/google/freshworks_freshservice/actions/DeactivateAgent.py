from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param

from ..core.FreshworksFreshserviceManager import FreshworksFreshserviceManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import (
    INTEGRATION_IDENTIFIER,
    CREATE_TICKET_SCRIPT_NAME,
    INTEGRATION_DISPLAY_NAME,
    DEACTIVATE_AGENT_SCRIPT_NAME,
)
from ..core.exceptions import (
    FreshworksFreshserviceNotFoundError,
    FreshworksFreshserviceAuthorizationError,
    FreshworksFreshserviceValidationError,
    FreshworksFreshserviceNegativeValueException,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_IDENTIFIER} - {CREATE_TICKET_SCRIPT_NAME}"
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
        agent_id = extract_action_param(
            siemplify,
            param_name="Agent ID",
            print_value=True,
            input_type=int,
            is_mandatory=True,
        )
        if agent_id < 0:
            raise FreshworksFreshserviceNegativeValueException(
                '"Agent ID" should be a positive number.'
            )

        manager = FreshworksFreshserviceManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
            force_test_connectivity=True,
        )

        try:
            siemplify.LOGGER.info(
                f"Deactivating Agent with ID {agent_id}"
                f"from {INTEGRATION_DISPLAY_NAME}"
            )
            agent_obj = manager.deactivate_agent(agent_id=agent_id)
            siemplify.LOGGER.info(
                f"Successfully deactivated agent with ID {agent_id}"
                f"from {INTEGRATION_DISPLAY_NAME}"
            )
            siemplify.result.add_result_json(agent_obj.to_json())
            output_message = f"Freshservice agent {agent_id} is deactivated."
            result_value = True

        except FreshworksFreshserviceAuthorizationError as error:
            output_message = (
                f"Failed to deactivate freshservice agent {agent_id},"
                f"maybe it was already deactivated? API response: {error}"
            )
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.exception(error)
        except FreshworksFreshserviceNotFoundError as error:
            output_message = (
                f"Failed to find {INTEGRATION_DISPLAY_NAME}"
                f"agent {agent_id} to deactivate."
            )
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.exception(error)

    except FreshworksFreshserviceValidationError as error:
        output_message = (
            f"Error executing action '{DEACTIVATE_AGENT_SCRIPT_NAME}'."
            f"Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    except Exception as error:
        output_message = (
            f"Error executing action '{DEACTIVATE_AGENT_SCRIPT_NAME}'."
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
