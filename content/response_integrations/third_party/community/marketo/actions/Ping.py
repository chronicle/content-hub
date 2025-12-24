from __future__ import annotations

from marketorestpython.client import MarketoClient
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

INTEGRATION = "Marketo"


@output_handler
def main():
    siemplify = SiemplifyAction()
    output_message = ""

    # INIT INTEGRATION PARAMETERS:
    client_id = siemplify.extract_configuration_param(
        provider_name=INTEGRATION,
        param_name="Client Id",
    )
    client_secret = siemplify.extract_configuration_param(
        provider_name=INTEGRATION,
        param_name="Client Secret",
    )
    munchkin_id = siemplify.extract_configuration_param(
        provider_name=INTEGRATION,
        param_name="Munchkin Id",
    )

    try:
        mc = MarketoClient(munchkin_id, client_id, client_secret, None, None)
        lead = mc.execute(
            method="get_lead_by_id",
            id=1,
            fields=["firstName", "middleName", "lastName", "department"],
        )
        status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
        output_message = ""
    except Exception:
        raise

    siemplify.end("Success", True)


if __name__ == "__main__":
    main()
