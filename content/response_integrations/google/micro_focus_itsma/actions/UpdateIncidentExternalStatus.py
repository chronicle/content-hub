from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.MicroFocusITSMAManager import MicroFocusITSMAManager


ITSMA_PROVIDER = "MicroFocusITSMA"


@output_handler
def main():
    # Configuration
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration(ITSMA_PROVIDER)
    itsma_manager = MicroFocusITSMAManager(
        conf["API Root"],
        conf["Username"],
        conf["Password"],
        conf["Tenant ID"],
        conf["External System"],
        conf["External ID"],
        conf["Verify SSL"],
    )

    # Parameters.
    incident_id = siemplify.parameters.get("Incident ID")
    status = siemplify.parameters.get("Status")

    result_value = itsma_manager.update_external_incident_status(
        incident_id,
        status
    )

    if result_value:
        output_message = f'An incident with id "{incident_id}" external status was change to {status}'
    else:
        output_message = "No ticket was updated."

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
