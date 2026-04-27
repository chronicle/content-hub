from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.TenableManager import TenableSecurityCenterManager
from soar_sdk.SiemplifyUtils import (
    dict_to_flat,
    add_prefix_to_dict_keys,
    convert_dict_to_json_result_dict,
)
import copy

SCRIPT_NAME = "TenableSecurityCenter - GetVulnerabilitiesForIP"
HIGH = "High"
SEVERITIES = {"Info": 0, "Low": 0, "Medium": 0, "High": 0, "Critical": 0}


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration("TenableSecurityCenter")
    server_address = conf["Server Address"]
    username = conf.get("Username")
    password = conf.get("Password")
    access_key = conf.get("Access Key")
    secret_key = conf.get("Secret Key")
    use_ssl = conf["Use SSL"].lower() == "true"

    tenable_manager = TenableSecurityCenterManager(
        server_address,
        username,
        password,
        access_key,
        secret_key,
        use_ssl,
    )

    enriched_entities = []
    json_results = {}

    for entity in siemplify.target_entities:
        try:
            if entity.entity_type == EntityTypes.ADDRESS:
                results = tenable_manager.get_vulnerabilities_for_ip(entity.identifier)
                json_results[entity.identifier] = results

                if results:
                    severities = copy.deepcopy(SEVERITIES)

                    for result in results:
                        severities[result["severity"]] += 1

                        if result["severity"] == HIGH:
                            entity.is_suspicious = True

                    entity.is_enriched = True

                    severities = add_prefix_to_dict_keys(
                        dict_to_flat(severities), "Tenable"
                    )
                    entity.additional_properties.update(severities)
                    enriched_entities.append(entity)

                    csv_output = tenable_manager.construct_csv(results)
                    siemplify.result.add_data_table(entity.identifier, csv_output)

        except Exception as e:
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(
                f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
            )
            siemplify.LOGGER._log.exception(e)

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]
        output_message = "Tenable: The following entities were enriched:\n" + "\n".join(
            entities_names
        )
        siemplify.update_entities(enriched_entities)

    else:
        output_message = "Tenable: No entities were enriched."

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
