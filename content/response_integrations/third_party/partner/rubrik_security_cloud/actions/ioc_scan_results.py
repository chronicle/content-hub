from __future__ import annotations

import json

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    IOC_SCAN_RESULTS_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import IOCScanResultsDatamodel
from ..core.rubrik_exceptions import RubrikException
from ..core.utils import get_integration_params, validate_required_string


@output_handler
def main():
    """Retrieve IOC Scan Results for a specific threat hunt from Rubrik Security Cloud.

    This action retrieves the results of an IOC (Indicator of Compromise) scan/threat hunt
    using the hunt ID. It returns detailed information about the scan status, matches found,
    and metrics. The action supports async execution and will return IN_PROGRESS status
    if the hunt is still running.

    Action Parameters:
        Hunt ID (str, required): The unique identifier of the threat hunt/IOC scan

    Returns:
        None. Results are returned via siemplify.end() with:
            - output_message (str): Status message describing the retrieval results
            - result_value (str): "true" if successful, "false" otherwise
            - status (str): Execution state (COMPLETED, INPROGRESS, or FAILED)

    Raises:
        ValueError: If the Hunt ID parameter is invalid or empty
        RubrikException: If API calls to Rubrik Security Cloud fail
        Exception: For any other unexpected errors during execution
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = IOC_SCAN_RESULTS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    service_account_json, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    hunt_id = siemplify.extract_action_param(
        param_name="Hunt ID", input_type=str, is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = RESULT_VALUE_TRUE

    try:
        hunt_id = validate_required_string(hunt_id, "Hunt ID")

        siemplify.LOGGER.info("Initializing Rubrik Security Cloud client")
        rubrik_manager = APIManager(
            service_account_json,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        siemplify.LOGGER.info(f"Retrieving IOC Scan Results for Hunt ID: {hunt_id}")
        response = rubrik_manager.get_ioc_scan_results(hunt_id)

        siemplify.result.add_result_json(json.dumps(response, indent=4))

        data = response.get("data", {})
        threat_hunt_detail = data.get("threatHuntDetailV2")
        threat_hunt_metrics = data.get("threatHuntObjectMetrics")

        if not threat_hunt_detail:
            siemplify.LOGGER.info(
                f"No threat hunt details found for the provided Hunt ID: {hunt_id}"
            )

        scan_results = IOCScanResultsDatamodel(threat_hunt_detail, threat_hunt_metrics)

        output_message = f"Successfully retrieved IOC Scan Results for Hunt ID: {hunt_id}"
        table_data = scan_results.to_csv()
        if table_data:
            siemplify.result.add_data_table("IOC Scan Results", construct_csv(table_data), "RSC")

        # Check if the hunt is still in progress
        if threat_hunt_detail.get("status", "SUCCEEDED") in ("PENDING", "IN_PROGRESS"):
            status = EXECUTION_STATE_INPROGRESS

    except (
        RubrikException,
        ValueError,
    ) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(IOC_SCAN_RESULTS_SCRIPT_NAME, str(e))
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
