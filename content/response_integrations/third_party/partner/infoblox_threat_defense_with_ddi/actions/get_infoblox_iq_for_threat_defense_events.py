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
    GET_SOC_INSIGHTS_EVENTS_SCRIPT_NAME,
    MAX_TABLE_RECORDS,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import InfobloxIQForThreatDefenseEvent
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
    siemplify.script_name = GET_SOC_INSIGHTS_EVENTS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    insight_id = extract_action_param(siemplify, param_name="Insight ID", input_type=str, is_mandatory=True)
    device_ip = extract_action_param(siemplify, param_name="Device IP", input_type=str, is_mandatory=False)
    query = extract_action_param(siemplify, param_name="Query", input_type=str, is_mandatory=False)
    source = extract_action_param(siemplify, param_name="Source", input_type=str, is_mandatory=False)
    indicator = extract_action_param(siemplify, param_name="Indicator", input_type=str, is_mandatory=False)
    threat_level = extract_action_param(siemplify, param_name="Threat Level", input_type=str, is_mandatory=False)
    threat_confidence = extract_action_param(
        siemplify, param_name="Threat Confidence", input_type=str, is_mandatory=False
    )
    limit = extract_action_param(
        siemplify,
        param_name="Limit",
        input_type=str,
        is_mandatory=False,
        default_value=DEFAULT_LIMIT,
    )
    tclass = extract_action_param(siemplify, param_name="tClass", input_type=str, is_mandatory=False)
    detected_from = extract_action_param(siemplify, param_name="Detected From", input_type=str, is_mandatory=False)
    detected_to = extract_action_param(siemplify, param_name="Detected To", input_type=str, is_mandatory=False)
    device_name = extract_action_param(siemplify, param_name="Device Name", input_type=str, is_mandatory=False)
    user = extract_action_param(siemplify, param_name="User", input_type=str, is_mandatory=False)

    output_message = ""
    result_value = RESULT_VALUE_TRUE
    status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        validate_required_string(insight_id, "Insight ID")
        limit = validate_integer_param(limit, "Limit", zero_allowed=False, allow_negative=False)
        validate_datetimeformat(detected_from, "Detected From")
        validate_datetimeformat(detected_to, "Detected To")

        api_manager = APIManager(api_root, api_key, verify_ssl=verify_ssl, siemplify=siemplify)
        response = api_manager.get_infoblox_iq_for_threat_defense_events(
            insight_id=insight_id,
            device_ip=device_ip,
            query=query,
            source=source,
            indicator=indicator,
            threat_level=threat_level,
            threat_confidence=threat_confidence,
            limit=limit,
            tclass=tclass,
            detected_from=detected_from,
            detected_to=detected_to,
            device_name=device_name,
            user=user,
        )
        events = response.get("events", [])
        if not events:
            output_message = f"No events found for Insight ID '{insight_id}'."
        else:
            table = [InfobloxIQForThreatDefenseEvent(item).to_csv() for item in events[:MAX_TABLE_RECORDS]]
            siemplify.result.add_data_table("Infoblox IQ for Threat Defense Events", construct_csv(table))
            output_message = (
                f"Successfully retrieved {len(events)} event(s) for Insight ID '{insight_id}'. "
                f"Showing up to {MAX_TABLE_RECORDS} in table."
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
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(GET_SOC_INSIGHTS_EVENTS_SCRIPT_NAME, e)
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
