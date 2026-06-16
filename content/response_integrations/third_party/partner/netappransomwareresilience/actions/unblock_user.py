from __future__ import annotations

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import ApiManager
from ..core.rrs_exceptions import RrsException


@output_handler
def main() -> None:
    """Unblock a user via the Ransomware Resilience Service.

    Calls the RRS API to unblock the target user (remediation for the
    Block User action) and reports the result back to the SOAR platform.
    """
    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("----------------- RRS - Unblock User: Init -----------------")

    unblock_user_result = None
    try:
        rrsManager = ApiManager(siemplify)
        # Extract parameters from action
        user_id = siemplify.extract_action_param("User ID", is_mandatory=True, print_value=False)
        user_ips = siemplify.extract_action_param("User IPs", print_value=False)
        siemplify.LOGGER.info("----------------- RRS - Unblock User: Started -----------------")

        # call unblock user api
        unblock_user_result = rrsManager.unblock_user(user_id, user_ips)
        # used to flag back to siemplify system, the action final status
        status = EXECUTION_STATE_COMPLETED
        # human readable message, showed in UI as the action result
        output_message = (
            f"Successfully unblocked user on the following entities using NetApp Ransomware Resilience: {user_id}"
        )
        # Set a simple result value, used for playbook if\else and placeholders.
        result_value = True

    except RrsException as e:
        output_message = f'Error executing action "Unblock User". Reason: {e}'
        siemplify.LOGGER.error(f"Unblock User: RRS error - {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        unblock_user_result = {}

    except Exception as e:
        output_message = f'Error executing action "Unblock User". Reason: {e}'
        siemplify.LOGGER.error(f"Unblock User: Failed to unblock user. Error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        unblock_user_result = {}

    siemplify.LOGGER.info("----------------- RRS - Unblock User: End -----------------")
    siemplify.LOGGER.info(
        f"Unblock User: \n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )

    # Add result to action output.
    siemplify.result.add_result_json(unblock_user_result)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
