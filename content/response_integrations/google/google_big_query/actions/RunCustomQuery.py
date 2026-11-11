from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv
from TIPCommon.validation import ParameterValidator
from google_big_query.core import GoogleBigQueryUtils
from google_big_query.core.GoogleBigQueryManager import GoogleBigQueryApiManager
from google_big_query.core.constants import INTEGRATION_DISPLAY_NAME, RUN_CUSTOM_QUERY_SCRIPT_NAME


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = (
        f"{INTEGRATION_DISPLAY_NAME} - {RUN_CUSTOM_QUERY_SCRIPT_NAME}"
    )

    siemplify.LOGGER.info("================= Main - Param Init =================")
    query = extract_action_param(
        siemplify, param_name="Query", is_mandatory=True, print_value=True
    )
    limit = extract_action_param(
        siemplify, param_name="Max Results To Return"
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    results = []
    status = EXECUTION_STATE_COMPLETED
    result_value = "true"
    conf_param_extractor = GoogleBigQueryUtils.ExtractConfigurationParameters(siemplify)
    try:
        if limit is not None:
            limit = ParameterValidator(siemplify).validate_positive(
                param_name="Max Results To Return",
                value=limit,
                print_value=True
            )

        manager = GoogleBigQueryApiManager.from_config_params(conf_param_extractor)
        results = manager.run_query(query, limit)
        siemplify.LOGGER.info(f"Found {len(results)} rows.")

        if results:
            siemplify.result.add_data_table("Results", construct_csv(results))

        output_message = (
            "Successfully executed query in the Google BigQuery!"
        )

    # pylint: disable=broad-exception-caught
    except Exception as e:
        error_msg = (
            f'Error executing action "{RUN_CUSTOM_QUERY_SCRIPT_NAME}". Reason: {e}'
        )
        siemplify.LOGGER.error(error_msg)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = error_msg

    siemplify.result.add_result_json(results)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
