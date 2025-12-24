from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.SixgillManager import PROVIDER, SixgillEnrichManager
from ..core.SixgillResultProcessor import SixgillActionResultProcessor


@output_handler
def main():
    siemplify = SiemplifyAction()
    client_id = siemplify.extract_configuration_param(PROVIDER, "Client Id")
    client_secret = siemplify.extract_configuration_param(PROVIDER, "Client Secret")

    sixgill_manager = SixgillEnrichManager(client_id, client_secret)
    sixgill_process = SixgillActionResultProcessor(siemplify, sixgill_manager)
    status, message, result = sixgill_process.test_connectivity()
    siemplify.end(message, result, status)


if __name__ == "__main__":
    main()
