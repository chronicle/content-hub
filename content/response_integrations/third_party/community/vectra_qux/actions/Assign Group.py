from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_action_param, extract_configuration_param

from ..core.constants import (
    ASSIGN_GROUP_SCRIPT_NAME,
    COMMON_ACTION_ERROR_MESSAGE,
    GROUP_TYPE_FIELD_MAPPING,
    INTEGRATION_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.GroupHTMLView import render_group_object_as_html
from ..core.UtilsManager import process_action_parameter, validate_integer
from ..core.VectraQUXExceptions import (
    BadRequestException,
    InvalidIntegerException,
    ItemNotFoundException,
)
from ..core.VectraQUXManager import VectraQUXManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ASSIGN_GROUP_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration parameters
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        input_type=str,
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        input_type=str,
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    # Action parameters
    group_id = extract_action_param(
        siemplify,
        param_name="Group ID",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    members = extract_action_param(
        siemplify,
        param_name="Members",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    members = process_action_parameter(members)
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        group_id = validate_integer(group_id, zero_allowed=False, field_name="Group ID")
        vectra_manager = VectraQUXManager(
            api_root,
            api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        group_assigned = vectra_manager.update_group_members(
            group_id,
            members,
            membership_action="append",
        )
        group_type = group_assigned.get("type")
        group_members = [
            (
                member.get(GROUP_TYPE_FIELD_MAPPING[group_type])
                if GROUP_TYPE_FIELD_MAPPING[group_type] != group_type
                else member
            )
            for member in group_assigned.get("members")
        ]
        members_not_assigned = []
        members_assigned = []

        for member in members:
            if member not in group_members:
                members_not_assigned.append(member)
            else:
                members_assigned.append(member)

        if members == members_not_assigned:
            output_message = f"No members were assigned to the {group_assigned.get('name')} group. Please provide valid members of type {group_type} that exists."
            result_value = RESULT_VALUE_FALSE
            status = EXECUTION_STATE_FAILED
        else:
            if members_not_assigned:
                output_message = f"Successfully assigned '{len(members_assigned)}' members to the {group_assigned.get('name')} group. However, the following members were not assigned: {', '.join(members_not_assigned)}. Please provide valid members of type {group_type} that exists."
            else:
                output_message = f"Successfully assigned {len(members)} members to the {group_assigned.get('name')} group."

            group_html_view = render_group_object_as_html(group_assigned, group_type)
            siemplify.result.add_html(
                "Group Details",
                "Assigned group members",
                group_html_view,
            )

        siemplify.result.add_result_json(json.dumps(group_assigned, indent=4))

    except InvalidIntegerException as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except (BadRequestException, ItemNotFoundException) as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(ASSIGN_GROUP_SCRIPT_NAME, e)
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
