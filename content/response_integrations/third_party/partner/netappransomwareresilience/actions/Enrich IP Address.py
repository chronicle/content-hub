from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import unix_now, convert_unixtime_to_datetime, output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED,EXECUTION_STATE_TIMEDOUT
from ..core.ApiManager import ApiManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("----------------- RRS - Enrich IP: Init -----------------")
    rrsManager = ApiManager(siemplify)
    ip_address = siemplify.extract_action_param("IP Address", print_value=True)
    siemplify.LOGGER.info("----------------- RRS - Enrich IP: Started -----------------")

    enrich_results = None
    try:
        
        # call enrich api
        enrich_results = rrsManager.enrich_ip(ip_address)

        status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
        output_message = f"Successfully enriched IP - {ip_address}"  # human readable message, showed in UI as the action result
        result_value = True  # Set a simple result value, used for playbook if\else and placeholders.

    except Exception as e:
        output_message = f"Failed to enrich IP - {ip_address}. Error: {e}"
        siemplify.LOGGER.error(f"Enrich IP: Failed to enrich IP - {ip_address}. Error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED    
        result_value = False

    siemplify.LOGGER.info("----------------- RRS - Enrich IP: End -----------------")
    siemplify.LOGGER.info(f"Enrich IP output: \n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}")
    
    # Add result to action output.
    siemplify.result.add_result_json(enrich_results)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
