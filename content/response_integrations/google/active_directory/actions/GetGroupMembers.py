from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from ..core.ActiveDirectoryManager import (
    ActiveDirectoryManager,
    ActiveDirectoryNotFoundGroupError,
)
import sys
import base64
import json

# =====================================
#             CONSTANTS               #
# =====================================
INTEGRATION_NAME = "ActiveDirectory"
SCRIPT_NAME = "ActiveDirectory - Get Group Members"

SUPPORTED_ENTITY_TYPES = [EntityTypes.USER, EntityTypes.HOSTNAME]
SEARCH_PAGE_SIZE = 1000


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    status = EXECUTION_STATE_COMPLETED
    result_value = False

    mode = "Main" if is_first_run else "QueryState"

    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATIONS:
    server = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Server",
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Username",
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Password",
    )
    domain = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Domain",
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Use SSL",
        input_type=bool,
    )
    custom_query_fields = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Custom Query Fields",
        input_type=str,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File - parsed into Base64 String",
    )
    # INIT ACTION CONFIGURATIONS:
    group_name = extract_action_param(
        siemplify, param_name="Group Name", is_mandatory=True
    )
    member_type = extract_action_param(
        siemplify, param_name="Members Type", is_mandatory=True
    )
    size_limit = extract_action_param(
        siemplify,
        param_name="Limit",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )
    is_nested_search = extract_action_param(
        siemplify,
        param_name="Perform Nested Search",
        is_mandatory=True,
        input_type=bool,
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    try:
        manager = ActiveDirectoryManager(
            server,
            domain,
            username,
            password,
            use_ssl,
            custom_query_fields,
            ca_certificate,
            siemplify.LOGGER,
        )
        cookie = None
        fetched_entities = []

        if not is_first_run:
            fetched_entities, cookie = json.loads(
                siemplify.parameters["additional_data"]
            )
            cookie = base64.b64decode(cookie)

        group_distinguished_name = manager.get_group_distinguished_name(group_name)

        entities, cookie = manager.list_user_group_members(
            page_size=SEARCH_PAGE_SIZE,
            size_limit=size_limit,
            entity_type=member_type,
            cookie=cookie,
            is_nested_search=is_nested_search,
            member_of=group_distinguished_name,
        )

        fetched_entities.extend([member.to_json() for member in entities])

        if cookie and (len(fetched_entities) < size_limit):
            cookie = base64.b64encode(cookie).decode()
            output_message = f"Still running... fetching {group_name} group members from {INTEGRATION_NAME}."
            status = EXECUTION_STATE_INPROGRESS
            result_value = json.dumps((fetched_entities, cookie))
        else:
            status = EXECUTION_STATE_COMPLETED
            result_value = True
            if fetched_entities:
                siemplify.result.add_result_json(fetched_entities)
                output_message = f"Successfully fetched {INTEGRATION_NAME} group {group_name} members."
            else:
                output_message = f"Successfully fetched data of group {group_name}. Note: Group is empty"
    except ActiveDirectoryNotFoundGroupError as e:
        output_message = f"{e}"
    except Exception as e:
        siemplify.LOGGER.error(f"Error executing action {SCRIPT_NAME}.")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = f"Error executing action {SCRIPT_NAME}. Reason: {e}."

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
