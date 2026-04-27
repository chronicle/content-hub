from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.IBossManager import IBossManager
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import LIST_POLICY_BLOCK_LIST_ENTRIES_SCRIPT_NAME, INTEGRATION_NAME
from ..core.exceptions import ListIsNotBlockListException

CSV_CASE_WALL_NAME = "Block List Entries. Category {}"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_POLICY_BLOCK_LIST_ENTRIES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    cloud_api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Cloud API Root",
        is_mandatory=True,
    )
    account_api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Account API Root",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )

    category_id = extract_action_param(
        siemplify, param_name="Category ID", is_mandatory=True, print_value=True
    )
    max_entries_to_return = extract_action_param(
        siemplify,
        param_name="Max Entries to Return",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_FAILED
    result_value = False
    try:
        manager = IBossManager(
            cloud_api_root,
            account_api_root,
            username,
            password,
            verify_ssl,
            siemplify.LOGGER,
        )
        manager.validate_if_block_list(category_id)
        entries = manager.list_policy_block_list_entries(
            category_id, max_entries_to_return
        )
        if entries:
            siemplify.result.add_result_json([entry.to_json() for entry in entries])
            siemplify.result.add_data_table(
                title=CSV_CASE_WALL_NAME.format(category_id),
                data_table=construct_csv([entry.to_csv() for entry in entries]),
            )

            result_value = True
            output_message = (
                "Successfully listed entries from the iBoss Block List in a category "
                f"with ID '{category_id}'")
        else:
            output_message = (
                "No Block List entries were found in the iBoss category with ID "
                f"'{category_id}'"
            )
        siemplify.LOGGER.info(output_message)

        status = EXECUTION_STATE_COMPLETED
    except ListIsNotBlockListException:
        output_message = (
            f"Category with ID {category_id} is not associated with a Block list."
        )
        siemplify.LOGGER.info(output_message)
        status = EXECUTION_STATE_COMPLETED
    except Exception as e:
        output_message = (
            f"Error executing action '{LIST_POLICY_BLOCK_LIST_ENTRIES_SCRIPT_NAME}'. "
            f"Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  "
        f"result_value: {result_value}\n  "
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
