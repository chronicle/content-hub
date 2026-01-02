"""Uses DUO's Python SDK: https://github.com/duosecurity/duo_client_python
Uses the DUO Admin API: https://duo.com/docs/adminapi

Returns Trust Monitor events from the last X days

Note: Requires DUO Admin API keys

Created by: jtdepalm@sentara.com
"""

from __future__ import annotations

import json
import time

import duo_client
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

INTEGRATION_NAME = "DUO"
SCRIPT_NAME = "DUO Get Trust Monitor Events"


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
        # number of days back to obtain DUO Trust Monitor Events
        days_back = int(
            siemplify.extract_action_param("Number Days Back", print_value=True),
        )

        # logic to compute number of days back
        x_days_back = (86400 * 1000) * days_back
        timestamp_now = int(time.time() * 1000)
        timestamp_x_days_ago = timestamp_now - x_days_back

        # Using SDK. Setup initial authentication
        admin_api = duo_client.Admin(ikey=adminIntKey, skey=adminSec, host=duoApi)
        # Obtain DUO Trust Mon Events
        trust_monitor = admin_api.get_trust_monitor_events_by_offset(
            maxtime=timestamp_now,
            mintime=timestamp_x_days_ago,
        )

        results = {"trust_monitor": trust_monitor}
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
