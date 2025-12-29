from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import INTEGRATION_NAME, SCRIPT_NAME_USEREID
from ..core.PagerDutyManager import PagerDutyManager


def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = INTEGRATION_NAME + SCRIPT_NAME_USEREID
    configurations = siemplify.get_configuration(INTEGRATION_NAME)
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    userID = siemplify.parameters["UserID"]
    api_token = configurations["api_key"]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    error_meesage = "There is no user with this ID"
    pager_duty = PagerDutyManager(api_token)

    try:
        siemplify.LOGGER.info("Starting to get the user information")
        user = pager_duty.get_user_by_ID(userID)
        result_value = True
        output_message = f"Successfully retrieved user {user['email']}"

        status = EXECUTION_STATE_COMPLETED

    except Exception:
        user = {"message": f"{error_meesage}"}
        output_message = error_meesage
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.result.add_result_json(user)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
