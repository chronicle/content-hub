from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_action_param, extract_configuration_param

from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    GROUP_TYPE_FIELD_MAPPING,
    INTEGRATION_NAME,
    REMOVE_GROUP_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.GroupHTMLView import render_group_object_as_html
from ..core.UtilsManager import process_action_parameter, validate_integer
from ..core.VectraRUXExceptions import (
    BadRequestException,
    InvalidIntegerException,
    ItemNotFoundException,
)
from ..core.VectraRUXManager import VectraRUXManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = REMOVE_GROUP_SCRIPT_NAME
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
        vectra_manager = VectraRUXManager(
            api_root,
            client_id,
            client_secret,
            siemplify=siemplify,
        )
        group_members = vectra_manager.get_group_members(group_id)
        group_removed = vectra_manager.update_group_members(
            group_id,
            members,
            membership_action="remove",
        )
        group_type = group_removed.get("type")
        removed_group_members = group_removed.get("members") or []
        updated_group_members = [
            (
                member.get(GROUP_TYPE_FIELD_MAPPING[group_type])
                if GROUP_TYPE_FIELD_MAPPING[group_type] != group_type
                else member
            )
            for member in removed_group_members
        ]

        members_not_removed = []
        members_removed = []

        for member in members:
            if member in group_members and member not in updated_group_members:
                members_removed.append(member)
            else:
                members_not_removed.append(member)

        if members == members_not_removed:
            output_message = f"No members were removed from the {group_removed.get('name')} group. Please provide valid members of type {group_type} that exists."
            result_value = RESULT_VALUE_FALSE
            status = EXECUTION_STATE_FAILED
        else:
            if members_not_removed:
                output_message = f"Successfully removed '{len(members_removed)}' members to the {group_removed.get('name')} group. However, the following members were not removed: {', '.join(members_not_removed)}. Please provide valid members of type {group_type} that exists."
            else:
                output_message = f"Successfully removed {len(members)} members to the {group_removed.get('name')} group."

            group_html_view = render_group_object_as_html(group_removed, group_type)
            siemplify.result.add_html(
                "Group Details",
                "Removed group members",
                group_html_view,
            )

        siemplify.result.add_result_json(json.dumps(group_removed, indent=4))

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
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(REMOVE_GROUP_SCRIPT_NAME, e)
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
