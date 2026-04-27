from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import construct_csv
from ..core.manager_factory import create_qualys_manager_from_action
from ..core.constants import INTEGRATION_NAME, LIST_REPORTS_SCRIPT_NAME
import json


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_REPORTS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = True
    status = EXECUTION_STATE_COMPLETED
    json_results = {}

    try:
        qualys_manager = create_qualys_manager_from_action(siemplify)
        reports = qualys_manager.list_reports()

        if reports:
            json_results = json.dumps(reports)
            csv_output = construct_csv(reports)
            siemplify.result.add_data_table("Reports", csv_output)
            output_message = (
                f"Successfully returned {len(reports)} reports from {INTEGRATION_NAME}."
            )
            siemplify.result.add_result_json(json_results)
        else:
            output_message = f"No reports found in {INTEGRATION_NAME}."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {LIST_REPORTS_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{LIST_REPORTS_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
