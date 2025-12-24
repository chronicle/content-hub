from __future__ import annotations

import re

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.VanillaManager import VanillaManager

# Consts:
INTEGRATION_NAME = "VanillaForums"
SCRIPT_NAME = "Add User"


def check_pass_valid(password):
    return (
        re.search("[a-zA-Z]", password) is not None
        and re.search("[0-9]", password) is not None
        and len(password) >= 6
    )


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
    new_firstName = siemplify.extract_action_param(param_name="First Name").strip()
    new_lastName = siemplify.extract_action_param(param_name="Last Name").strip()
    new_email = siemplify.extract_action_param(param_name="Email").lower().strip()
    new_role_id = siemplify.extract_action_param(param_name="Role ID").strip()
    same_names_allowed = siemplify.extract_action_param(
        param_name="Override Name Duplicity",
        input_type=bool,
    )  # true -> True , false -> False
    special_chars = siemplify.extract_action_param(
        param_name="Additional Identifiers",
    ).strip()  # (default value is ' ')
    photo_url = siemplify.extract_action_param(param_name="Photo URL")
    email_confirmed = siemplify.extract_action_param(
        param_name="Email Confirmed",
    ).lower()
    password = siemplify.extract_action_param(
        param_name="Password",
        input_type=str,
    ).strip()

    special_chars_list = special_chars.split(",")
    print(special_chars_list)
    # Init result json:
    result_json_obj = {}
    # Init result values:
    status = EXECUTION_STATE_FAILED
    output_message = f"The user <{new_email}> was not added to Vanilla."
    result_value = False

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        if not check_pass_valid(password):
            raise Exception(
                "Password parameter is not by needed standard. Please make sure it includes letters and digits and is at least 6 characters long.",
            )

        # Create manager instance for method:
        vanillaManager = VanillaManager(apiToken, baseUrl)

        # Search for username in system:
        search_regular_res_json = vanillaManager.search_user_by_name(
            new_firstName + " " + new_lastName,
        )
        special_char = ""
        if len(search_regular_res_json) > 0:  # Found with space
            for char in special_chars_list:
                print(char)
                search_special_chars_json = vanillaManager.search_user_by_name(
                    new_firstName + char + new_lastName,
                )
                if len(search_special_chars_json) == 0:  # Not found with current char
                    print("found")
                    special_char = char  # good identifier
                    break
            if special_char == "":  # All given chars are already in use
                raise Exception(
                    "Username with all given characters is already in Vanilla.",
                )

        # Char needed only if allowed and name exists:
        char_needed = (
            True if same_names_allowed and len(search_regular_res_json) > 0 else False
        )

        # Add user to Vanilla users:
        res_json = vanillaManager.add_new_user(
            new_email,
            new_firstName,
            new_lastName,
            password,
            new_role_id,
            char_needed,
            special_char,
            photo_url,
            email_confirmed,
        )
        # Success adding user:
        result_json_obj["user_details"] = res_json
        result_json_obj["Email"] = res_json.get("email")
        result_json_obj["Password"] = res_json.get("password")

        status = EXECUTION_STATE_COMPLETED
        output_message = (
            "User <"
            + new_email
            + "> was succesfully registered as a member in Vanilla."
        )
        result_value = True

    except Exception as e:
        siemplify.LOGGER.error(e)
        output_message += " Error: " + str(e)

    finally:
        siemplify.LOGGER.info("----------------- Main - Finished -----------------")
        siemplify.result.add_result_json(result_json_obj)
        siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
