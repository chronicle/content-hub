from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.ThreatCrowdManager import ThreatCrowdManager


@output_handler
def main():
    siemplify = SiemplifyAction()

    # Configuration.
    conf = siemplify.get_configuration("ThreatCrowd")
    use_ssl = conf["Use SSL"].lower() == "true"
    threat_crowd_manager = ThreatCrowdManager(use_ssl)

    is_connected = threat_crowd_manager.test_connectivity()

    if is_connected:
        output_message = "Connection Established"
        result_value = "true"
    else:
        output_message = "Connection Failed"
        result_value = "false"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
