from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.PortnoxManager import PortnoxManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("Portnox")
    api_root = conf["Api Root"]
    username = conf["Username"]
    password = conf["Password"]
    use_ssl = conf.get("Verify SSL", "False").lower() == "true"
    portnox_manager = PortnoxManager(api_root, username, password, use_ssl)
    portnox_manager.test_conectivity()

    output_message = "Connection Established"
    result_value = "true"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
