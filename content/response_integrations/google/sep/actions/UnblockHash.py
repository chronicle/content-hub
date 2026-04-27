from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SEPManager import SEP14Manager
from TIPCommon import extract_configuration_param


INTEGRATION_NAME = "SEP"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "SEP - Unblock Hash"
    result_value = "false"
    output_message = ""
    errors = ""

    conf = siemplify.get_configuration("SEP")
    username = conf["Username"]
    password = conf["Password"]
    domain = conf["Domain"]
    url = conf["Api Root"]
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
    )
    black_list = siemplify.parameters["Black List Name"]

    sep_manager = SEP14Manager(url, username, password, domain, verify_ssl=verify_ssl)

    enriched_entities = []
    blacklisted_hashes = sep_manager.getBlackList(black_list)["data"]

    for entity in siemplify.target_entities:
        if (
            entity.entity_type == EntityTypes.FILEHASH
            and len(entity.identifier) == 32
            and entity.identifier in blacklisted_hashes
        ):
            # Hash is MD5 and blacklisted
            enriched_entities.append(entity)
            blacklisted_hashes.remove(entity.identifier)

    try:
        # Unblock the hashes
        sep_manager.setBlackList("MD5", blacklisted_hashes)

    except Exception as e:
        # API call failed - no entities were enriched
        enriched_entities = []
        errors = f"Blocking failed: {str(e)}\n"
        siemplify.LOGGER.error(f"Blocking failed: {str(e)}\n")
        siemplify.LOGGER.exception(e)

    for entity in enriched_entities:
        entity.additional_properties.update({"SEP_IsUnBlocked": False})

    if enriched_entities:
        result_value = "true"
        entities_names = list(map(str, enriched_entities))

        output_message = (
            "The following hashes were unblocked by Symantec Endpoint Protection:\n"
            + "\n".join(entities_names)
        )
        output_message += errors

        siemplify.update_entities(enriched_entities)

    else:
        output_message += "No hashes were unblocked.\n"
        output_message += errors

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
