from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import INTEGRATION_NAME, SEARCH_DOMAIN_SCRIPT_NAME
from ..core.silent_push_manager import SilentPushManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SEARCH_DOMAIN_SCRIPT_NAME

    # Extract Integration config
    server_url = siemplify.extract_configuration_param(
        INTEGRATION_NAME, "Silent Push Server"
    )
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")

    # Extract action parameter
    query = siemplify.extract_action_param("Domain", print_value=True)
    limit = siemplify.extract_action_param("Limit", print_value=True)
    skip = siemplify.extract_action_param("Skip", print_value=True)
    start_date = siemplify.extract_action_param("Start Date", print_value=True)
    end_date = siemplify.extract_action_param("End Date", print_value=True)
    risk_score_min = siemplify.extract_action_param("Risk Score Min", print_value=True)
    risk_score_max = siemplify.extract_action_param("Risk Score Max", print_value=True)
    domain_regex = siemplify.extract_action_param("Domain Regex", print_value=True)
    name_server = siemplify.extract_action_param("Name Server", print_value=True)
    asnum = siemplify.extract_action_param("Asnum", print_value=True)
    asname = siemplify.extract_action_param("Asname", print_value=True)
    min_ip_diversity = siemplify.extract_action_param("Min IP Diversity", print_value=True
    )
    registrar = siemplify.extract_action_param("Registrar", print_value=True)
    min_asn_diversity = siemplify.extract_action_param("Min ASN Diversity", print_value=True
    )
    certificate_issuer = siemplify.extract_action_param("Certificate Issuer", print_value=True
    )
    whois_date_after = siemplify.extract_action_param("Whois Date After", print_value=True
    )

    try:
        sp_manager = SilentPushManager(server_url, api_key, logger=siemplify.LOGGER)

        siemplify.LOGGER.info(f"Connecting to {INTEGRATION_NAME}...\n")
        raw_response = sp_manager.search_domains(
            query=query,
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
            skip=skip,
        )

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
        output_message = (
            f"Failed to retrieve to the search-domain"
            f"records for {INTEGRATION_NAME} server! Error: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    for entity in siemplify.target_entities:
        print(entity.identifier)

    siemplify.LOGGER.info(
        "\n  status: {}\n  result_value: {}\n  output_message: {}".format(
            status, result_value, output_message
        )
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
