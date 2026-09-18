from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler
from TIPCommon.extraction import extract_action_param

from ..core.APIManager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    DEFAULT_LIMIT,
    GET_SOC_INSIGHTS_INDICATORS_SCRIPT_NAME,
    MAX_TABLE_RECORDS,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import InfobloxIQForThreatDefenseIndicator
from ..core.InfobloxExceptions import InfobloxException
from ..core.utils import (
    get_integration_params,
    validate_datetimeformat,
    validate_integer_param,
    validate_required_string,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_SOC_INSIGHTS_INDICATORS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    insight_id = extract_action_param(siemplify, param_name="Insight ID", input_type=str, is_mandatory=True)
    threat_level = extract_action_param(siemplify, param_name="Threat Level", input_type=str, is_mandatory=False)
    indicators = extract_action_param(siemplify, param_name="Threat Indicators", input_type=str, is_mandatory=False)
    status = extract_action_param(siemplify, param_name="Status", input_type=str, is_mandatory=False)
    users = extract_action_param(siemplify, param_name="Users", input_type=str, is_mandatory=False)
    detected_at = extract_action_param(siemplify, param_name="Detected At", input_type=str, is_mandatory=False)
    limit = extract_action_param(
        siemplify,
        param_name="Limit",
        input_type=str,
        is_mandatory=False,
        default_value=DEFAULT_LIMIT,
    )

    output_message = ""
    result_value = RESULT_VALUE_TRUE
    result_status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        validate_required_string(insight_id, "Insight ID")
        limit = validate_integer_param(limit, "Limit", zero_allowed=False, allow_negative=False)
        validate_datetimeformat(detected_at, "Detected At")
        api_manager = APIManager(api_root, api_key, verify_ssl=verify_ssl, siemplify=siemplify)
        response = api_manager.get_infoblox_iq_for_threat_defense_indicators(
            insight_id=insight_id,
            threat_level=threat_level,
            indicators=indicators,
            status=status,
            users=users,
            detected_at=detected_at,
            limit=limit,
        )
        indicators = response.get("indicators", [])
        if not indicators:
            output_message = f"No indicators found for Insight ID '{insight_id}'."
        else:
            table = [InfobloxIQForThreatDefenseIndicator(item).to_csv() for item in indicators[:MAX_TABLE_RECORDS]]
            siemplify.result.add_data_table("Infoblox IQ for Threat Defense Indicators", construct_csv(table))
            output_message = (
                f"Successfully retrieved {len(indicators)} indicator(s) for Insight ID "
                f"'{insight_id}'. Showing up to {MAX_TABLE_RECORDS} in table."
            )
        siemplify.result.add_result_json(json.dumps(response, indent=4))
    except (InfobloxException, ValueError) as e:
        result_status = EXECUTION_STATE_FAILED
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        result_status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(GET_SOC_INSIGHTS_INDICATORS_SCRIPT_NAME, e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"status: {result_status}")
    siemplify.LOGGER.info(f"result_value: {result_value}")
    siemplify.LOGGER.info(f"output_message: {output_message}")
    siemplify.end(output_message, result_value, result_status)


if __name__ == "__main__":
    main()
