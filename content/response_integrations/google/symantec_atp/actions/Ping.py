from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SymantecATPManager import SymantecATPManager

ATP_PROVIDER = "SymantecATP"
ACTION_NAME = "SymantecATP_Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    conf = siemplify.get_configuration(ATP_PROVIDER)
    verify_ssl = conf.get("Verify SSL", "false").lower() == "true"
    # Init fuction does the connection.
    atp_manager = SymantecATPManager(
        conf.get("API Root"),
        conf.get("Client ID"),
        conf.get("Client Secret"),
        verify_ssl,
    )

    if atp_manager:
        output_message = "Connection Established."
    else:
        output_message = "Connection Failed."

    siemplify.end(output_message, True)


if __name__ == "__main__":
    main()
