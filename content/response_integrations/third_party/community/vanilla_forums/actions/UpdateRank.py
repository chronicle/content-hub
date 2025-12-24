from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.VanillaManager import VanillaManager

# Consts:
INTEGRATION_NAME = "VanillaForums"
SCRIPT_NAME = "Update Rank"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # API Token ACTION parameter is rebundant.
    conf = siemplify.get_configuration(INTEGRATION_NAME)
    apiToken = conf.get("API Token")
    baseUrl = conf.get("URL")

    # INIT ACTION PARAMETERS:
    user_rank_id = siemplify.extract_action_param(param_name="Rank ID").strip()
    user_id = siemplify.extract_action_param(param_name="User ID").strip()

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    # Init result json:
    result_json_obj = {}
    # Init result values:
    status = EXECUTION_STATE_FAILED
    output_message = f"The Rank of the user <userID: {user_id}> was not changed."
    result_value = False

    vanillaManager = VanillaManager(apiToken, baseUrl)

    try:
        result_json_obj = vanillaManager.change_user_rank(user_rank_id, user_id)
        # succesfully updated rank -> update result values:
        status = EXECUTION_STATE_COMPLETED
        output_message = f"The Rank of the user <userID: {user_id}> was changed succesfully to <rankID: {user_rank_id}>"
        result_value = True

    except Exception as e:
        siemplify.LOGGER.error(e)
        output_message += " Error: " + str(e)

    finally:
        siemplify.LOGGER.info("----------------- Main - Finished -----------------")
        siemplify.LOGGER.info(
            f"\n  result_value: {result_value}\n  output_message: {output_message}",
        )
        siemplify.result.add_result_json(result_json_obj)
        siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
