from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.NSMManager import NsmManager

# Consts
# Provider Sign.
NSM_PROVIDER = "McAfeeNSM"


@output_handler
def main():
    # configurations.
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration(NSM_PROVIDER)
    nsm_manager = NsmManager(
        conf["API Root"],
        conf["Username"],
        conf["Password"],
        conf["Domain ID"],
        conf["Siemplify Policy Name"],
        conf["Sensors Names List Comma Separated"],
    )

    # End session.
    nsm_manager.logout()

    siemplify.end("Connection Established.", True)


if __name__ == "__main__":
    main()
