from __future__ import annotations
import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, construct_csv
from TIPCommon import extract_action_param
from ..core.datamodels import SOCInsightIndicator
from ..core.APIManager import APIManager
from ..core.InfobloxExceptions import InfobloxException
from ..core.constants import (
    GET_SOC_INSIGHTS_INDICATORS_SCRIPT_NAME,
    RESULT_VALUE_TRUE,
    RESULT_VALUE_FALSE,
    COMMON_ACTION_ERROR_MESSAGE,
    MAX_TABLE_RECORDS,
    DEFAULT_LIMIT,
)
from ..core.utils import get_integration_params, validate_required_string, validate_integer_param


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_SOC_INSIGHTS_INDICATORS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    insight_id = extract_action_param(
        siemplify, param_name="Insight ID", input_type=str, is_mandatory=True
    )
    confidence = extract_action_param(
        siemplify, param_name="Confidence", input_type=str, is_mandatory=False
    )
    indicator = extract_action_param(
        siemplify, param_name="Indicator", input_type=str, is_mandatory=False
    )
    actor = extract_action_param(siemplify, param_name="Actor", input_type=str, is_mandatory=False)
    from_time = extract_action_param(
        siemplify, param_name="From", input_type=str, is_mandatory=False
    )
    to_time = extract_action_param(siemplify, param_name="To", input_type=str, is_mandatory=False)
    action_param = extract_action_param(
        siemplify, param_name="Action", input_type=str, is_mandatory=False
    )
    limit = extract_action_param(
        siemplify,
        param_name="Limit",
        input_type=str,
        is_mandatory=False,
        default_value=DEFAULT_LIMIT,
    )

    output_message = ""
    result_value = RESULT_VALUE_TRUE
    status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        validate_required_string(insight_id, "Insight ID")
        limit = validate_integer_param(limit, "Limit", zero_allowed=False, allow_negative=False)
        api_manager = APIManager(api_root, api_key, verify_ssl=verify_ssl, siemplify=siemplify)
        response = api_manager.get_soc_insights_indicators(
            insight_id=insight_id,
            confidence=confidence,
            indicator=indicator,
            actor=actor,
            action=action_param,
            from_time=from_time,
            to_time=to_time,
            limit=limit,
        )
        indicators = response.get("indicators", [])
        if not indicators:
            output_message = f"No indicators found for Insight ID '{insight_id}'."
        else:
            table = [SOCInsightIndicator(item).to_csv() for item in indicators[:MAX_TABLE_RECORDS]]
            siemplify.result.add_data_table("SOC Insight Indicators", construct_csv(table))
            output_message = (
                f"Successfully retrieved {len(indicators)} indicator(s) for Insight ID "
                f"'{insight_id}'. Showing up to {MAX_TABLE_RECORDS} in table."
            )
        siemplify.result.add_result_json(json.dumps(response, indent=4))
    except (InfobloxException, ValueError) as e:
        status = EXECUTION_STATE_FAILED
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            GET_SOC_INSIGHTS_INDICATORS_SCRIPT_NAME, e
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
