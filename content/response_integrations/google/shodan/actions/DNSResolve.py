from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.ShodanManager import ShodanManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import flat_dict_to_csv
from soar_sdk.SiemplifyDataModel import EntityTypes
import json


@output_handler
def main():
    siemplify = SiemplifyAction()

    conf = siemplify.get_configuration("Shodan")
    verify_ssl = conf.get("Verify SSL", "False").lower() == "true"
    api_key = conf.get("API key", "")
    shodan = ShodanManager(api_key, verify_ssl=verify_ssl)

    hostnames_list = []
    json_results = {}
    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.HOSTNAME:
            hostnames_list.append(entity.identifier)
    # Convert hostnames list to string
    hostnames = ",".join(hostnames_list)

    hostnames_info = shodan.dns_resolve(hostnames)
    if hostnames_info:
        json_results = hostnames_info
        siemplify.result.add_data_table(
            "Shodan DNS Reslove Report", flat_dict_to_csv(hostnames_info)
        )
        output_message = "Successfully look up the IP address for the following hostnames: {0} \n".format(
            "\n".join(hostnames_list)
        )
        result_value = json.dumps(hostnames_info)
    else:
        output_message = "Failed to look up the IP address for the following hostnames: {0} \n".format(
            "\n".join(hostnames_list)
        )
        result_value = "{}"

    # add json
    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
