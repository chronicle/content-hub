from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param

from ..core.APIManager import APIManager
from ..core.constants import (
    ALLOWED_INSIGHT_STATUS_VALUES,
    COMMON_ACTION_ERROR_MESSAGE,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    UPDATE_STATUS_OF_INSIGHT_SCRIPT_NAME,
)
from ..core.InfobloxExceptions import InfobloxException
from ..core.utils import get_integration_params, validate_enum, validate_required_string


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_STATUS_OF_INSIGHT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    insight_id = extract_action_param(siemplify, param_name="Insight ID", input_type=str, is_mandatory=True)
    insight_status = extract_action_param(siemplify, param_name="Status", input_type=str, is_mandatory=True)
    comment = extract_action_param(siemplify, param_name="Comment", input_type=str, is_mandatory=False)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""

    try:
        validate_required_string(insight_id, "Insight ID")
        validate_enum(insight_status, ALLOWED_INSIGHT_STATUS_VALUES, "Status")

        infoblox_manager = APIManager(api_root, api_key, verify_ssl, siemplify)
        response = infoblox_manager.update_infoblox_iq_for_threat_defense_status(
            insight_id=insight_id, status=insight_status, comment=comment
        )

        siemplify.result.add_result_json(json.dumps(response, indent=4))
        output_message = f"Successfully updated status of Insight ID '{insight_id}' to '{insight_status}'."

    except (InfobloxException, ValueError) as e:
        status = EXECUTION_STATE_FAILED
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(UPDATE_STATUS_OF_INSIGHT_SCRIPT_NAME, e)
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
