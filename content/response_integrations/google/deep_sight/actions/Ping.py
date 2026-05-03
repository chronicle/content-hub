from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.DeepSightManager import DeepSightManager
from soar_sdk.SiemplifyAction import SiemplifyAction


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("DeepSight")
    api_key = conf["ApiKey"]
    use_ssl = conf["Use SSL"].lower() == "true"
    deepsight_manager = DeepSightManager(api_key, use_ssl=use_ssl)

    deepsight_manager.test_connectivity()

    siemplify.end("Connected succesfully.", "true")


if __name__ == "__main__":
    main()
