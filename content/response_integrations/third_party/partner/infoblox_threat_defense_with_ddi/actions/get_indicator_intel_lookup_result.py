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
    GET_INDICATOR_INTEL_LOOKUP_RESULT_ACTION_IDENTIFIER,
    GET_INDICATOR_INTEL_LOOKUP_RESULT_SCRIPT_NAME,
    MAX_TABLE_RECORDS,
)
from ..core.datamodels import IndicatorIntelLookupResult
from ..core.utils import get_integration_params, validate_required_string


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_INDICATOR_INTEL_LOOKUP_RESULT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # --- Parameter Extraction (outside try/except) ---
    api_root, api_key, verify_ssl = get_integration_params(siemplify)
    job_id = extract_action_param(
        siemplify,
        param_name="Job ID",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        job_id = validate_required_string(job_id, "Job ID")

        # --- API Manager ---
        api_manager = APIManager(api_root, api_key, verify_ssl, siemplify)
        response = api_manager.get_indicator_intel_lookup_result(job_id)

        # --- Output Formatting ---
        results = response.get("results", [])
        table_results = []
        if results and isinstance(results, list):
            for item in results[:MAX_TABLE_RECORDS]:
                model = IndicatorIntelLookupResult(item)
                table_results.append(model.to_csv())
            output_message = (
                f"Successfully retrieved {len(results)} dossier results for Job ID {job_id}. "
                f"Showing up to {MAX_TABLE_RECORDS} in table."
            )
        else:
            output_message = f"No dossier results found for Job ID {job_id}."

        siemplify.result.add_result_json(json.dumps(response))
        if table_results:
            siemplify.result.add_data_table(
                title="Dossier Lookup Results", data_table=construct_csv(table_results)
            )

    except (InfobloxException, ValueError) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            GET_INDICATOR_INTEL_LOOKUP_RESULT_ACTION_IDENTIFIER, e
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
