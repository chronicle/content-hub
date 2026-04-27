from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.MalShareManager import MalShareManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    # Configuration.
    conf = siemplify.get_configuration("MalShare")
    api_key = conf["Api Key"]
    verify_ssl = conf.get("Verify SSL", "false").lower() == "true"
    malshare = MalShareManager(api_key, verify_ssl)

    malshare.test_connectivity()

    # If no exception occur - then connection is successful
    siemplify.end("Connected successfully.", "true")


if __name__ == "__main__":
    main()
