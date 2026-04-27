from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from ..core.ActiveDirectoryManager import ActiveDirectoryManager
import sys
import base64
import json

# =====================================
#             CONSTANTS               #
# =====================================
INTEGRATION_NAME = "ActiveDirectory"
SCRIPT_NAME = "ActiveDirectory - SearchActiveDirectory"
SEARCH_PAGE_SIZE = 1000


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    mode = "Main" if is_first_run else "QueryState"

    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATIONS:
    server = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Server",
        input_type=str,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Username",
        input_type=str,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Password",
        input_type=str,
    )
    domain = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Domain",
        input_type=str,
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
    query_string = extract_action_param(
        siemplify,
        param_name="Query String",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )
    limit = extract_action_param(
        siemplify, param_name="Limit", input_type=int, print_value=True, default_value=0
    )
    limit = max(0, limit)

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

        entities, cookie = manager.search_with_paging(
            query_string, SEARCH_PAGE_SIZE, cookie, limit
        )
        fetched_entities.extend(entities)

        if cookie and (len(fetched_entities) < limit):
            cookie = base64.b64encode(cookie).decode()
            output_message = f"Fetched {len(fetched_entities)} entities"
            status = EXECUTION_STATE_INPROGRESS
            result_value = json.dumps((fetched_entities, cookie))
        else:
            status = EXECUTION_STATE_COMPLETED
            result_value = True
            if entities:
                siemplify.result.add_result_json(fetched_entities)
                output_message = (
                    f"Successfully performed query {query_string} in Active Directory"
                )
            else:
                output_message = (
                    f"No results to show following the query: {query_string}"
                )
    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}.")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = f"Error executing action {SCRIPT_NAME}. Reason: {e}"

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
