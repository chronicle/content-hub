from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.VanillaManager import VanillaManager

# Consts:
INTEGRATION_NAME = "VanillaForums"
SCRIPT_NAME = "Update Badge"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION PARAMETERS:
    conf = siemplify.get_configuration(INTEGRATION_NAME)
    apiToken = conf.get("API Token")
    baseUrl = conf.get("URL")

    # INIT ACTION PARAMETERS:
    user_id = siemplify.extract_action_param(param_name="User ID").strip()
    badge_id = siemplify.extract_action_param(param_name="Badge ID").strip()

    # Init result json:
    given_badge_details = {}
    # Init result values:
    status = EXECUTION_STATE_FAILED
    output_message = (
        f"The badge <rankID: {badge_id}> wasn't given to the user <userID: {user_id}. "
    )
    result_value = False

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        # CREATE MANAGER INSTANCE (FOR METHODS):
        vanilla_manager = VanillaManager(apiToken, baseUrl)

        # GIVE USER WANTED BADGE:
        given_badge_details = vanilla_manager.give_user_badge(badge_id, user_id)
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f"The badge <badgeID: {badge_id}> was given to the user <userID: {user_id}>"
        )
        result_value = True

    except Exception as e:
        siemplify.LOGGER.error(e)
        output_message += "Error" + str(e)

    finally:
        siemplify.LOGGER.info("----------------- Main - Finished -----------------")
        siemplify.LOGGER.info(output_message)
        siemplify.result.add_result_json(given_badge_details)
        siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
