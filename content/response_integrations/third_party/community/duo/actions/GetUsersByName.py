"""Uses DUO's Python SDK: https://github.com/duosecurity/duo_client_python
Uses the DUO Admin API: https://duo.com/docs/adminapi

Obtains user, authentication and device data from DUO MFA on a specific user
Note: Requires DUO Admin API keys

Created by: jtdepalm@sentara.com
"""

from __future__ import annotations

import json

import duo_client
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

INTEGRATION_NAME = "DUO"
SCRIPT_NAME = "DUO Get Users by Name"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
    try:
        # list to contain results from action
        res = []
        user_id = None

        duoApi = siemplify.extract_configuration_param(
            provider_name=INTEGRATION_NAME,
            param_name="API Hostname",
        )
        adminSec = siemplify.extract_configuration_param(
            provider_name=INTEGRATION_NAME,
            param_name="Admin Secret Key",
        )
        adminIntKey = siemplify.extract_configuration_param(
            provider_name=INTEGRATION_NAME,
            param_name="Admin Integration Key",
        )

        # ***parameters***
        # target username to obtain data on
        username = siemplify.extract_action_param("Username", print_value=True)
        # Using SDK. Setup initial authentication.
        admin_api = duo_client.Admin(ikey=adminIntKey, skey=adminSec, host=duoApi)
        # obtain target user's data from DUO
        user_data = admin_api.get_users_by_name(username=username)

        for data in user_data:
            user_id = data["user_id"]

        results = {"user_name": username, "user_id": user_id, "user_data": user_data}
        res.append(results)
        siemplify.result.add_result_json(res)
        json_result = json.dumps(res)
        output_message = f"Results: {json_result}"

    except Exception as e:
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Failed. Error is : {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.LOGGER.info(f"Result: {result}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
