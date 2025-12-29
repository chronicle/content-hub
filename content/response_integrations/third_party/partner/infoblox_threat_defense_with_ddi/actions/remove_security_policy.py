from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_action_param
from ..core.APIManager import APIManager
from ..core.InfobloxExceptions import InfobloxException
from ..core.constants import (
    REMOVE_SECURITY_POLICY_SCRIPT_NAME,
    RESULT_VALUE_TRUE,
    RESULT_VALUE_FALSE,
    COMMON_ACTION_ERROR_MESSAGE,
)
from ..core.utils import get_integration_params, validate_required_string, validate_integer_param


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = REMOVE_SECURITY_POLICY_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    security_policy_id = extract_action_param(
        siemplify, param_name="Security Policy ID", input_type=str, is_mandatory=True
    )

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        validate_required_string(security_policy_id, "Security Policy ID")
        security_policy_id = validate_integer_param(
            security_policy_id, "Security Policy ID", zero_allowed=False, allow_negative=False
        )
        api_manager = APIManager(api_root, api_key, verify_ssl=verify_ssl, siemplify=siemplify)
        api_manager.remove_security_policy(security_policy_id)
        output_message = f"Successfully removed security policy with ID '{security_policy_id}'."
    except (InfobloxException, ValueError) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            REMOVE_SECURITY_POLICY_SCRIPT_NAME, str(e)
        )
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"status: {status}")
    siemplify.LOGGER.info(f"result_value: {result_value}")
    siemplify.LOGGER.info(f"output_message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
