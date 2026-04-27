from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SymantecATPManager import SymantecATPManager
from soar_sdk.SiemplifyDataModel import EntityTypes


ATP_PROVIDER = "SymantecATP"
ACTION_NAME = "SymantecATP_Submit File To Sandbox"


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
    command_ids = []
    submitted_entities = []

    for entity in siemplify.target_entities:
        try:
            if (
                entity.entity_type == EntityTypes.FILEHASH
                and atp_manager.is_hash_sha256(entity.identifier)
            ):
                command_id = atp_manager.submit_file_to_sandbox(entity.identifier)
                command_ids.append(command_id)
                submitted_entities.append(entity)
        except Exception as err:
            error_message = (
                f'Error submitting file "{entity.identifier}" to sandbox, Error: {err}'
            )
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(err)
            errors.append(error_message)

    if submitted_entities:
        output_message = f"{','.join([entity.identifier for entity in submitted_entities])} were submitted to sandbox."
    else:
        output_message = "No file hashes were submitted to sandbox."

    # Attach errors if exists.
    if errors:
        output_message = "{0},\n\nERRORS:\n{1}".format(
            output_message, " \n ".join(errors)
        )

    siemplify.end(output_message, ",".join(command_ids))


if __name__ == "__main__":
    main()
