from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SentinelOneManager import SentinelOneManager


# Consts.
SENTINEL_ONE_PROVIDER = "SentinelOne"


@output_handler
def main():
    # Configuration.
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration(SENTINEL_ONE_PROVIDER)
    sentinel_one_manager = SentinelOneManager(
        conf["Api Root"], conf["Username"], conf["Password"]
    )

    # Get system status.
    system_status = sentinel_one_manager.get_system_status()

    # Form output message.
    output_message = f"System Status is: {system_status}"

    siemplify.end(output_message, True)


if __name__ == "__main__":
    main()
