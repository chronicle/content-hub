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
from ..core.VectraRUXExceptions import InvalidIntegerException, VectraRUXException
from ..core.VectraRUXManager import VectraRUXManager


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
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        input_type=str,
        is_mandatory=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        print_value=False,
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
    last_login_gte = extract_action_param(
        siemplify,
        param_name="Last Login GTE",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    email = extract_action_param(
        siemplify,
        param_name="Email",
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
        result_limit = validate_integer(
            validate_limit_param(result_limit),
            zero_allowed=True,
            field_name="Limit",
        )
        vectra_manager = VectraRUXManager(
            api_root,
            client_id,
            client_secret,
            siemplify=siemplify,
        )

        user_objects, users = vectra_manager.get_user_list(
            result_limit,
            role=role,
            email=email,
            last_login_gte=last_login_gte,
        )

        if not users:
            output_message = "No users were found with the provided parameters."
        else:
            output_message = f"Successfully retrieved the {len(user_objects)} users."

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
    except VectraRUXException as error:
        output_message = str(error)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(
            f"{error}, while performing action {LIST_USERS_SCRIPT_NAME}",
        )
        siemplify.LOGGER.exception(error)
    except Exception as error:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            LIST_USERS_SCRIPT_NAME,
            error,
        )
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"is_success: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
