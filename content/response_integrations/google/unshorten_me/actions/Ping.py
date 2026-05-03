from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.UnshortenMeManager import UnshortenMeManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("UnshortenMe")
    use_ssl = conf.get("Use SSL", "False").lower() == "true"

    unshortenme_manager = UnshortenMeManager(use_ssl=use_ssl)

    # Test connectivity
    unshortenme_manager.test_connectivity()
    siemplify.end("Connected successfully.", "true")


if __name__ == "__main__":
    main()
