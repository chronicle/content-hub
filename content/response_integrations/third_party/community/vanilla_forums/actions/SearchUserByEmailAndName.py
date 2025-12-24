from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.VanillaManager import VanillaManager

# Consts:
INTEGRATION_NAME = "VanillaForums"
SCRIPT_NAME = "Search User By Email and Name"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Extract integration params:
    conf = siemplify.get_configuration(INTEGRATION_NAME)
    apiToken = conf.get("API Token")
    baseUrl = conf.get("URL")

    # Extract action params:
    user_name = siemplify.extract_action_param("User Name").strip()
    user_email = siemplify.extract_action_param("User Email").lower().strip()

    # Init result json:
    res_json = {}
    json_res_by_email = {}
    json_res_by_name = {}
    # Init result values:
    status = EXECUTION_STATE_FAILED
    output_message = f"Could not find a user with both Email address: <{user_email}> and username: <{user_name}>. "
    result_value = False

    siemplify.LOGGER.info("================= Main - Started ====================")
    # Creating manager instance for methods:
    vanillaManager = VanillaManager(apiToken, baseUrl)

    try:
        emailFound = False
        # search by email:
        json_res_by_email = vanillaManager.search_user_by_email(user_email)
        res_json["Email"] = True if len(json_res_by_email) > 0 else False

        if res_json.get("Email"):
            output_message = f"Email address <{user_email}> was found in the system. \n"
            emailFound = True

        # search by name:
        json_res_by_name = vanillaManager.search_user_by_name(user_name)
        res_json["UserName"] = True if len(json_res_by_name) > 0 else False
        if res_json.get("UserName"):
            output_message += f"User name <{user_name}> was found in the system. "

        # update result values:
        result_value = emailFound or res_json.get("UserName")
        if not result_value:
            output_message = f"Email address <{user_email}> and username <{user_name}> were not found."

        res_json["UserDetails"] = json_res_by_email if emailFound else {}

        status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        siemplify.LOGGER.error(e)
        output_message += " Error: " + str(e)

    finally:
        siemplify.LOGGER.info(
            f"\n  result_value: {result_value}\n  output_message: {output_message}",
        )
        siemplify.result.add_result_json(res_json)
        siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
