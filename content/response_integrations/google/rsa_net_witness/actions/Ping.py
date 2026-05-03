from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.RSAManager import RSA

# Consts.
RSA_PROVIDER = "RSANetWitness"


@output_handler
def main():

    # Configuration.
    siemplify = SiemplifyAction()
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
    connection = rsa_manager.test_connectivity()

    siemplify.end("Connection Established.", connection)


if __name__ == "__main__":
    main()
