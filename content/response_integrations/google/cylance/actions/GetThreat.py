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

SCRIPT_NAME = "Cylance - GetThreat"


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

    threshold = int(siemplify.parameters["Threshold"])

    affected_entities = []
    json_results = {}

    for entity in siemplify.target_entities:
        try:
            if entity.entity_type == EntityTypes.FILEHASH:
                threat = cm.get_threat(entity.identifier)

                json_results[entity.identifier] = threat

                if threat:
                    if threat.get("cylance_score", -1) > threshold:
                        entity.is_suspicious = True

                    # Enrich the entity
                    flat_threat = dict_to_flat(threat)
                    entity.additional_properties.update(
                        dict_to_flat(add_prefix_to_dict(flat_threat, "Cylance"))
                    )

                    entity.is_enriched = True
                    affected_entities.append(entity)

        except Exception as e:
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(
                f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
            )
            siemplify.LOGGER._log.exception(e)

    if affected_entities:
        entities_names = [entity.identifier for entity in affected_entities]

        output_message = "Following threats were found:\n{}".format(
            "\n".join(entities_names)
        )

        siemplify.update_entities(affected_entities)
    else:
        output_message = "No threats were found"

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
