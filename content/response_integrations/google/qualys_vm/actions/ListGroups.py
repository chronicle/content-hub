from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import construct_csv
from ..core.manager_factory import create_qualys_manager_from_action
from ..core.constants import INTEGRATION_NAME, LIST_GROUPS_SCRIPT_NAME
import json


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_GROUPS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = True
    status = EXECUTION_STATE_COMPLETED
    json_results = {}

    try:
        qualys_manager = create_qualys_manager_from_action(siemplify)
        groups = qualys_manager.list_asset_groups()

        if groups:
            json_results = json.dumps(groups)
            csv_output = construct_csv(groups)
            siemplify.result.add_data_table("Groups", csv_output)
            output_message = (
                f"Successfully returned {len(groups)} groups from {INTEGRATION_NAME}."
            )
            siemplify.result.add_result_json(json_results)
        else:
            output_message = f"No groups found in {INTEGRATION_NAME}."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {LIST_GROUPS_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{LIST_GROUPS_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
