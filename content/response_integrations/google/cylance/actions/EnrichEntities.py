from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.CylanceManager import CylanceManager
from soar_sdk.SiemplifyUtils import (
    dict_to_flat,
    add_prefix_to_dict,
    convert_dict_to_json_result_dict,
)

SCRIPT_NAME = "Cylance - EnrichEntities"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration("Cylance")

    server_address = conf["Server Address"]
    application_secret = conf["Application Secret"]
    application_id = conf["Application ID"]
    tenant_identifier = conf["Tenant Identifier"]

    cm = CylanceManager(
        server_address, application_id, application_secret, tenant_identifier
    )

    enriched_entities = []
    json_results = {}

    for entity in siemplify.target_entities:
        try:
            device = None

            if entity.entity_type == EntityTypes.ADDRESS:
                device = cm.get_device_by_name(entity.identifier, is_address=True)
            elif entity.entity_type == EntityTypes.HOSTNAME:
                device = cm.get_device_by_name(entity.identifier)

            if device:
                json_results[entity.identifier] = device

                flat_device = add_prefix_to_dict(dict_to_flat(device), "Cylance")
                entity.additional_properties.update(flat_device)

                entity.is_enriched = True
                enriched_entities.append(entity)

        except Exception as e:
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(
                f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
            )
            siemplify.LOGGER._log.exception(e)

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]

        output_message = "Following entities were enriched:\n" + "\n".join(
            entities_names
        )

        siemplify.update_entities(enriched_entities)

    else:
        output_message = "No entities were enriched."

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
