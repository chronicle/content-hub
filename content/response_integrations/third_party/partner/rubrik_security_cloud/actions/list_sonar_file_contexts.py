from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    DEFAULT_LIMIT,
    DEFAULT_SONAR_FILE_SORT_ORDER,
    LIST_SONAR_FILE_CONTEXTS_SCRIPT_NAME,
    MAX_SNAPSHOTS_LIMIT,
    MAX_TABLE_RECORDS,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.datamodels import SonarFileContextsDatamodel
from ..core.rubrik_exceptions import RubrikException
from ..core.utils import (
    get_integration_params,
    validate_integer_param,
    validate_required_string,
)


@output_handler
def main():
    """List Sonar file contexts for a specific object snapshot from Rubrik Security Cloud.

    This action retrieves file contexts detected by Rubrik Sonar for a specific object
    snapshot. File contexts include sensitive data findings in files with support for
    filtering by file name, path, user ID, and pagination.

    Action Parameters:
        Object ID (str, required): The unique identifier of the object
        Snapshot ID (str, required): The unique identifier of the snapshot
        File Name (str, optional): Filter by file name
        File Path (str, optional): Filter by file path
        User ID (str, optional): Filter by user ID
        Include Whitelisted Results (str, optional): Whether to include whitelisted results
        Limit (str, optional): Maximum number of file contexts to retrieve (default: 50)
        Next Page Token (str, optional): Token for pagination to retrieve next page
        Sort By (str, optional): Field to sort results by
        Sort Order (str, optional): Sort order for results (default: from constants)

    Returns:
        None. Results are returned via siemplify.end() with:
            - output_message (str): Status message describing the retrieval results
            - result_value (str): "true" if successful, "false" otherwise
            - status (str): Execution state (COMPLETED or FAILED)

    Raises:
        ValueError: If parameter validation fails (e.g., invalid object ID or snapshot ID)
        RubrikException: If API calls to Rubrik Security Cloud fail
        Exception: For any other unexpected errors during execution
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_SONAR_FILE_CONTEXTS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    service_account_json, verify_ssl = get_integration_params(siemplify)

    # Action Parameters
    object_id = siemplify.extract_action_param(
        param_name="Object ID", input_type=str, is_mandatory=True
    )
    snapshot_id = siemplify.extract_action_param(
        param_name="Snapshot ID", input_type=str, is_mandatory=True
    )
    file_name = siemplify.extract_action_param(
        param_name="File Name", input_type=str, is_mandatory=False, default_value=None
    )
    file_path = siemplify.extract_action_param(
        param_name="File Path", input_type=str, is_mandatory=False, default_value=None
    )
    user_id = siemplify.extract_action_param(
        param_name="User ID", input_type=str, is_mandatory=False, default_value=None
    )
    include_whitelisted = siemplify.extract_action_param(
        param_name="Include Whitelisted Results",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )
    limit = siemplify.extract_action_param(
        param_name="Limit",
        input_type=str,
        is_mandatory=False,
        default_value=DEFAULT_LIMIT,
    )
    next_page_token = siemplify.extract_action_param(
        param_name="Next Page Token",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )
    sort_by = siemplify.extract_action_param(
        param_name="Sort By", input_type=str, is_mandatory=False, default_value=None
    )
    sort_order = siemplify.extract_action_param(
        param_name="Sort Order",
        input_type=str,
        is_mandatory=False,
        default_value=DEFAULT_SONAR_FILE_SORT_ORDER,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = RESULT_VALUE_TRUE

    try:
        object_id = validate_required_string(object_id, "Object ID")
        snapshot_id = validate_required_string(snapshot_id, "Snapshot ID")

        limit = validate_integer_param(
            limit,
            "Limit",
            zero_allowed=False,
            allow_negative=False,
            max_value=MAX_SNAPSHOTS_LIMIT,
            default_value=DEFAULT_LIMIT,
        )

        siemplify.LOGGER.info("Initializing Rubrik Security Cloud client")
        rubrik_manager = APIManager(
            service_account_json,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        siemplify.LOGGER.info(
            f"Retrieving Sonar file contexts for Object ID: {object_id}, Snapshot ID: {snapshot_id}"
        )
        response = rubrik_manager.list_sonar_file_contexts(
            object_id=object_id,
            snapshot_id=snapshot_id,
            file_name=file_name.strip() if file_name else None,
            file_path=file_path.strip() if file_path else None,
            user_id=user_id.strip() if user_id else None,
            include_whitelisted=include_whitelisted,
            limit=limit,
            next_page_token=next_page_token.strip() if next_page_token else None,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        siemplify.result.add_result_json(json.dumps(response, indent=4))

        data = response.get("data", {})
        policy_obj = data.get("policyObj", {})
        file_result_connection = policy_obj.get("fileResultConnection", {})
        edges = file_result_connection.get("edges", [])
        page_info = file_result_connection.get("pageInfo", {})

        file_count = len(edges)
        has_next_page = page_info.get("hasNextPage", False)
        end_cursor = page_info.get("endCursor", "")

        file_contexts_data = SonarFileContextsDatamodel(edges, page_info)

        output_message = (
            f"Successfully retrieved {file_count} file context(s) for Object ID: {object_id}"
            f"Showing up to {MAX_TABLE_RECORDS} records in table."
        )
        if has_next_page:
            output_message += f". More results available. Next page token: {end_cursor}"

        table_data = file_contexts_data.to_csv()
        consise_table_data = table_data[:MAX_TABLE_RECORDS]
        if consise_table_data:
            siemplify.result.add_data_table(
                "Sonar File Contexts", construct_csv(consise_table_data), "RSC"
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
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            LIST_SONAR_FILE_CONTEXTS_SCRIPT_NAME, str(e)
        )
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
