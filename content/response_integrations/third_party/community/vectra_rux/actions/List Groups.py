from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import construct_csv, extract_action_param, extract_configuration_param

from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    INTEGRATION_NAME,
    LIST_GROUPS_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.UtilsManager import (
    process_action_parameter,
    validate_integer,
    validate_limit_param,
)
from ..core.VectraRUXExceptions import InvalidIntegerException, VectraRUXException
from ..core.VectraRUXManager import VectraRUXManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_GROUPS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration parameters
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

    # Action parameters
    host_names = extract_action_param(
        siemplify,
        param_name="Host Names",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    host_ids = extract_action_param(
        siemplify,
        param_name="Host Ids",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    account_names = extract_action_param(
        siemplify,
        param_name="Account Names",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    domains = extract_action_param(
        siemplify,
        param_name="Domains",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    importance = extract_action_param(
        siemplify,
        param_name="Importance",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    ips = extract_action_param(
        siemplify,
        param_name="IPs",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    description = extract_action_param(
        siemplify,
        param_name="Description",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    last_modified_timestamp = extract_action_param(
        siemplify,
        param_name="Last Modified Timestamp GTE",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    name = extract_action_param(
        siemplify,
        param_name="Name",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    last_modified_by = extract_action_param(
        siemplify,
        param_name="Last Modified By",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    group_type = extract_action_param(
        siemplify,
        param_name="Type",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    result_limit = extract_action_param(
        siemplify,
        param_name="Limit",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    action_parameters = [host_names, account_names, domains, ips]
    processed_action_parameters = map(process_action_parameter, action_parameters)
    host_names, account_names, domains, ips = processed_action_parameters

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        result_limit = validate_integer(
            validate_limit_param(result_limit),
            zero_allowed=True,
            field_name="Limit",
        )
        vectra_manager = VectraRUXManager(
            api_root,
            client_id,
            client_secret,
            siemplify=siemplify,
        )

        group_objects, groups = vectra_manager.get_group_list(
            result_limit,
            group_type,
            host_names=host_names,
            host_ids=host_ids,
            account_names=account_names,
            domains=domains,
            importance=importance,
            ips=ips,
            description=description,
            last_modified_timestamp=last_modified_timestamp,
            name=name,
            last_modified_by=last_modified_by,
        )

        if not groups:
            output_message = "No groups were found with the provided parameters."
        else:
            output_message = f"Successfully retrieved {len(groups)} groups."
            siemplify.result.add_data_table(
                title="List Of Groups",
                data_table=construct_csv(
                    [group_obj.fetch_group_details() for group_obj in group_objects],
                ),
            )

        siemplify.result.add_result_json(json.dumps(groups, indent=4))

    except InvalidIntegerException as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except VectraRUXException as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(
            f"{e}, while performing action {LIST_GROUPS_SCRIPT_NAME}",
        )
        siemplify.LOGGER.exception(e)
    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(LIST_GROUPS_SCRIPT_NAME, e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"is_success: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
