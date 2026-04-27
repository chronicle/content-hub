from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.CylanceManager import CylanceManager

SCRIPT_NAME = "Cylance - AddToGlobalList"


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

    list_type = siemplify.parameters.get("List Type")
    category = siemplify.parameters.get("Category")
    reason = (
        siemplify.parameters.get("Reason")
        if siemplify.parameters.get("Reason")
        else "None"
    )

    output_message = ""
    affected_entities = []
    failed_entities = []
    existing_entities = []

    for entity in siemplify.target_entities:
        try:
            if entity.entity_type == EntityTypes.FILEHASH:
                if cm.add_to_global_list(
                    entity.identifier,
                    list_type=list_type,
                    category=category,
                    reason=reason,
                ):
                    affected_entities.append(entity)
                else:
                    existing_entities.append(entity)

        except Exception as e:
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(
                f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
            )
            failed_entities.append(entity)
            siemplify.LOGGER._log.exception(e)

    if affected_entities:
        entities_names = [entity.identifier for entity in affected_entities]

        output_message += "\nFollowing hashes were added to {}:\n{}".format(
            list_type, "\n".join(entities_names)
        )
    else:
        output_message += f'\nNo hash was added to the global list "{list_type}"\n'
    if existing_entities:
        entities_names = [entity.identifier for entity in existing_entities]

        output_message += (
            "\nThere have already an entry for these threats in {}:\n{}".format(
                list_type, "\n".join(entities_names)
            )
        )

    if failed_entities:
        entities_names = [entity.identifier for entity in failed_entities]

        output_message += "\nFollowing hashes failed to added {}:\n{}".format(
            list_type, "\n".join(entities_names)
        )

    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
