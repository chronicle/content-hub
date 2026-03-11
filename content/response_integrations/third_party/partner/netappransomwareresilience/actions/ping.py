from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import ApiManager
from ..core.rrs_exceptions import RrsException


@output_handler
def main() -> None:
    """Test connectivity to the Ransomware Resilience Service.

    Validates the authentication token against the RRS API to verify that the
    integration is properly configured and the server is reachable.
    """
    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("----------------- RRS - Test connection: Init -----------------")

    try:
        rrsManager = ApiManager(siemplify)
        siemplify.LOGGER.info("----------------- RRS - Test connection: Started -----------------")

        is_token_valid = rrsManager.is_token_valid()
        siemplify.LOGGER.info(f"Ping: {is_token_valid=}")

        # used to flag back to siemplify system, the action final status
        status = EXECUTION_STATE_COMPLETED
        # human readable message, showed in UI as the action result
        output_message = "Successfully connected to Ransomware Resilience server!"
        # Set a simple result value, used for playbook if\else and placeholders.
        result_value = True

    except RrsException as e:
        output_message = str(e)
        siemplify.LOGGER.error(f"Ping: RRS error - {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    except Exception as e:
        output_message = f"Failed to connect to the Ransomware Resilience server! {e}"
        siemplify.LOGGER.error(f"Connection to API failed, performing action {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- RRS - Test connection: End -----------------")

    siemplify.LOGGER.info(
        f"Ping: \n  status: {status}\n  result_value: {result_value}"
        f"\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
