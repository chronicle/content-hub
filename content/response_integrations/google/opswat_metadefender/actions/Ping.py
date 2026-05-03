from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.OpswatMetadefenderManager import OpswatMetadefenderManager


@output_handler
def main():
    siemplify = SiemplifyAction()

    conf = siemplify.get_configuration("OpswatMetadefender")
    verify_ssl = conf.get("Verify SSL", "false").lower() == "true"
    om = OpswatMetadefenderManager(
        conf["ApiRoot"], api_key=conf["ApiKey"], verify_ssl=verify_ssl
    )

    if om.test_conectivity():
        output_message = "Connection Established"
        result_value = "true"

    else:
        output_message = "Connection failed. Please check your credentials."
        result_value = "false"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
