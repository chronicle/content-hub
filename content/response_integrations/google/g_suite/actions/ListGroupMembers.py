from __future__ import annotations
import json

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv

from g_suite.core.action_init import create_api_client
from g_suite.core.consts import INTEGRATION_NAME, LIST_GROUP_MEMBERS_SCRIPT_NAME
from g_suite.core.exceptions import GSuiteNotFoundException
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {LIST_GROUP_MEMBERS_SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Action configuration
    group_email_address = extract_action_param(
        siemplify, param_name="Group Email Address", is_mandatory=True, print_value=True
    )
    include_derived_membership = extract_action_param(
        siemplify,
        param_name="Include Derived Membership",
        is_mandatory=True,
        default_value=True,
        print_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_FAILED
    result_value = json.dumps([])

    try:
        gsuite_manager = create_api_client(siemplify)
        group_members = gsuite_manager.list_group_members(
            group_email_address=group_email_address,
            include_derived_membership=include_derived_membership,
        )
        json_results = [member.as_json() for member in group_members]
        siemplify.result.add_result_json(json_results)
        siemplify.result.add_data_table(
            f"Group {group_email_address} Members",
            construct_csv([member.as_csv() for member in group_members]),
        )
        output_message = f"Successfully fetched group members."

        status = EXECUTION_STATE_COMPLETED
        result_value = json.dumps(json_results)

    except GSuiteNotFoundException as error:
        output_message = (
            f"Error executing action {LIST_GROUP_MEMBERS_SCRIPT_NAME}. Reason: "
            "Group email address was not found"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
    except Exception as error:
        output_message = (
            f"Error executing action {LIST_GROUP_MEMBERS_SCRIPT_NAME}. Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
