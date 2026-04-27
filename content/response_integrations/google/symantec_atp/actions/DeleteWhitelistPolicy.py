from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SymantecATPManager import SymantecATPManager


ATP_PROVIDER = "SymantecATP"
ACTION_NAME = "SymantecATP_Delete whitelist policy"
INSIGHT_MESSAGE = "{0} was Whitelisted."


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
    whitelisted_entities = []
    result_value = False

    for entity in siemplify.target_entities:
        try:
            atp_manager.delete_whitelist_policy_by_identifier(entity.identifier)
            result_value = True
        except Exception as err:
            error_message = f'Error deleting whitelist policy for entity "{entity.identifier}", Error: {err}'
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(err)
            errors.append(error_message)

    if result_value:
        output_message = f"{','.join([entity.identifier for entity in whitelisted_entities])} whitelist policies were deleted."
    else:
        output_message = "No whitelist policies were deleted."

    # Attach errors if exists.
    if errors:
        output_message = "{0},\n\nERRORS:\n{1}".format(
            output_message, " \n ".join(errors)
        )

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
