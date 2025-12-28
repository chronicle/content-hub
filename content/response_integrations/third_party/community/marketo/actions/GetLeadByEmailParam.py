from __future__ import annotations

from marketorestpython.client import MarketoClient
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

INTEGRATION = "Marketo"
SCRIPT_NAME = "Get Lead By Email Param"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

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
    email = siemplify.extract_action_param(param_name="Email")
    email = email.lower()

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = ""  # human readable message, showed in UI as the action result
    result_value = (
        False  # Set a simple result value, used for playbook if\else and placeholders.
    )
    lead_details = {}

    try:
        mc = MarketoClient(munchkin_id, client_id, client_secret, None, None)
        lead_details = mc.execute(
            method="get_multiple_leads_by_filter_type",
            filterType="email",
            filterValues=str(email),
        )
        if lead_details:
            output_message += f"The user <{email}> exists in Marketo, the lead ID is: <{lead_details[0].get('id')}>"
            result_value = True
        else:
            output_message += f"The user <{email}> doesn't exists in Marketo"
            result_value = False

    except Exception as e:
        result_value = False
        output_message += f"\n failed to find lead for: {email}"
        raise Exception(f"Response:{lead_details}. Error:{e}")

    siemplify.result.add_result_json(lead_details)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
