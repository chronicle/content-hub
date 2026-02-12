from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.SymantecContentAnalysisManager import SymantecContentAnalysisManager

INTEGRATION_PROVIDER = "SymantecContentAnalysis"
ACTION_NAME = "SymantecContentAnalysis_Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    conf = siemplify.get_configuration(INTEGRATION_PROVIDER)

    # CR: verify_ssl = conf.get('Verify SSL').lower() == 'true'
    verify_ssl = True if conf.get("Verify SSL").lower() == "true" else False
    symantec_manager = SymantecContentAnalysisManager(
        conf.get("API Root"), conf.get("API Key"), verify_ssl
    )

    connected = symantec_manager.ping()

    if connected:
        output_message = "Connection Established."
    else:
        output_message = "Connection Failed"

    siemplify.end(output_message, True)


if __name__ == "__main__":
    main()
