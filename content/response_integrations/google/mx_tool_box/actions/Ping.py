from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.MXToolBoxManager import MXToolBoxManager

MXTOOLBOX_PROVIDER = "MXToolBox"


@output_handler
def main():
    # Configurations.
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration(MXTOOLBOX_PROVIDER)
    verify_ssl = conf["Verify SSL"].lower() == "true"
    mx_tool_box_manager = MXToolBoxManager(
        conf["API Root"], conf["API Key"], verify_ssl
    )

    result_value = mx_tool_box_manager.ping()

    if result_value:
        output_message = "Connection Established."
    else:
        output_message = "Connection Failed."

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
