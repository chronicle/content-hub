from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import unix_now, convert_unixtime_to_datetime, output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED,EXECUTION_STATE_TIMEDOUT
from ..core.ApiManager import ApiManager

@output_handler
def main():
    siemplify = SiemplifyAction()

    siemplify.LOGGER.info("----------------- RRS - Test connection: Init -----------------")
    rrsManager = ApiManager(siemplify)
    siemplify.LOGGER.info("----------------- RRS - Test connection: Started -----------------")

    try:
        is_token_valid = rrsManager.is_token_valid()
        siemplify.LOGGER.info(f"Ping: {is_token_valid=}")

        status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
        output_message = "Successfully connected to Ransomware Resilience server!"  # human readable message, showed in UI as the action result
        result_value = True  # Set a simple result value, used for playbook if\else and placeholders.

    except Exception as e:
        output_message = f"Failed to connect to the Ransomware Resilience server! {e}"
        connectivity_result = False
        siemplify.LOGGER.error(f"Connection to API failed, performing action {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED    
        result_value = False

    siemplify.LOGGER.info("----------------- RRS - Test connection: End -----------------")

    siemplify.LOGGER.info("Ping: \n  status: {}\n  result_value: {}\n  output_message: {}".format(status,result_value, output_message))
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
