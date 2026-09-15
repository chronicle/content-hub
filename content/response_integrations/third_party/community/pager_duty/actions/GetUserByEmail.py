from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import INTEGRATION_NAME, SCRIPT_NAME_USEREMAIL
from ..core.PagerDutyManager import PagerDutyManager


def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = INTEGRATION_NAME + SCRIPT_NAME_USEREMAIL
    configurations = siemplify.get_configuration(INTEGRATION_NAME)

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    api_token = configurations["api_key"]
    user_email = siemplify.parameters["Email"]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    pager_duty = PagerDutyManager(api_token)

    try:
        siemplify.LOGGER.info("Starting to get the user information")
        user = pager_duty.get_user_by_email(user_email)
        user_name = user["name"]
        siemplify.result.add_result_json(user)
        output_message = f"Successfully retrieved user {user_name} with the email {user_email}\n"
        result_value = True
        status = EXECUTION_STATE_COMPLETED

    except Exception:
        output_message = "There is no user with this Email."
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
