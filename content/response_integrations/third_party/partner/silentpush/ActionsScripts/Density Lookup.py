from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import unix_now, convert_unixtime_to_datetime, output_handler
from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED,EXECUTION_STATE_TIMEDOUT

from constants import (INTEGRATION_NAME, DENSITY_LOOKUP_SCRIPT_NAME )
from SilentPushManager import SilentPushManager

@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DENSITY_LOOKUP_SCRIPT_NAME 

    # Extract Integration config
    server_url = siemplify.extract_configuration_param(INTEGRATION_NAME, "Silent Push Server")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")

    qtype = siemplify.extract_action_param("qtype", print_value=True)
    query = siemplify.extract_action_param("query", print_value=True)
    scope = siemplify.extract_action_param("scope", print_value=True)

    try:
        sp_manager = SilentPushManager(server_url, api_key, logger=siemplify.LOGGER)
        raw_response = sp_manager.density_lookup(qtype=qtype, query=query, scope=scope)
        
        records = raw_response.get("response", {}).get("records", [])
        
        if not records:
            error_message = f"No density records found for {qtype} {query}"
            siemplify.LOGGER.error(error_message)
            status = EXECUTION_STATE_FAILED
            siemplify.end(error_message, "false", status)
        
        output_message = f"qtype: {qtype}, query: {query}, records: {records}"
        status = EXECUTION_STATE_COMPLETED
        result_value = True
    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Failed to retrieve density records for {qtype} {query} for {INTEGRATION_NAME} server! Error: {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    for entity in siemplify.target_entities:
        print(entity.identifier)

    siemplify.LOGGER.info("\n  status: {}\n  result_value: {}\n  output_message: {}".format(status,result_value, output_message))
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
