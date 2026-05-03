from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.URLVoidManager import URLVoidManager
from soar_sdk.SiemplifyAction import SiemplifyAction


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("URLVoid")
    api_root = conf["ApiUrl"]
    api_key = conf["ApiKey"]
    verify_ssl = conf.get("Verify SSL", "False").lower() == "true"

    urlvoid_manager = URLVoidManager(api_root, api_key, verify_ssl=verify_ssl)

    connectivity = urlvoid_manager.test_connectivity()
    output_message = "Connected Successfully"
    siemplify.end(output_message, connectivity)


if __name__ == "__main__":
    main()
