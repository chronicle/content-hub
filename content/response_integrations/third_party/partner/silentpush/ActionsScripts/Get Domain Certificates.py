from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import unix_now, convert_unixtime_to_datetime, output_handler
from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED,EXECUTION_STATE_TIMEDOUT


from constants import (INTEGRATION_NAME, GET_DOMAIN_CERTIFICATES_SCRIPT_NAME )
from SilentPushManager import SilentPushManager

@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_DOMAIN_CERTIFICATES_SCRIPT_NAME 

    # Extract Integration config
    server_url = siemplify.extract_configuration_param(INTEGRATION_NAME, "Silent Push Server")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")

    domain = siemplify.extract_action_param("domain", print_value=True)
    domain_regex = siemplify.extract_action_param("domain_regex", print_value=True)
    certificate_issuer = siemplify.extract_action_param("certificate_issuer", print_value=True)
    date_min = siemplify.extract_action_param("date_min", print_value=True)
    date_max = siemplify.extract_action_param("date_max", print_value=True)
    prefer = siemplify.extract_action_param("prefer", print_value=True)
    max_wait = siemplify.extract_action_param("max_wait", print_value=True)
    with_metadata = siemplify.extract_action_param("with_metadata", print_value=True)
    skip = siemplify.extract_action_param("skip", print_value=True)
    limit = siemplify.extract_action_param("limit", print_value=True)

    params = {
        "domain_regex": domain_regex,
        "cert_issuer": certificate_issuer,
        "date_min": date_min,
        "date_max": date_max,
        "prefer": prefer,
        "max_wait": int(max_wait) if max_wait else None,
        "with_metadata":  bool(with_metadata) if with_metadata else False,
        "skip":  int(skip) if skip else None,
        "limit": int(limit) if limit else None,
    }
    filter_params = {key:value for key, value in params.items() if value is not None}

    try:
        sp_manager = SilentPushManager(server_url, api_key, logger=siemplify.LOGGER)
        raw_response = sp_manager.get_domain_certificates(domain, **(filter_params or {}))
        
        if raw_response.get("response", {}).get("job_status", {}):
            job_details = raw_response.get("response", {}).get("job_status", {})
            
            output_message = f"domain: {domain}, job_details: {job_details}"
            status = EXECUTION_STATE_COMPLETED
            result_value = True
            
            siemplify.end(output_message, result_value, status)
       
        certificates = raw_response.get("response", {}).get("domain_certificates", [])
        metadata = raw_response.get("response", {}).get("metadata", {})

        if not certificates:
            error_message = f"No certificates found for domain: {domain}"
            siemplify.LOGGER.error(error_message)
            status = EXECUTION_STATE_FAILED
            siemplify.end(error_message, "false", status)    
        
        output_message = f"domain: {domain}, certificates: {certificates}, metadata: {metadata}"
        status = EXECUTION_STATE_COMPLETED
        result_value = True
    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Failed to retrieve certificates data for domain {domain} for {INTEGRATION_NAME} server! Error: {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    for entity in siemplify.target_entities:
        print(entity.identifier)

    siemplify.LOGGER.info("\n  status: {}\n  result_value: {}\n  output_message: {}".format(status,result_value, output_message))
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
