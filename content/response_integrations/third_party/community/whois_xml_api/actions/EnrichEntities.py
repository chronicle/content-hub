from __future__ import annotations

import requests
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler

# Example Consts:
INTEGRATION_NAME = "Whois XML API"

SCRIPT_NAME = "WHOIS XML API EnrichEntities"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    api_key = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
    )

    url = f"https://www.whoisxmlapi.com/whoisserver/WhoisService?apiKey={api_key}&outputFormat=json"

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = (
        "output message :"  # human readable message, showed in UI as the action result
    )
    successfull_entities = []  # In case this actions contains entity based logic, collect successfull entity.identifiers

    json_result = {}
    for entity in siemplify.target_entities:
        siemplify.LOGGER.info(f"proccessing entity {entity.identifier}")
        if (
            entity.entity_type == EntityTypes.HOSTNAME and not entity.is_internal
        ) or entity.entity_type == EntityTypes.URL:
            entity_to_scan = entity.identifier

            scan_url = f"{url}&domainName={entity_to_scan}"

            response = requests.get(scan_url)
            response.raise_for_status()
            json_result[entity.identifier] = response.json()
            register_details = (
                response.json().get("WhoisRecord", {}).get("registrant", {})
            )
            if register_details:
                entity.additional_properties.update(register_details)
                successfull_entities.append(entity)

    if json_result:
        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))
    if successfull_entities:
        output_message += "\n Successfully processed entities:\n   {}".format(
            "\n   ".join([x.identifier for x in successfull_entities]),
        )
        siemplify.update_entities(
            successfull_entities,
        )  # This is the actual enrichment (this function sends the data back to the server)
    else:
        output_message += "\n No entities where processed."

    result_value = len(successfull_entities)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
