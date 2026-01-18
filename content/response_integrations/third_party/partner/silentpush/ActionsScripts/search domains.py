from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import unix_now, convert_unixtime_to_datetime, output_handler
from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED,EXECUTION_STATE_TIMEDOUT

from constants import (INTEGRATION_NAME, SEARCH_DOMAIN_SCRIPT_NAME )
from SilentPushManager import SilentPushManager

@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SEARCH_DOMAIN_SCRIPT_NAME 
    
    # Extract Integration config
    server_url = siemplify.extract_configuration_param(INTEGRATION_NAME, "Silent Push Server")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")
    
    #Extract action parameter
    query = siemplify.extract_action_param("domain", print_value=True)
    limit = siemplify.extract_action_param("limit", print_value=True)
    skip = siemplify.extract_action_param("skip", print_value=True)
    start_date = siemplify.extract_action_param("start_date", print_value=True)
    end_date = siemplify.extract_action_param("end_date", print_value=True)
    risk_score_min = siemplify.extract_action_param("risk_score_min", print_value=True)
    risk_score_max = siemplify.extract_action_param("risk_score_max", print_value=True)
    domain_regex = siemplify.extract_action_param("domain_regex", print_value=True)
    name_server = siemplify.extract_action_param("name_server", print_value=True)
    asnum = siemplify.extract_action_param("asnum", print_value=True)
    asname = siemplify.extract_action_param("asname", print_value=True)
    min_ip_diversity = siemplify.extract_action_param("min_ip_diversity", print_value=True)
    registrar = siemplify.extract_action_param("registrar", print_value=True)
    min_asn_diversity = siemplify.extract_action_param("min_asn_diversity", print_value=True)
    certificate_issuer = siemplify.extract_action_param("certificate_issuer", print_value=True)
    whois_date_after = siemplify.extract_action_param("whois_date_after", print_value=True)

    try:
        sp_manager = SilentPushManager(server_url, api_key, logger=siemplify.LOGGER)

        siemplify.LOGGER.info(f"Connecting to {INTEGRATION_NAME}...\n")
        raw_response = sp_manager.search_domains(query=query,
        start_date=start_date,
        end_date=end_date,
        risk_score_min=risk_score_min,
        risk_score_max=risk_score_max,
        limit=limit,
        domain_regex=domain_regex,
        name_server=name_server,
        asnum=asnum,
        asname=asname,
        min_ip_diversity=min_ip_diversity,
        registrar=registrar,
        min_asn_diversity=min_asn_diversity,
        certificate_issuer=certificate_issuer,
        whois_date_after=whois_date_after,
        skip=skip)

        records = raw_response.get("response", {}).get("records", [])
        if not records:
            output_message = f"No domains found for query :{query}" 
        else:
            output_message = f"result : {records}"
        status = EXECUTION_STATE_COMPLETED
        result_value = True
    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Failed to retrieve to the search-domain records for {INTEGRATION_NAME} server! Error: {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    for entity in siemplify.target_entities:
        print(entity.identifier)



    siemplify.LOGGER.info("\n  status: {}\n  result_value: {}\n  output_message: {}".format(status,result_value, output_message))
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
