from __future__ import annotations
import json
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.NetskopeManagerFactory import NetskopeManagerFactory
from ..core.constants import QUARANTINE_MAX_LIMIT
from TIPCommon import (
    extract_action_param,
    construct_csv,
    dict_to_flat,
)
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

INTEGRATION_NAME = "Netskope"
LISTQUARANTINEDFILES_SCRIPT_NAME = f"{INTEGRATION_NAME} - ListQuarantinedFiles"
CSV_TABLE_NAME = "Netskope - Quarantined Files"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LISTQUARANTINEDFILES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Parameters
    use_v2_api = extract_action_param(
        siemplify,
        param_name="Use V2 API",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )
    start_time = extract_action_param(
        siemplify, param_name="Start Time", is_mandatory=False, print_value=True
    )
    end_time = extract_action_param(
        siemplify, param_name="End Time", is_mandatory=False, print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Items To Return",
        is_mandatory=False,
        input_type=int,
        print_value=True,
    )
    if use_v2_api:
        limit = limit or QUARANTINE_MAX_LIMIT

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    siemplify.LOGGER.info("Starting to perform the action")
    status = EXECUTION_STATE_FAILED
    json_results = []
    output_files = ""

    try:
        netskope_manager = NetskopeManagerFactory.get_manager(
            siemplify, api_version="v2" if use_v2_api else "v1"
        )
        files_gen = netskope_manager.get_quarantined_files(
            start_time=start_time, end_time=end_time, limit=limit
        )
        files = list(files_gen)

        output_message = f"Found {len(files)} quarantined files"

        if files:
            json_results = files
            flat_files = list(map(dict_to_flat, files))
            csv_output = construct_csv(flat_files)
            siemplify.result.add_data_table(CSV_TABLE_NAME, csv_output)

        # add json
        siemplify.result.add_result_json(json.dumps(json_results))
        output_files = json.dumps(files)
        siemplify.LOGGER.info("Finished performing the action")
        status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        output_message = f'Error executing action "ListQuarantinedFiles". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, output_files, status)


if __name__ == "__main__":
    main()
