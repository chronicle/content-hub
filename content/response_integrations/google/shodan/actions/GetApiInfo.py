from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.ShodanManager import ShodanManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import flat_dict_to_csv
import json


@output_handler
def main():
    siemplify = SiemplifyAction()

    conf = siemplify.get_configuration("Shodan")
    verify_ssl = conf.get("Verify SSL", "False").lower() == "true"
    api_key = conf.get("API key", "")
    shodan = ShodanManager(api_key, verify_ssl=verify_ssl)

    api_info = shodan.get_api_info()
    json_results = {}
    if api_info:
        json_results = api_info
        siemplify.result.add_data_table("Shodan API Info", flat_dict_to_csv(api_info))
        output_message = "Successfully get information about the API plan"
        result_value = json.dumps(api_info)
    else:
        output_message = "Failed to get information about the API plan"
        result_value = "{}"

    # add json
    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
