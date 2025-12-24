from __future__ import annotations

import json
import sys
import time

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.WebhookManager import WebhookManager


def seconds(timeframe_minutes):
    return 60 * timeframe_minutes


# Consts:
INTEGRATION_NAME = "Webhook"
SCRIPT_NAME = "Get Webhook Response"


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Extract Integration params:
    conf = siemplify.get_configuration(INTEGRATION_NAME)
    baseUrl = conf.get("URL")

    # INIT ACTION PARAMETERS:
    token_id = siemplify.extract_action_param(param_name="Token ID").strip()
    responses_choice = (
        siemplify.extract_action_param(param_name="Responses To Retrieve")
        .lower()
        .strip()
    )  # ALL or LATEST
    custom_timeframe = float(
        siemplify.extract_action_param(param_name="TimeFrame").strip(),
    )
    condition_type = siemplify.extract_action_param(
        param_name="Pending Condition",
    )  # TIMEFRAME or AWAITCLICK

    # Init result json:
    res_json = {}
    # Init result values:
    status = EXECUTION_STATE_FAILED
    output_message = f"Could not fetch information regarding token ID <{token_id}>"
    result_value = False
    # Init json for run parameters:
    runs_params_json = {}
    # Create manager instance for methods:
    webhookManager = WebhookManager(baseUrl)

    siemplify.LOGGER.info("================= Main - Started ====================")

    if is_first_run:
        if condition_type == "TimeFrame":
            timeframe = seconds(custom_timeframe)
            start_time = time.time()

    try:
        # Fetch info:
        if condition_type == "TimeFrame":
            if not is_first_run:
                runs_params_json = json.loads(siemplify.parameters["additional_data"])
                start_time = runs_params_json.get("start_time")
                timeframe = runs_params_json.get("timeframe")
            curr_time = time.time()
            duration = curr_time - start_time
            if duration >= timeframe:  # finished timeframe
                res_json = webhookManager.get_requests(
                    token_id,
                    responses_choice,
                )  # only call once.
                status = EXECUTION_STATE_COMPLETED
                if len(res_json.get("data")) > 0:
                    output_message = f"Fetched requests for token ID <{token_id}> after listenning <{custom_timeframe}> minutes."
                else:
                    output_message = (
                        f"After waiting <{custom_timeframe}> No requests were found"
                    )
                result_value = True
            else:  # Timeframe not finished
                status = EXECUTION_STATE_INPROGRESS
                output_message = f"Awaiting Timout: <{custom_timeframe}> minutes. Time passed: <{duration}> seconds."
                result_value = json.dumps(
                    {"timeframe": timeframe, "start_time": start_time},
                )

        if condition_type == "AwaitClick":
            res_json = webhookManager.get_requests(token_id, responses_choice)
            if len(res_json.get("data")) > 0:  # Click happened
                status = EXECUTION_STATE_COMPLETED
                output_message = (
                    f"Successfully fetched first requests for token ID <{token_id}>"
                )
                result_value = True
            else:
                status = EXECUTION_STATE_INPROGRESS
                output_message = (
                    f"Still waiting for first request for token ID <{token_id}>"
                )
                result_value = True

    except Exception as e:
        siemplify.LOGGER.error(e)
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Could not fetch information regarding token ID <{token_id}> " + str(e)
        )
        result_value = False
        raise Exception(e)

    finally:
        siemplify.LOGGER.info(
            f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
        )
        siemplify.result.add_result_json(res_json)
        siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
