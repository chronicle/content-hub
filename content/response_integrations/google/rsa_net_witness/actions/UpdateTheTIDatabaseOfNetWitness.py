from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.RSAManager import RSA

# Consts.
RSA_PROVIDER = "RSANetWitness"


@output_handler
def main():

    # Siemplify object and log definition.
    siemplify = SiemplifyAction()
    siemplify.script_name = "Update the 'TI' database of NetWitness"
    # CR: Remove this line or add logging to all of the actions steps
    siemplify.LOGGER.info("---- Started ----")

    # Variables Definition.
    result_value = True

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
    input_value = siemplify.parameters["Key Value String"]

    for entity in siemplify.target_entities:
        result = rsa_manager.upload_parsers_feeds(
            entity.identifier, input_value, siemplify.run_folder
        )
        if not result:
            result_value = False

    if result_value:
        output_message = "TI database updated successfully"
    else:
        output_message = "TI database was not updated."

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
