from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# Imports
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.AlienVaultTIManager import AlienVaultTIManager


@output_handler
def main():
    siemplify = SiemplifyAction()

    # Configuration.
    conf = siemplify.get_configuration("AlienVaultTI")
    api_key = conf["Api Key"]
    alienvault = AlienVaultTIManager(api_key)

    # Execute Test Connectivity.
    result = alienvault.test_connectivity()

    if result:
        output_message = "Connection Established."
    else:
        output_message = "Connection Failed."

    siemplify.end(output_message, result)


if __name__ == "__main__":
    main()
