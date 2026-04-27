from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SymantecATPManager import SymantecATPManager


ATP_PROVIDER = "SymantecATP"
ACTION_NAME = "SymantecATP_Close Incident"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    conf = siemplify.get_configuration(ATP_PROVIDER)
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    verify_ssl = conf.get("Verify SSL", "false").lower() == "true"
    atp_manager = SymantecATPManager(
        conf.get("API Root"),
        conf.get("Client ID"),
        conf.get("Client Secret"),
        verify_ssl,
    )
    # Parameters.
    incident_uuid = siemplify.parameters.get("Incident UUID")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    is_closed = False

    try:
        is_closed = atp_manager.close_incident(incident_uuid)

    except Exception as err:
        siemplify.LOGGER.error(f"General error performing action {ACTION_NAME}")
        siemplify.LOGGER.exception(err)

    if is_closed:
        output_message = f"Incident with uuid {incident_uuid} was closed."
    else:
        output_message = f"Incident with uuid {incident_uuid} was not closed."

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  is_closed: {is_closed}\n output_message: {output_message}"
    )

    siemplify.end(output_message, is_closed)


if __name__ == "__main__":
    main()
