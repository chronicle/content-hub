from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SymantecATPManager import SymantecATPManager
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.SymantecATPManager import ATPEntityTypes


ATP_PROVIDER = "SymantecATP"
ACTION_NAME = "SymantecATP_Add To Blacklist"
INSIGHT_MESSAGE = "{0} was blacklisted."


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    conf = siemplify.get_configuration(ATP_PROVIDER)
    verify_ssl = conf.get("Verify SSL", "false").lower() == "true"
    atp_manager = SymantecATPManager(
        conf.get("API Root"),
        conf.get("Client ID"),
        conf.get("Client Secret"),
        verify_ssl,
    )

    errors = []
    blacklisted_entities = []
    result_value = False

    for entity in siemplify.target_entities:
        try:

            result = None

            if entity.entity_type == EntityTypes.FILEHASH:
                if atp_manager.is_hash_sha256(entity.identifier):
                    result = atp_manager.create_blacklist_policy(
                        entity.identifier, ATPEntityTypes.SHA256
                    )
                else:
                    result = atp_manager.create_blacklist_policy(
                        entity.identifier, ATPEntityTypes.MD5
                    )
            elif entity.entity_type == EntityTypes.HOSTNAME:
                result = atp_manager.create_blacklist_policy(
                    entity.identifier, ATPEntityTypes.HOST
                )
            elif entity.entity_type == EntityTypes.ADDRESS:
                result = atp_manager.create_blacklist_policy(
                    entity.identifier, ATPEntityTypes.ADDRESS
                )
            elif entity.entity_type == EntityTypes.URL:
                result = atp_manager.create_blacklist_policy(
                    entity.identifier, ATPEntityTypes.URL
                )

            if result:
                blacklisted_entities.append(entity)
                siemplify.add_entity_insight(
                    entity,
                    INSIGHT_MESSAGE.format(entity.identifier),
                    triggered_by=ATP_PROVIDER,
                )
                result_value = True

        except Exception as err:
            error_message = (
                f'Error adding "{entity.identifier}" to a blacklist, Error: {err}'
            )
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(err)
            errors.append(error_message)

    if result_value:
        output_message = f"{','.join([entity.identifier for entity in blacklisted_entities])} were blacklisted."
    else:
        output_message = "No entities were blacklisted."

    # Attach errors if exists.
    if errors:
        output_message = "{0},\n\nERRORS:\n{1}".format(
            output_message, " \n ".join(errors)
        )

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
