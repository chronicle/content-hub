from __future__ import annotations

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    DELETE_RESPONSE_POLICY_ZONE_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.infoblox_exceptions import InfobloxException, ItemNotFoundException
from ..core.utils import get_integration_params, validate_required_string


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DELETE_RESPONSE_POLICY_ZONE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, username, password, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    reference_id = extract_action_param(
        siemplify,
        param_name="Reference ID",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        validate_required_string(reference_id, "Reference ID")
        api_manager = APIManager(
            api_root, username, password, verify_ssl=verify_ssl, siemplify=siemplify
        )
        _ = api_manager.delete_response_policy_zone(reference_id)
        output_message = (
            f"Successfully deleted the Response Policy Zone with reference ID `{reference_id}`."
        )

    except ItemNotFoundException as e:
        output_message = str(e).format(reference_id=reference_id)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except (InfobloxException, ValueError) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            DELETE_RESPONSE_POLICY_ZONE_SCRIPT_NAME, str(e)
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
