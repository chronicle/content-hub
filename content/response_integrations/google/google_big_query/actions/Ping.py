from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from google_big_query.core import GoogleBigQueryUtils
from google_big_query.core.GoogleBigQueryManager import GoogleBigQueryApiManager
from google_big_query.core.constants import INTEGRATION_DISPLAY_NAME, PING_SCRIPT_NAME


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_DISPLAY_NAME} - {PING_SCRIPT_NAME}"
    conf_param_extractor = GoogleBigQueryUtils.ExtractConfigurationParameters(siemplify)
    try:
        siemplify.LOGGER.info("================= Main - Param Init =================")
        manager = GoogleBigQueryApiManager.from_config_params(conf_param_extractor)

        siemplify.LOGGER.info("----------------- Main - Started -----------------")
        manager.test_connectivity()

        status = EXECUTION_STATE_COMPLETED
        output_message = (
            "Successfully connected to the Google BigQuery server "
            "with the provided connection parameters!"
        )
        result_value = "true"

    except Exception as e:
        siemplify.LOGGER.error(
            f"Failed to connect to the Google BigQuery server! Error is {e}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = (
            f"Failed to connect to the Google BigQuery server! Error is {e}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
