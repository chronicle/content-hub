from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.VanillaManager import VanillaManager

# Consts:
INTEGRATION_NAME = "VanillaForums"
SCRIPT_NAME = "Get User Details"


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
    user_id = siemplify.extract_action_param(param_name="User ID").strip()

    # Init result json:
    response_json = {}
    # Init result values:
    status = EXECUTION_STATE_FAILED
    output_message = f"The user details of <userID: {user_id}> could not be fetched, or there is no such user."
    result_value = False

    # Creating manager instance for methods:
    vanillaManager = VanillaManager(apiToken, baseUrl)

    try:
        response_json = vanillaManager.get_user_details(user_id)
        status = EXECUTION_STATE_COMPLETED
        output_message = f"The user details of <userID: {user_id}> succesfully fetched."
        result_value = True

    except Exception as e:
        siemplify.LOGGER.error(e)
        output_message += " Error: " + str(e)

    finally:
        siemplify.LOGGER.info(
            f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
        )
        siemplify.result.add_result_json(response_json)
        siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
