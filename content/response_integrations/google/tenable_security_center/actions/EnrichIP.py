from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, validate_string_python2
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.TenableManager import TenableSecurityCenterManager, TenableSecurityCenterException
from soar_sdk.SiemplifyUtils import (
    dict_to_flat,
    add_prefix_to_dict_keys,
    convert_dict_to_json_result_dict,
)
from ..core.constants import SCRIPT_NAME


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
    repo_name = siemplify.parameters["Repository Name"]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

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
    invalid_enriched_entity = []
    output_message = ""
    result_value = True
    invalid_ip = []

    repo_name = validate_string_python2(repo_name)

    for entity in siemplify.target_entities:
        try:
            if entity.entity_type == EntityTypes.ADDRESS:

                entity.entity_type = validate_string_python2(entity.entity_type)

                ip_info = tenable_manager.get_ip_info(entity.identifier, repo_name)

                json_results[entity.identifier] = ip_info.to_json()

                ip_info = add_prefix_to_dict_keys(
                    dict_to_flat(ip_info.to_json()), "Tenable"
                )

                entity.is_enriched = True

                entity.additional_properties.update(ip_info)

                enriched_entities.append(entity)

        except TenableSecurityCenterException as e:

            invalid_ip.append(entity.identifier)

        except Exception as e:
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(
                f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
            )
            siemplify.LOGGER._log.exception(e)

    if invalid_ip:
        output_message += (
            "Tenable: The following entities were not enriched:\n"
            + ", ".join(invalid_ip)
        )

    if enriched_entities and invalid_enriched_entity:
        invalid_enriched_entity = [
            entity.identifier for entity in invalid_enriched_entity
        ]
        output_message += (
            "\nTenable: The following entities were not enriched:\n"
            + ", ".join(invalid_enriched_entity)
        )

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]
        output_message += (
            "\nTenable: The following entities were enriched:\n"
            + ", ".join(entities_names)
        )
        siemplify.update_entities(enriched_entities)
        result_value = True

    else:
        output_message = "\nTenable: No entities were enriched."
        result_value = False

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  is_success: {result_value}\n  output_message: {output_message}"
    )

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
