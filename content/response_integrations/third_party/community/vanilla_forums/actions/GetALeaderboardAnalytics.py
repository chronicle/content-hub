from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.VanillaManager import VanillaManager

# Consts:
INTEGRATION_NAME = "VanillaForums"
SCRIPT_NAME = "Get a Leaderboard Analytics"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Integration params:
    conf = siemplify.get_configuration(INTEGRATION_NAME)
    apiToken = conf.get("API Token")
    baseUrl = conf.get("URL")

    # Action params:
    leaderboards = siemplify.extract_action_param(param_name="Leaderboards")
    limit = siemplify.extract_action_param(param_name="Amount Limit").strip()
    start_time = siemplify.extract_action_param(param_name="From").strip()
    end_time = siemplify.extract_action_param(param_name="To").strip()
    # Split leaderboards to a list of boards:
    leaderboards_lst = leaderboards.split(",")

    # Init result json:
    res_json = []
    res_sub_json = {}

    # Init result values:
    status = EXECUTION_STATE_FAILED
    output_message = ""
    result_value = False

    # Creating manager instance for methods:
    vanillaManager = VanillaManager(apiToken, baseUrl)
    try:
        # Fetch each leaderboard analytics:
        for board in leaderboards_lst:
            board = board.strip()
            res_sub_json["board"] = board
            res_sub_json["board_details"] = vanillaManager.get_leaderboard_analytics(
                board,
                limit,
                start_time,
                end_time,
            )
            res_json.append(res_sub_json)
            output_message += (
                f"The board <{board.capitalize()}> analytics fetched successfully.\n "
            )
        status = EXECUTION_STATE_COMPLETED
        output_message += (
            "All the requested leaderboards analytics were successfully fetched.\n"
        )
        result_value = True

    except Exception as e:
        siemplify.LOGGER.error(e)
        output_message += (
            f"Could not fetch the <{leaderboards}> leaderbooard analytics. "
        )
        output_message += "Error: " + str(e)

    finally:
        siemplify.LOGGER.info(
            f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
        )

        siemplify.result.add_result_json(res_json)
        siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
