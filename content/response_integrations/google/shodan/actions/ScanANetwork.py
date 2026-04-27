from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.ShodanManager import ShodanManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes


@output_handler
def main():
    siemplify = SiemplifyAction()

    conf = siemplify.get_configuration("Shodan")
    verify_ssl = conf.get("Verify SSL", "False").lower() == "true"
    api_key = conf.get("API key", "")
    shodan = ShodanManager(api_key, verify_ssl=verify_ssl)

    ips_list = []
    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.ADDRESS:
            ips_list.append(entity.identifier)
    # Convert ips list to strings
    ips = ",".join(ips_list)

    scan_info = shodan.scan(ips)
    if scan_info:
        scan_id = scan_info.get("id")
        output_message = (
            f"Successfully scan a network using Shodan. Scan ID is {scan_id}"
        )
        result_value = scan_id
    else:
        output_message = "Failed to scan a network using Shodan"
        result_value = "{}"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
