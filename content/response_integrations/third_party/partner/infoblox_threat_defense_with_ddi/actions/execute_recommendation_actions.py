from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler
from TIPCommon.extraction import extract_action_param

from ..core.APIManager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    EXECUTE_RECOMMENDATION_ACTIONS_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import RecommendationActionResult
from ..core.InfobloxExceptions import InfobloxException
from ..core.utils import get_integration_params, validate_required_string


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = EXECUTE_RECOMMENDATION_ACTIONS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    insight_id = extract_action_param(siemplify, param_name="Insight ID", input_type=str, is_mandatory=True)
    recommendation_id = extract_action_param(
        siemplify, param_name="Recommendation Id", input_type=str, is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""

    try:
        validate_required_string(insight_id, "Insight ID")
        validate_required_string(recommendation_id, "Recommendation Id")

        infoblox_manager = APIManager(api_root, api_key, verify_ssl, siemplify)
        response = infoblox_manager.execute_recommendation_actions(
            insight_id=insight_id,
            items={"items": [{"recommendation_id": recommendation_id}]},
        )

        siemplify.result.add_result_json(json.dumps(response, indent=4))

        results = response.get("results", [])
        if results:
            table = [RecommendationActionResult(item).to_csv() for item in results]
            siemplify.result.add_data_table("Recommendation Action Results", construct_csv(table))

        failed_items = [item for item in results if item.get("status") == "failed"]
        if failed_items:
            status = EXECUTION_STATE_FAILED
            result_value = RESULT_VALUE_FALSE
            output_message = "; ".join(item.get("message", "Unknown error") for item in failed_items)
        else:
            output_message = (
                f"Successfully executed Recommendation Id '{recommendation_id}' for Insight ID '{insight_id}'."
            )

    except (InfobloxException, ValueError) as e:
        status = EXECUTION_STATE_FAILED
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(EXECUTE_RECOMMENDATION_ACTIONS_SCRIPT_NAME, e)
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
