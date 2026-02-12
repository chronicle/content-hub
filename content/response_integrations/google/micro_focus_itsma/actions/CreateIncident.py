from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

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
    display_label = siemplify.parameters.get("Display Label")
    description = siemplify.parameters.get("Description")
    impact_scope = siemplify.parameters.get("Impact Scope")
    urgency = siemplify.parameters.get("Urgency")
    service_id = siemplify.parameters.get("Service ID")

    incident_id = itsma_manager.create_incident(
        display_label, description, impact_scope, urgency, service_id
    )

    if incident_id:
        output_message = f'An incident with id "{incident_id}" was successfully created.'
    else:
        output_message = "No ticket was created."

    siemplify.end(output_message, incident_id)


if __name__ == "__main__":
    main()
