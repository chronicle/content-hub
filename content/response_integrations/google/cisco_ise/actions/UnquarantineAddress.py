from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CiscoISEManager import CiscoISEManager
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon import extract_configuration_param

INTEGRATION_NAME = "CiscoISE"


@output_handler
def main():
    # Configuration.
    siemplify = SiemplifyAction()
    siemplify.script_name = "CiscoISE_Unquarantine Address"
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Password"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    cim = CiscoISEManager(api_root, username, password, verify_ssl)

    # Variables.
    unquarantined_ips = []
    result_value = False
    errors = []
    errors_flag = False

    ip_addresses = [
        entity.identifier
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.ADDRESS
    ]

    for ip_address in ip_addresses:
        try:
            mac_address = cim.get_endpoint_mac_by_ip(ip_address)
            cim.unquarantine_endpoint(mac_address)
            unquarantined_ips.append(ip_address)
        except Exception as err:
            siemplify.LOGGER.error(f'Error unquarantine "{ip_address}", ERROR: {err}')
            errors_flag = True
            errors.append(f'Error unquarantine "{ip_address}", ERROR: {err}')

    if unquarantined_ips:
        output_message = f"{','.join(unquarantined_ips)} were unquarantined."
        result_value = True
    else:
        output_message = "No addresses were unquarantined."

    if errors_flag:
        output_message = f"{output_message} \n \n  ERRORS: {errors}"
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
