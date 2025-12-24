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

from ..core.TelegramManager import TelegramManager

POLL = "poll"


IDENTIFIER = "Telegram"
SCRIPT_NAME = "Send Question And Wait"


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("================= Main - Param Init =================")
    bot_api_token = siemplify.extract_configuration_param(IDENTIFIER, "API Token")

    poll_id = siemplify.extract_action_param("Poll ID", print_value=True).strip()
    vote_threshold = int(
        siemplify.extract_action_param(
            "Answer Votes Threshold",
            print_value=True,
        ).strip(),
    )
    custom_timeframe = float(
        siemplify.extract_action_param("Waiting Timeframe", print_value=True).strip(),
    )
    limit = int(
        siemplify.extract_action_param("Scan back Limit", print_value=True).strip(),
    )

    status = EXECUTION_STATE_FAILED
    output_message = f"Could not fetch poll_results for poll <{poll_id}>. "
    result_value = False
    last_irrelevant_update_id = (
        None  # update_id of the last scanned update which is not related to our poll.
    )

    # Creating an instance of Telegram object
    telegram_manager = TelegramManager(bot_api_token)

    siemplify.LOGGER.info("================= Main - Started ====================")

    poll_results = {}

    # Checking for votes:
    try:
        if is_first_run:
            seconds_in_minute = 60
            timeframe = custom_timeframe * seconds_in_minute
            start_time = time.time()
        else:
            # Fetch info regarding time passed and updates:
            runs_params_json = json.loads(siemplify.parameters["additional_data"])
            start_time = runs_params_json.get("start_time")
            timeframe = float(runs_params_json.get("timeframe"))
            if "last_update" in runs_params_json:  # get offset to scan updates from:
                last_irrelevant_update_id = (
                    int(runs_params_json.get("last_update"))
                    if runs_params_json.get("last_update") is not None
                    else None
                )
        curr_time = time.time()
        duration = curr_time - start_time  # overall action runtime
        poll_results = telegram_manager.get_updates(
            limit,
            last_irrelevant_update_id,
            POLL,
        )
        if not poll_results["ok"]:  # Error fetching updates
            raise Exception(poll_results["description"])
        if len(poll_results["result"]) > 0:  # found (some) answers
            if is_first_run:  # don't re-scan irrelevant updates next run:
                past_irrelevant_results = [
                    x
                    for x in poll_results["result"]
                    if "poll" in x and x.get("poll").get("id") != poll_id
                ]
                if past_irrelevant_results:
                    last_irrelevant_update_id = max(
                        [update["update_id"] for update in past_irrelevant_results],
                    )  # to scan less updates next run
            # Keep only our poll:
            poll_results["result"] = [
                x
                for x in poll_results["result"]
                if "poll" in x and x.get("poll").get("id") == poll_id
            ]
        if len(poll_results["result"]) > 0:  # found our answers:
            # check threshold satisfaction:
            for result in poll_results.get("result"):
                for option in result.get("poll").get("options"):
                    if (
                        option.get("voter_count") >= vote_threshold
                    ):  # threshold satisfied.
                        output_message = (
                            f"answers threshold met for poll <{poll_id}> after "
                            f"<{duration}s>"
                        )
                        status = EXECUTION_STATE_COMPLETED
                        result_value = True
                        break
            if not result_value:
                if duration >= timeframe:  # Timeframe reached.
                    output_message = (
                        f"Custom timeframe was reached for poll <{poll_id}>, "
                        f"threshold was not met, \nbut some answers were fecthed"
                    )
                    status = EXECUTION_STATE_COMPLETED
                    result_value = False
                else:
                    output_message = (
                        f"Votes threashold for poll <{poll_id}> not yet met, "
                        "though some answers were found.\n"
                        f"Still waiting. \n Time passed:<{duration}>s"
                    )
                    status = EXECUTION_STATE_INPROGRESS
                    result_value = json.dumps(
                        {
                            "timeframe": timeframe,
                            "start_time": start_time,
                            "last_update": last_irrelevant_update_id,
                        },
                    )
        elif duration >= timeframe:  # Timeframe reached.
            output_message = (
                f"Custom timeframe was reached for poll <{poll_id}>. No answers found."
            )
            status = EXECUTION_STATE_COMPLETED
            result_value = False
        else:
            output_message = (
                f"Still waiting for answers to meet requirements for poll {poll_id}.\n"
                f"Time passed:<{duration}s>"
            )
            status = EXECUTION_STATE_INPROGRESS
            result_value = json.dumps(
                {
                    "timeframe": timeframe,
                    "start_time": start_time,
                    "last_update": last_irrelevant_update_id,
                },
            )
    except Exception as e:
        siemplify.LOGGER.error("ERROR: " + str(e))
        output_message += f"Error: {e!s}"
    finally:
        fin_results = {}
        fin_results["raw"] = poll_results
        if poll_results.get("ok") is True and len(poll_results.get("result")) > 0:
            fin_results["answers"] = (
                poll_results.get("result")[len(poll_results.get("result")) - 1]
                .get("poll")
                .get("options")
            )
        siemplify.LOGGER.info(
            f"\n  status: {status}\n  result_value: {result_value}\n"
            f"  output_message: {output_message}",
        )

        siemplify.LOGGER.info("----------------- Main - Finished -----------------")
        siemplify.result.add_result_json(fin_results)
        siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
