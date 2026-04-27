from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.F5BIGIPAccessPolicyManagerManager import F5BIGIPAccessPolicyManagerManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    LIST_ACTIVE_SESSIONS_ACTION,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_ACTIVE_SESSIONS_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="BIG-IP APM Address",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="User Name",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    token_timeout = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Token Timeout (in Seconds)",
        is_mandatory=False,
        input_type=int,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""

    try:
        limit = extract_action_param(
            siemplify,
            param_name="Limit",
            is_mandatory=False,
            print_value=True,
            default_value=0,
            input_type=str,
        )

        f5bigip_manager = F5BIGIPAccessPolicyManagerManager(
            api_root=api_root,
            username=username,
            password=password,
            token_timeout=token_timeout,
            verify_ssl=verify_ssl,
        )
        list_of_sessions = f5bigip_manager.list_active_sessions(limit=limit)

        if list_of_sessions:
            siemplify.result.add_result_json(
                [session.to_json() for session in list_of_sessions]
            )
            output_message += "Successfully listed active sessions."

        else:
            result_value = False
            output_message += f"No active sessions found in {INTEGRATION_DISPLAY_NAME}"

    except Exception as e:
        output_message += (
            f"Failed to perform action {LIST_ACTIVE_SESSIONS_ACTION}! Error is {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
