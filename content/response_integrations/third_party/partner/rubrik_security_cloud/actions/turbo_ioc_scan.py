from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    TURBO_IOC_SCAN_SCRIPT_NAME,
)
from ..core.datamodels import TurboIOCScanDatamodel
from ..core.rubrik_exceptions import RubrikException
from ..core.utils import (
    generate_scan_name,
    get_integration_params,
    is_valid_date,
    string_to_list,
    validate_integer_param,
)


@output_handler
def main():
    """Execute Turbo IOC Scan action for Rubrik Security Cloud.

    This action initiates a Turbo IOC (Indicator of Compromise) scan across Rubrik
    infrastructure. Turbo scans are optimized for speed and can scan multiple IOCs
    across clusters with configurable time ranges and snapshot limits.

    Action Parameters:
        IOC (str, required): Comma-separated list of IOCs to scan for
        Scan Name (str, optional): Custom name for the scan (auto-generated if not provided)
        Cluster ID (str, optional): Comma-separated list of cluster IDs to scan
        Start Time (str, optional): Start time for snapshot range (ISO format)
        End Time (str, optional): End time for snapshot range (ISO format)
        Max Snapshots Per Object (str, optional): Maximum snapshots to scan per object

    Returns:
        None. Results are returned via siemplify.end() with:
            - output_message (str): Status message describing the scan results
            - result_value (str): "true" if successful, "false" otherwise
            - status (str): Execution state (COMPLETED or FAILED)

    Raises:
        ValueError: If parameter validation fails (e.g., invalid dates, start time after end time)
        RubrikException: If API calls to Rubrik Security Cloud fail
        Exception: For any other unexpected errors during execution
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = TURBO_IOC_SCAN_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    service_account_json, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    ioc = siemplify.extract_action_param(param_name="IOC", input_type=str, is_mandatory=True)

    scan_name = siemplify.extract_action_param(
        param_name="Scan Name", input_type=str, is_mandatory=False
    )
    cluster_id = siemplify.extract_action_param(
        param_name="Cluster ID", input_type=str, is_mandatory=False, default_value=None
    )
    start_time = siemplify.extract_action_param(
        param_name="Start Time", input_type=str, is_mandatory=False, default_value=None
    )
    end_time = siemplify.extract_action_param(
        param_name="End Time", input_type=str, is_mandatory=False, default_value=None
    )
    max_snapshots_per_object = siemplify.extract_action_param(
        param_name="Max Snapshots Per Object",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = RESULT_VALUE_TRUE

    try:
        ioc_list = string_to_list(ioc, param_name="IOC", is_mandatory=True)
        scan_name = generate_scan_name(scan_name)
        cluster_ids = string_to_list(cluster_id)
        max_snapshots_per_object = validate_integer_param(
            max_snapshots_per_object,
            "Max Snapshots Per Object",
            zero_allowed=False,
            allow_negative=False,
        )

        start_time = is_valid_date(start_time)
        end_time = is_valid_date(end_time)

        if start_time and end_time and (start_time > end_time):
            raise ValueError("Start Time must be before End Time")

        siemplify.LOGGER.info("Initializing Rubrik Security Cloud client")
        rubrik_manager = APIManager(
            service_account_json,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        siemplify.LOGGER.info("Starting Turbo IOC Scan")
        response = rubrik_manager.start_turbo_ioc_scan(
            ioc_list=ioc_list,
            scan_name=scan_name,
            cluster_ids=cluster_ids,
            start_time=start_time,
            end_time=end_time,
            max_snapshots_per_object=max_snapshots_per_object,
        )

        siemplify.result.add_result_json(json.dumps(response, indent=4))
        hunt_id = response.get("data", {}).get("startTurboThreatHunt", {}).get("huntId")

        turbo_scan = TurboIOCScanDatamodel(hunt_id)

        output_message = f"Successfully started Turbo IOC Scan with hunt ID: {hunt_id}"

        table_data = turbo_scan.to_csv()
        if table_data:
            siemplify.result.add_data_table(
                "Turbo IOC Scan Results", construct_csv(table_data), "RSC"
            )

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
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(TURBO_IOC_SCAN_SCRIPT_NAME, str(e))
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
