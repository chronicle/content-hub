from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler
from TIPCommon.extraction import extract_action_param

from ..core.APIManager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    UNDO_RECOMMENDATION_ACTION_SCRIPT_NAME,
)
from ..core.datamodels import RecommendationActionResult
from ..core.InfobloxExceptions import InfobloxException
from ..core.utils import get_integration_params, validate_required_string


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UNDO_RECOMMENDATION_ACTION_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    audit_entry_id = extract_action_param(siemplify, param_name="Audit Entry ID", input_type=str, is_mandatory=True)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""

    try:
        validate_required_string(audit_entry_id, "Audit Entry ID")

        infoblox_manager = APIManager(api_root, api_key, verify_ssl, siemplify)
        response = infoblox_manager.undo_recommendation_action(audit_entry_id=audit_entry_id)

        siemplify.result.add_result_json(json.dumps(response, indent=4))

        result = response.get("result", {})
        if result:
            undo_result = RecommendationActionResult(result)
            siemplify.result.add_data_table("Undo Recommendation Action Result", construct_csv([undo_result.to_csv()]))

        if result.get("status") == "failed":
            status = EXECUTION_STATE_FAILED
            result_value = RESULT_VALUE_FALSE
            output_message = result.get("message") or f"Failed to undo audit entry '{audit_entry_id}'."
        else:
            output_message = f"Successfully undone the action for Audit Entry ID '{audit_entry_id}'."

    except (InfobloxException, ValueError) as e:
        status = EXECUTION_STATE_FAILED
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(UNDO_RECOMMENDATION_ACTION_SCRIPT_NAME, e)
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
