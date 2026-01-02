from __future__ import annotations
import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, construct_csv
from TIPCommon import extract_action_param
from ..core.datamodels import SOCInsightEvent
from ..core.APIManager import APIManager
from ..core.InfobloxExceptions import InfobloxException
from ..core.constants import (
    GET_SOC_INSIGHTS_EVENTS_SCRIPT_NAME,
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
    siemplify.script_name = GET_SOC_INSIGHTS_EVENTS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root, api_key, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    insight_id = extract_action_param(
        siemplify, param_name="Insight ID", input_type=str, is_mandatory=True
    )
    device_ip = extract_action_param(
        siemplify, param_name="Device IP", input_type=str, is_mandatory=False
    )
    query = extract_action_param(siemplify, param_name="Query", input_type=str, is_mandatory=False)
    query_type = extract_action_param(
        siemplify, param_name="Query Type", input_type=str, is_mandatory=False
    )
    source = extract_action_param(
        siemplify, param_name="Source", input_type=str, is_mandatory=False
    )
    indicator = extract_action_param(
        siemplify, param_name="Indicator", input_type=str, is_mandatory=False
    )
    threat_level = extract_action_param(
        siemplify, param_name="Threat Level", input_type=str, is_mandatory=False
    )
    confidence_level = extract_action_param(
        siemplify, param_name="Confidence Level", input_type=str, is_mandatory=False
    )
    limit = extract_action_param(
        siemplify,
        param_name="Limit",
        input_type=str,
        is_mandatory=False,
        default_value=DEFAULT_LIMIT,
    )
    from_time = extract_action_param(
        siemplify, param_name="From", input_type=str, is_mandatory=False
    )
    to_time = extract_action_param(siemplify, param_name="To", input_type=str, is_mandatory=False)

    output_message = ""
    result_value = RESULT_VALUE_TRUE
    status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        validate_required_string(insight_id, "Insight ID")
        limit = validate_integer_param(limit, "Limit", zero_allowed=False, allow_negative=False)

        api_manager = APIManager(api_root, api_key, verify_ssl=verify_ssl, siemplify=siemplify)
        response = api_manager.get_soc_insights_events(
            insight_id=insight_id,
            device_ip=device_ip,
            query=query,
            query_type=query_type,
            source=source,
            indicator=indicator,
            threat_level=threat_level,
            confidence_level=confidence_level,
            limit=limit,
            from_time=from_time,
            to_time=to_time,
        )
        events = response.get("events", [])
        if not events:
            output_message = f"No events found for Insight ID '{insight_id}'."
        else:
            table = [SOCInsightEvent(item).to_csv() for item in events[:MAX_TABLE_RECORDS]]
            siemplify.result.add_data_table("SOC Insight Events", construct_csv(table))
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
