from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.IPVoidManager import IPVoidManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("IPVoid")
    api_root = conf["Api Root"]
    api_key = conf["Api Key"]
    use_ssl = conf.get("Use SSL", "False").lower() == "true"

    ipvoid_manager = IPVoidManager(api_root, api_key, use_ssl=use_ssl)

    # Test connectivity
    ipvoid_manager.test_connectivity()
    siemplify.end("Connected successfully.", "true")


if __name__ == "__main__":
    main()
