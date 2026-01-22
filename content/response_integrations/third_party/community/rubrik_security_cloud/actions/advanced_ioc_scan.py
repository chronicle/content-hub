from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    ADVANCE_IOC_SCAN_SCRIPT_NAME,
    COMMON_ACTION_ERROR_MESSAGE,
    MAX_TABLE_RECORDS,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import AdvanceIOCScanDatamodel
from ..core.rubrik_exceptions import RubrikException
from ..core.utils import (
    generate_scan_name,
    get_integration_params,
    is_valid_date,
    string_to_list,
    validate_integer_param,
    validate_json,
)


@output_handler
def main():
    """Execute Advanced IOC Scan action for Rubrik Security Cloud.

    This action initiates an advanced Indicator of Compromise (IOC) scan on specified
    Rubrik objects. It supports various scan configurations including IOC types, date ranges,
    file size filters, and path inclusions/exclusions.

    Action Parameters:
        Object ID (str, required): Comma-separated list of object IDs to scan
        IOC Type (str, optional): Type of IOC to search for
        IOC Value (str, optional): Specific IOC value to search for
        Scan Name (str, optional): Custom name for the scan (auto-generated if not provided)
        Advanced IOC (str, optional): JSON string with advanced IOC configuration
        Start Date (str, optional): Start date for snapshot range (ISO format)
        End Date (str, optional): End date for snapshot range (ISO format)
        Max Snapshots Per Object (str, optional): Maximum snapshots to scan per object
        Max Matches Per Snapshot (str, optional): Maximum matches to return per snapshot
        Min File Size (str, optional): Minimum file size to scan (bytes)
        Max File Size (str, optional): Maximum file size to scan (bytes)
        Paths To Include (str, optional): Comma-separated paths to include in scan
        Paths To Exclude (str, optional): Comma-separated paths to exclude from scan
        Paths To Exempt (str, optional): Comma-separated paths to exempt from scan

    Returns:
        None. Results are returned via siemplify.end() with:
            - output_message (str): Status message describing the scan results
            - result_value (str): "true" if successful, "false" otherwise
            - status (str): Execution state (COMPLETED or FAILED)

    Raises:
        ValueError: If parameter validation fails (e.g., invalid dates, start date after end date)
        RubrikException: If API calls to Rubrik Security Cloud fail
        Exception: For any other unexpected errors during execution
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = ADVANCE_IOC_SCAN_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    service_account_json, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    object_id = siemplify.extract_action_param(
        param_name="Object ID", input_type=str, is_mandatory=True
    )
    ioc_type = siemplify.extract_action_param(
        param_name="IOC Type", input_type=str, is_mandatory=False, default_value=None
    )
    ioc_value = siemplify.extract_action_param(
        param_name="IOC Value", input_type=str, is_mandatory=False, default_value=None
    )
    scan_name = siemplify.extract_action_param(
        param_name="Scan Name",
        input_type=str,
        is_mandatory=False,
    )
    advance_ioc = siemplify.extract_action_param(
        param_name="Advanced IOC",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )
    start_date = siemplify.extract_action_param(
        param_name="Start Date", input_type=str, is_mandatory=False, default_value=None
    )
    end_date = siemplify.extract_action_param(
        param_name="End Date", input_type=str, is_mandatory=False, default_value=None
    )
    max_snapshots_per_object = siemplify.extract_action_param(
        param_name="Max Snapshots Per Object",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )
    max_matches_per_snapshot = siemplify.extract_action_param(
        param_name="Max Matches Per Snapshot",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )
    max_snapshots_per_object = siemplify.extract_action_param(
        param_name="Max Snapshots Per Object",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )
    min_file_size = siemplify.extract_action_param(
        param_name="Min File Size",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )
    max_file_size = siemplify.extract_action_param(
        param_name="Max File Size",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )
    paths_to_include = siemplify.extract_action_param(
        param_name="Paths To Include",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )
    paths_to_exclude = siemplify.extract_action_param(
        param_name="Paths To Exclude",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )
    paths_to_exempt = siemplify.extract_action_param(
        param_name="Paths To Exempt",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = RESULT_VALUE_TRUE

    try:
        object_id = string_to_list(object_id, param_name="Object ID", is_mandatory=True)
        scan_name = generate_scan_name(scan_name)
        advance_ioc = validate_json(advance_ioc, "advance ioc")

        # Validate and process integer parameters
        max_snapshots_per_object = validate_integer_param(
            max_snapshots_per_object,
            "Max Snapshots Per Object",
            zero_allowed=False,
            allow_negative=False,
        )

        max_matches_per_snapshot = validate_integer_param(
            max_matches_per_snapshot,
            "Max Matches Per Snapshot",
            zero_allowed=False,
            allow_negative=False,
        )

        min_file_size = validate_integer_param(
            min_file_size,
            "Min File Size",
            zero_allowed=True,
            allow_negative=False,
        )

        max_file_size = validate_integer_param(
            max_file_size,
            "Max File Size",
            zero_allowed=False,
            allow_negative=False,
        )

        start_date = is_valid_date(start_date)
        end_date = is_valid_date(end_date)

        paths_to_include = string_to_list(paths_to_include)
        paths_to_exclude = string_to_list(paths_to_exclude)
        paths_to_exempt = string_to_list(paths_to_exempt)

        if start_date and end_date and (start_date > end_date):
            raise ValueError("Start Date must be before End Date")

        siemplify.LOGGER.info("Initializing Rubrik Security Cloud client")
        rubrik_manager = APIManager(
            service_account_json,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        siemplify.LOGGER.info("Starting Advance IOC Scan")
        response = rubrik_manager.start_advance_ioc_scan(
            object_id=object_id,
            ioc_type=ioc_type,
            ioc_value=ioc_value.strip() if ioc_value else None,
            scan_name=scan_name,
            advance_ioc_json=advance_ioc,
            start_date=start_date,
            end_date=end_date,
            max_snapshots_per_object=max_snapshots_per_object,
            min_file_size=min_file_size,
            max_file_size=max_file_size,
            paths_to_include=paths_to_include,
            paths_to_exclude=paths_to_exclude,
            paths_to_exempt=paths_to_exempt,
        )

        siemplify.result.add_result_json(json.dumps(response, indent=4))
        hunts = response.get("data", {}).get("startBulkThreatHunt", {}).get("hunts", [])

        model = AdvanceIOCScanDatamodel(hunts)
        output_message = (
            f"Successfully started Advance IOC Scan with {len(hunts)} hunt(s)"
            f"Showing up to {MAX_TABLE_RECORDS} records in table."
        )
        table_data = model.to_csv()
        consise_table_data = table_data[:MAX_TABLE_RECORDS]
        if consise_table_data:
            siemplify.result.add_data_table(
                "Advance IOC Scan Results", construct_csv(consise_table_data), "RSC"
            )

    except (
        ValueError,
        RubrikException,
    ) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(ADVANCE_IOC_SCAN_SCRIPT_NAME, str(e))
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
