from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# Imports
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.DShieldManager import DShieldManager


@output_handler
def main():
    siemplify = SiemplifyAction()

    # Configuration.
    conf = siemplify.get_configuration("DShield")
    api_root = conf["Api Root"]
    dshield = DShieldManager(api_root)

    # Execute Test Connectivity.
    result = dshield.test_connectivity()

    if result:
        output_message = "Connection Established."
        result_value = "true"
    else:
        output_message = "Connection Failed."
        result_value = "false"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
