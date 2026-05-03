from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.HaveIBeenPwnedManager import HaveIBeenPwnedManager
from soar_sdk.SiemplifyAction import SiemplifyAction


@output_handler
def main():
    siemplify = SiemplifyAction()

    conf = siemplify.get_configuration("HaveIBeenPwned")
    api_key = conf.get("Api Key")
    verify_ssl = str(conf.get("Verify SSL", "False")).lower() == "true"
    hibp_manager = HaveIBeenPwnedManager(api_key, use_ssl=verify_ssl)

    hibp_manager.test_connectivity()

    output_message = "Connection Established"
    result_value = "true"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
