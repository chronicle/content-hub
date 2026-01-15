from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import unix_now, convert_unixtime_to_datetime, output_handler
from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED,EXECUTION_STATE_TIMEDOUT

from constants import (INTEGRATION_NAME, GET_ASN_REPUTATION_SCRIPT_NAME )
from SilentPushManager import SilentPushManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_ASN_REPUTATION_SCRIPT_NAME 

    # Extract Integration config
    server_url = siemplify.extract_configuration_param(INTEGRATION_NAME, "Silent Push Server")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")

    asn = siemplify.extract_action_param("asn", print_value=True)
    explain = siemplify.extract_action_param("explain", print_value=True)
    limit = siemplify.extract_action_param("limit", print_value=True)

    try:
        sp_manager = SilentPushManager(server_url, api_key, logger=siemplify.LOGGER)
        raw_response = sp_manager.get_asn_reputation(asn, limit, explain)
        
        asn_reputation = extract_and_sort_asn_reputation(raw_response)
        
        if not asn_reputation:
            error_message = f"No reputation data found for ASN {asn}."
            siemplify.LOGGER.error(error_message)
            status = EXECUTION_STATE_FAILED
            siemplify.end(error_message, "false", status)
        
        status = EXECUTION_STATE_COMPLETED
        result_value = True
        data_for_table = prepare_asn_reputation_table(asn_reputation, explain)
        siemplify.result.add_result_json({"ASN": data_for_table})
        output_message = f"asn : {data_for_table}"
    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Failed to retrieve reputation data found for ASN {asn} for {INTEGRATION_NAME} server! Error: {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)


    for entity in siemplify.target_entities:
        print(entity.identifier)

    siemplify.LOGGER.info("\n  status: {}\n  result_value: {}\n  output_message: {}".format(status,result_value, output_message))
    siemplify.end(output_message, result_value, status)

def prepare_asn_reputation_table(asn_reputation: list, explain: bool) -> list:
    """
    Prepare the data for the ASN reputation table.

    Args:
        asn_reputation (list): List of ASN reputation entries.
        explain (bool): Whether to include explanations in the table.

    Returns:
        list: Data formatted for the table.
    """
    data_for_table = []
    
    for entry in asn_reputation:
        row = {
            "ASN": entry.get("asn"),
            "Reputation": entry.get("asn_reputation"),
            "ASName": entry.get("asname"),
            "Date": entry.get("date"),
        }
        if explain and entry.get("asn_reputation_explain") :
            print("On line 73", explain)
            row["Explanation"] = entry.get("asn_reputation_explain")
        data_for_table.append(row)
    return data_for_table

def extract_and_sort_asn_reputation(raw_response: dict) -> list:
    """
    Extract ASN reputation data and sort by date.

    Args:
        raw_response (dict): Raw response data from API.

    Returns:
        list: Sorted ASN reputation data.
    """
    response_data = raw_response.get("response", {})

    if not isinstance(response_data, dict):
        response_data = {"asn_reputation": response_data}

    asn_reputation = response_data.get("asn_reputation") or response_data.get("asn_reputation_history", [])

    if isinstance(asn_reputation, dict):
        asn_reputation = [asn_reputation]
    elif not isinstance(asn_reputation, list):
        asn_reputation = []

    return sorted(asn_reputation, key=lambda x: x.get("date", ""), reverse=True)


if __name__ == "__main__":
    main()
