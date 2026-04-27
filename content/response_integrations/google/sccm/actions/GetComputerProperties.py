from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from ..core.SCCMManager import SCCMManager
from ..core.constants import INTEGRATION_NAME, GET_COMPUTER_PROPERTIES_ACTION, ENRICH_PREFIX
from TIPCommon import (
    extract_configuration_param,
    dict_to_flat,
    flat_dict_to_csv,
    add_prefix_to_dict_keys,
)
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_COMPUTER_PROPERTIES_ACTION

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Server Address",
        is_mandatory=True,
    )
    domain = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Domain",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""

    try:
        sccm = SCCMManager(server_address, domain, username, password)
        enriched_entities = []
        failed_entities = []
        json_results = {}

        for entity in siemplify.target_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

            try:
                if entity.entity_type == EntityTypes.HOSTNAME:
                    # Remove domain
                    if "@" in entity.identifier:
                        host_name = entity.identifier.split("@")[0]
                    elif "." in entity.identifier:
                        host_name = entity.identifier.split(".")[0]
                    else:
                        host_name = entity.identifier

                    computer_properties = sccm.get_computer_info(host_name, siemplify)

                    if computer_properties:
                        json_results[entity.identifier] = computer_properties
                        flat_report = dict_to_flat(computer_properties)

                        # Enrich and add csv table
                        csv_output = flat_dict_to_csv(flat_report)
                        flat_report = add_prefix_to_dict_keys(
                            flat_report, ENRICH_PREFIX
                        )

                        siemplify.result.add_entity_table(entity.identifier, csv_output)
                        entity.additional_properties.update(flat_report)

                        enriched_entities.append(entity)
                        entity.is_enriched = True
                    else:
                        failed_entities.append(entity)

                siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")
            except Exception as e:
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        if enriched_entities:
            entities_names = [entity.identifier for entity in enriched_entities]
            output_message = (
                "Following entities were enriched with SCCM data:\n"
                + "\n".join(entities_names)
            )
            siemplify.update_entities(enriched_entities)
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

        if failed_entities:
            entities_names = [entity.identifier for entity in failed_entities]
            output_message += (
                "\nSCCM data for the following entities was not found:\n"
                + "\n".join(entities_names)
            )

        if not enriched_entities:
            output_message = "No entities were enriched."
            result_value = False

    except Exception as e:
        output_message = (
            f"Failed to connect to the Microsoft SCCM instance! The reason is {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"Status: {status}, Result Value: {result_value}, Output Message: {output_message}"
    )

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
