from __future__ import annotations

from marketorestpython.client import MarketoClient
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

SCRIPT_NAME = "Create lead"
INTEGRATION = "Marketo"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")
    json_result = {}

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

    # INIT ACTION PARAMETERS:
    email = siemplify.extract_action_param(param_name="Email").lower()
    first_name = siemplify.extract_action_param(param_name="First Name")
    last_name = siemplify.extract_action_param(param_name="Last Name")
    country = siemplify.extract_action_param(param_name="Country")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
    output_message = ""  # human readable message, showed in UI as the action result
    result_value = (
        False  # Set a simple result value, used for playbook if\else and placeholders.
    )

    try:
        input_data = [
            {
                "email": email,
                "firstName": first_name,
                "lastName": last_name,
                "country": country,
            },
        ]

        mc = MarketoClient(munchkin_id, client_id, client_secret, None, None)
        response = mc.execute(
            leads=input_data,
            method="create_update_leads",
            action="createOnly",
            lookupField="email",
        )
        json_result = response[0]

        if "reasons" in response[0]:
            output_message = (
                f"Failed to create the user <{email}> as a lead. Error: {response[0]}"
            )
            result_value = False
        else:
            output_message = f"The lead was created successfully for the user <{email}>, the lead ID is <{response[0].get('id')}>"
            result_value = True

    except Exception as e:
        output_message = f"Failed to create the user <{email}> as a lead. Error: {e}"
        result_value = False
        status = EXECUTION_STATE_FAILED
        raise Exception(f"Failed to create the user <{email}> as a lead. Error: {e}")

    siemplify.result.add_result_json(json_result)

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
