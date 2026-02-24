from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import INTEGRATION_NAME, LIST_IP_INFORMATION_SCRIPT_NAME
from ..core.silent_push_manager import SilentPushManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_IP_INFORMATION_SCRIPT_NAME

    # Extract Integration config
    server_url = siemplify.extract_configuration_param(INTEGRATION_NAME, "Silent Push Server")
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")

    ips = siemplify.extract_action_param("Ips", print_value=True)
    ips = ips.split(",")

    try:
        sp_manager = SilentPushManager(server_url, api_key, logger=siemplify.LOGGER)
        ipv4_addresses, ipv6_addresses = validate_ips(ips, sp_manager)

        results = []
        if ipv4_addresses:
            results.extend(gather_ip_information(sp_manager, ipv4_addresses, resource="ipv4"))

        if ipv6_addresses:
            results.extend(gather_ip_information(sp_manager, ipv6_addresses, resource="ipv6"))

        if not results:
            error_message = f"No information found for IPs: {', '.join(ips)}"
            siemplify.LOGGER.error(error_message)
            status = EXECUTION_STATE_FAILED
            siemplify.end(error_message, "false", status)

        output_message = f"Comprehensive IP Information : {results}"
        status = EXECUTION_STATE_COMPLETED
        result_value = True
    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to retrieve Comprehensive IP Information "
            f"of IP's :{ips} for {INTEGRATION_NAME} server! Error: {error}"
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


def validate_ips(ips: list, client: SilentPushManager) -> tuple:
    """
    Validates and categorizes the IPs into IPv4 and IPv6 addresses.

    Args:
        ips (list): List of IPs to validate.
        client (SilentPushManager): The client instance to use for validation.

    Returns:
        tuple: A tuple containing two lists: (ipv4_addresses, ipv6_addresses)
    """
    ipv4_addresses = []
    ipv6_addresses = []

    for ip in ips:
        if client.validate_ip_address(ip, allow_ipv6=False):  # IPv4
            ipv4_addresses.append(ip)
        elif client.validate_ip_address(ip, allow_ipv6=True):  # IPv6
            ipv6_addresses.append(ip)

    return ipv4_addresses, ipv6_addresses


def gather_ip_information(client: SilentPushManager, ip_addresses: list, resource: str) -> list:
    """
    Gathers IP information for a given list of IP addresses.

    Args:
        client (SilentPushManager): The client instance to query IP information.
        ip_addresses (list): The list of IPs to gather information for.
        resource (str): The resource type ('ipv4' or 'ipv6').

    Returns:
        list: A list of IP to ASN information.
    """
    ip_info = client.list_ip_information(ip_addresses, resource=resource)
    return ip_info.get("response", {}).get("ip2asn", [])


if __name__ == "__main__":
    main()
