from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.VanillaManager import VanillaManager

# Consts:
INTEGRATION_NAME = "VanillaForums"
SCRIPT_NAME = "Update User Role"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION PARAMETERS:
    conf = siemplify.get_configuration(INTEGRATION_NAME)
    apiToken = conf.get("API Token")
    baseURL = conf.get("URL")

    # INIT ACTION PARAMETERS:
    userID = siemplify.extract_action_param(param_name="UserID").strip()
    roleID = siemplify.extract_action_param(param_name="RoleID").strip()

    # Init result json:
    res_json = {}
    # Init resut values:
    status = EXECUTION_STATE_FAILED
    output_message = f"The user <{userID}> role was not updated. "
    result_value = False

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    # Create VanillaManager instance for methods:
    vanillaManager = VanillaManager(apiToken, baseURL)

    try:
        # Update user's role:
        res_json = vanillaManager.give_user_role(roleID, userID)
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f"The user <{userID}> role was updated to <{roleID}> successfully"
        )
        result_value = True

    except Exception as e:
        siemplify.LOGGER.error(e)
        output_message += "Error: " + str(e)

    finally:
        siemplify.LOGGER.info("----------------- Main - Finished -----------------")
        siemplify.LOGGER.info(
            f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
        )
        siemplify.result.add_result_json(res_json)
        siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
