from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import construct_csv, extract_action_param, extract_configuration_param

from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    INTEGRATION_NAME,
    LIST_ASSIGNMENTS_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.UtilsManager import (
    process_action_parameter_integer,
    validate_integer,
    validate_limit_param,
)
from ..core.VectraRUXExceptions import InvalidIntegerException
from ..core.VectraRUXManager import VectraRUXManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_ASSIGNMENTS_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        input_type=str,
        is_mandatory=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        input_type=str,
        is_mandatory=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        print_value=False,
        is_mandatory=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = RESULT_VALUE_TRUE
    status = EXECUTION_STATE_COMPLETED

    try:
        query_params_mapping = {}

        # Action Parameters
        account_ids = extract_action_param(
            siemplify,
            param_name="Accounts IDs",
            input_type=str,
            is_mandatory=False,
        )

        host_ids = extract_action_param(
            siemplify,
            param_name="Hosts IDs",
            input_type=str,
            is_mandatory=False,
        )

        assignee_ids = extract_action_param(
            siemplify,
            param_name="Assignees IDs",
            input_type=str,
            is_mandatory=False,
        )

        resolution_ids = extract_action_param(
            siemplify,
            param_name="Resolution IDs",
            input_type=str,
            is_mandatory=False,
        )

        resolved_status = extract_action_param(
            siemplify,
            param_name="Resolved",
            input_type=str,
            is_mandatory=False,
        )
        if resolved_status != "None":
            query_params_mapping["resolved"] = resolved_status

        created_after = extract_action_param(
            siemplify,
            param_name="Created After",
            input_type=str,
            is_mandatory=False,
        )
        if created_after:
            query_params_mapping["created_after"] = created_after

        account_ids = process_action_parameter_integer(account_ids, "Accounts IDs")
        if account_ids:
            query_params_mapping["accounts"] = ",".join(account_ids)

        host_ids = process_action_parameter_integer(host_ids, "Hosts IDs")
        if host_ids:
            query_params_mapping["hosts"] = ",".join(host_ids)

        assignee_ids = process_action_parameter_integer(assignee_ids, "Assignees IDs")
        if assignee_ids:
            query_params_mapping["assignees"] = ",".join(assignee_ids)

        resolution_ids = process_action_parameter_integer(
            resolution_ids,
            "Resolution IDs",
        )
        if resolution_ids:
            query_params_mapping["resolution"] = ",".join(resolution_ids)

        max_assignment_to_return = extract_action_param(
            siemplify,
            param_name="Limit",
            input_type=str,
            is_mandatory=False,
        )

        max_assignment_to_return = validate_integer(
            validate_limit_param(max_assignment_to_return),
            zero_allowed=True,
            field_name="Limit",
        )
        vectra_manager = VectraRUXManager(
            api_root,
            client_id,
            client_secret,
            siemplify=siemplify,
        )

        assignments_obj, assignments = vectra_manager.get_assignment_list(
            query_params_mapping,
            max_assignment_to_return,
        )

        if not assignments:
            output_message = "No assignments found with provided parameters"
        else:
            output_message = f"Successfully retrieved {len(assignments)} assignments."
            siemplify.result.add_data_table(
                title="Assignment Details",
                data_table=construct_csv(
                    [
                        assignment.list_assignment_csv()
                        for assignment in assignments_obj
                    ],
                ),
            )

        siemplify.result.add_result_json(json.dumps(assignments, indent=4))
    except InvalidIntegerException as e:
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE
        output_message = f"{e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            LIST_ASSIGNMENTS_SCRIPT_NAME,
            e,
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
