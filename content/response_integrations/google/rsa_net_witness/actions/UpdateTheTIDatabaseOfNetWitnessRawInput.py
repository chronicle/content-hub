from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.RSAManager import RSA

# Consts.
RSA_PROVIDER = "RSANetWitness"
ACTION_NAME = "RSANetWitness_Update The TI Database Of NetWitness Raw Input"


@output_handler
def main():
    # Siemplify object and log definition.
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME

    # Variables Definition.
    result_value = True
    errors = []

    # Configuration.
    config = siemplify.get_configuration(RSA_PROVIDER)

    # Configuration Parameters.
    concentrator_uri = config["Concentrator Api Root"]
    decoder_uri = config["Decoder Api Root"]
    username = config["Username"]
    password = config["Password"]
    verify_ssl = config.get("Verify SSL", "false").lower() == "true"

    rsa_manager = RSA(
        concentrator_uri=concentrator_uri,
        decoder_uri=decoder_uri,
        username=username,
        password=password,
        verify_ssl=verify_ssl,
    )

    # Parameters.
    identifiers = siemplify.parameters.get("Identifiers").split(",")
    key_value_items = siemplify.parameters.get("Key And Value Items", "")

    for identifier in identifiers:
        try:
            rsa_manager.upload_parsers_feeds(
                identifier, key_value_items, siemplify.run_folder
            )
        except Exception as err:
            error_massage = f'Failed uploading item: "{identifier}", Error: {err}'
            siemplify.LOGGER.error(error_massage)
            siemplify.LOGGER.exception(err)
            errors.append(error_massage)
            result_value = False

    if result_value:
        output_message = "TI database updated successfully"
    else:
        output_message = "TI database was updated partially or not updated at all."

    if errors:
        output_message = "{0}\n\nErrors:\n{1}".format(output_message, "\n".join(errors))

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
