from __future__ import annotations

import json

from marketorestpython.client import MarketoClient
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

INTEGRATION = "Marketo"
SCRIPT_NAME = "Request Campaign"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")
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

    # INIT ACTION PARAMETERS:
    campaign_id = siemplify.extract_action_param(
        param_name="Campaign Id",
        input_type=int,
    )
    lead_id = siemplify.extract_action_param(param_name="Lead Id", input_type=int)
    tokens = siemplify.extract_action_param(param_name="Tokens Json")

    json_tokens = json.loads(tokens)
    json_tokens = {
        k: (v.lower() if "password" not in k.lower() else v)
        for k, v in json_tokens.items()
    }
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        failed_entities = []  # In case this actions contains entity based logic, collect failed entity.identifiers
        successfull_entities = []  # In case this actions contains entity based logic, collect successfull entity.identifiers

        mc = MarketoClient(munchkin_id, client_id, client_secret, None, None)
        response = mc.execute(
            method="request_campaign",
            id=campaign_id,
            leads=[lead_id],
            tokens=json_tokens,
        )
        output_message = f"The Campaign ID <{campaign_id}> was sent successfully to the Lead ID <{lead_id}>"
        result_value = True
        status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message += (
            f"\n The Campaign ID <{campaign_id}> wasn't sent to the Lead ID <{lead_id}>"
        )
        raise  # used to return entire error details - including stacktrace back to client UI. Best for most usecases
        # in case you want to handle the error yourself, don't raise, and handle error result ouputs:

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
