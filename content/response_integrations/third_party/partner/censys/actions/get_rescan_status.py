from __future__ import annotations

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import APIManager
from ..core.censys_exceptions import CensysException
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    GET_RESCAN_STATUS_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.utils import get_integration_params


@output_handler
def main():
    """Get the current status of a scan by its ID asynchronously.

    This action retrieves the current status of a scan by its ID. It allows users to monitor
    the progress of previously initiated scans and determine when scan results are available.
    The action supports async execution and will return IN_PROGRESS status if the scan is
    still running.

    Action Parameters:
        Scan ID (str, required): The unique identifier of the tracked scan

    Returns:
        None. Results are returned via siemplify.end() with:
            - output_message (str): Status message describing the scan status
            - result_value (bool): True if successful, False otherwise
            - status (str): Execution state (COMPLETED, INPROGRESS, or FAILED)

    Raises:
        CensysException: If API calls to Censys fail
        Exception: For any other unexpected errors during execution
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_RESCAN_STATUS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_key, organization_id, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    scan_id = siemplify.extract_action_param(
        param_name="Scan ID", input_type=str, is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""

    try:
        # Validate Scan ID
        if not scan_id or not scan_id.strip():
            raise ValueError("Scan ID must be a non-empty string.")

        scan_id = scan_id.strip()

        # Initialize API Manager
        censys_manager = APIManager(
            api_key,
            organization_id,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        siemplify.LOGGER.info(f"Retrieving scan status for Scan ID: {scan_id}")
        response = censys_manager.get_rescan_status(scan_id)

        # Add JSON result
        siemplify.result.add_result_json(response)

        # Extract scan information
        result = response.get("result", {})
        tracked_scan_id = result.get("tracked_scan_id")

        if "completed" not in result:
            # Scan is still in progress
            status = EXECUTION_STATE_INPROGRESS
            output_message = f"Scan is still in progress. Scan ID: {tracked_scan_id}"
            siemplify.LOGGER.info(output_message)
        else:
            if result.get("completed"):
                # Scan is complete
                status = EXECUTION_STATE_COMPLETED
                output_message = f"Scan completed successfully. Scan ID: {tracked_scan_id}"
                siemplify.LOGGER.info(output_message)

            else:
                # Scan is failed
                status = EXECUTION_STATE_FAILED
                output_message = f"Scan failed. Scan ID: {tracked_scan_id}"
                siemplify.LOGGER.info(output_message)

    except ValueError as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except (CensysException, Exception) as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(GET_RESCAN_STATUS_SCRIPT_NAME, str(e))
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
