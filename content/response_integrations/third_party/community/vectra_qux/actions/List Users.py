from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import construct_csv, extract_action_param, extract_configuration_param

from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    INTEGRATION_NAME,
    LIST_USERS_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.UtilsManager import validate_integer, validate_limit_param
from ..core.VectraQUXExceptions import InvalidIntegerException, VectraQUXException
from ..core.VectraQUXManager import VectraQUXManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_USERS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        input_type=str,
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        input_type=str,
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    # Action parameters
    role = extract_action_param(
        siemplify,
        param_name="Role",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    username = extract_action_param(
        siemplify,
        param_name="User Name",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    account_type = extract_action_param(
        siemplify,
        param_name="Account Type",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    authentication_profile = extract_action_param(
        siemplify,
        param_name="Authentication Profile",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    last_login_gte = extract_action_param(
        siemplify,
        param_name="Last Login GTE",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    result_limit = extract_action_param(
        siemplify,
        param_name="Limit",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    result_value = RESULT_VALUE_TRUE
    status = EXECUTION_STATE_COMPLETED
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        result_limit = validate_limit_param(result_limit)
        result_limit = validate_integer(
            result_limit,
            zero_allowed=True,
            field_name="Limit",
        )
        vectra_manager = VectraQUXManager(
            api_root,
            api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        user_objects, users = vectra_manager.get_user_list(
            result_limit,
            role=role,
            username=username,
            account_type=account_type,
            authentication_profile=authentication_profile,
            last_login_gte=last_login_gte,
        )

        if not users:
            output_message = "No users were found with the provided parameters."
        else:
            output_message = f"Successfully retrieved the {len(users)} users."

            siemplify.result.add_data_table(
                title="List Of Users",
                data_table=construct_csv(
                    [user_obj.fetch_user_details() for user_obj in user_objects],
                ),
            )

        siemplify.result.add_result_json(json.dumps(users, indent=4))

    except InvalidIntegerException as error:
        output_message = str(error)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
    except VectraQUXException as error:
        output_message = str(error)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(
            f"{error}, while performing action {LIST_USERS_SCRIPT_NAME}",
        )
        siemplify.LOGGER.exception(error)
    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(LIST_USERS_SCRIPT_NAME, e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"is_success: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
