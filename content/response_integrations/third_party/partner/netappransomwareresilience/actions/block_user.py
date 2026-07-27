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
    """Block a user via the Ransomware Resilience Service.

    Calls the RRS API to block the target user and reports the result
    back to the SOAR platform.
    """
    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("----------------- RRS - Block User: Init -----------------")

    block_user_result = None
    try:
        rrsManager = ApiManager(siemplify)
        # Extract parameters from action
        user_id = siemplify.extract_action_param("User ID", is_mandatory=True, print_value=False)
        user_ips = siemplify.extract_action_param("User IPs", print_value=False)
        duration = siemplify.extract_action_param("Duration", print_value=True)
        siemplify.LOGGER.info("----------------- RRS - Block User: Started -----------------")

        # call block user api
        block_user_result = rrsManager.block_user(user_id, user_ips, duration)
        # used to flag back to siemplify system, the action final status
        status = EXECUTION_STATE_COMPLETED
        # human readable message, showed in UI as the action result
        output_message = (
            f"Successfully blocked user on the following entities using NetApp Ransomware Resilience: {user_id}"
        )
        # Set a simple result value, used for playbook if\else and placeholders.
        result_value = True

    except RrsException as e:
        output_message = f'Error executing action "Block User". Reason: {e}'
        siemplify.LOGGER.error(f"Block User: RRS error - {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        block_user_result = {}

    except Exception as e:
        output_message = f'Error executing action "Block User". Reason: {e}'
        siemplify.LOGGER.error(f"Block User: Failed to block user. Error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        block_user_result = {}

    siemplify.LOGGER.info("----------------- RRS - Block User: End -----------------")
    siemplify.LOGGER.info(
        f"Block User: \n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )

    # Add result to action output.
    siemplify.result.add_result_json(block_user_result)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
