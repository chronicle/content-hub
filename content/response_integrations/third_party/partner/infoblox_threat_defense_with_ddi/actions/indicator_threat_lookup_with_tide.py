from __future__ import annotations
import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, construct_csv
from TIPCommon import extract_action_param
from ..core.APIManager import APIManager
from ..core.InfobloxExceptions import InfobloxException
from ..core.constants import (
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    COMMON_ACTION_ERROR_MESSAGE,
    INDICATOR_THREAT_LOOKUP_WITH_TIDE_SCRIPT_NAME,
    MAX_TABLE_RECORDS,
    TIDE_RLIMIT,
)
from ..core.datamodels import IndicatorThreatLookupTideResult
from ..core.utils import get_integration_params, validate_integer_param


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = INDICATOR_THREAT_LOOKUP_WITH_TIDE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # --- Parameter Extraction (outside try/except) ---
    api_root, api_key, verify_ssl = get_integration_params(siemplify)
    indicator_type = extract_action_param(
        siemplify,
        param_name="Indicator Type",
        input_type=str,
        is_mandatory=False,
        default_value="All",
        print_value=True,
    )
    indicator_value = extract_action_param(
        siemplify,
        param_name="Indicator Value",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    domain = extract_action_param(
        siemplify,
        param_name="Domain",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    tld = extract_action_param(
        siemplify,
        param_name="Top-Level Domain",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    threat_class = extract_action_param(
        siemplify,
        param_name="Threat Class",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    target = extract_action_param(
        siemplify,
        param_name="Target",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    expiration = extract_action_param(
        siemplify,
        param_name="Expiration",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    limit = extract_action_param(
        siemplify, param_name="Limit", input_type=str, is_mandatory=False, default_value=TIDE_RLIMIT
    )

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        # --- API Manager ---
        limit = validate_integer_param(limit, "Limit", zero_allowed=False, allow_negative=False)
        api_manager = APIManager(api_root, api_key, verify_ssl, siemplify)
        response = api_manager.indicator_threat_lookup_with_tide(
            indicator_type=indicator_type,
            indicator_value=indicator_value,
            domain=domain,
            tld=tld,
            threat_class=threat_class,
            target=target,
            expiration=expiration,
            rlimit=limit,
        )

        # --- Output Formatting ---
        threats = response.get("threat", [])
        table_results = []
        if threats and isinstance(threats, list):
            for item in threats[:MAX_TABLE_RECORDS]:
                model = IndicatorThreatLookupTideResult(item)
                table_results.append(model.to_csv())
            output_message = (
                f"Successfully retrieved {len(threats)} TIDE threat records. "
                f"Showing up to {MAX_TABLE_RECORDS} in table."
            )
        else:
            output_message = "No TIDE threat data found."

        siemplify.result.add_result_json(json.dumps(response))
        if table_results:
            siemplify.result.add_data_table(
                title="TIDE Indicator Threat Lookup Results",
                data_table=construct_csv(table_results),
            )

    except InfobloxException as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            INDICATOR_THREAT_LOOKUP_WITH_TIDE_SCRIPT_NAME, e
        )
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"result_value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
