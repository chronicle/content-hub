# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""AtlassianConfluenceServer - GetChildPages."""
from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_action_param

from ..core.ConfluenceManager import ConfluenceManager
from ..core.constants import GET_CHILD_PAGES_SCRIPT_NAME
from ..core.exceptions import ConfluenceInvalidLimitError
from ..core.utils import get_configuration_params


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_CHILD_PAGES_SCRIPT_NAME
    siemplify.LOGGER.info("--------------- Main - Param Init ---------------")

    # Integration Configuration
    (api_root, username, password, api_token, verify_ssl) = get_configuration_params(
        siemplify_action_instance=siemplify
    )

    # Action parameters
    page_id = extract_action_param(
        siemplify, param_name="Page ID", is_mandatory=True, print_value=True
    )
    max_records = extract_action_param(
        siemplify,
        param_name="Max Records to Return",
        input_type=int,
        is_mandatory=True,
        print_value=True,
        default_value=10,
    )

    siemplify.LOGGER.info("--------------- Main - Started ---------------")

    result_value = False
    status = EXECUTION_STATE_FAILED

    try:
        if max_records < 1:
            raise ConfluenceInvalidLimitError(
                "Invalid value was provided for 'Max Records to "
                f"Return': {max_records}. Positive number should be provided."
            )

        confluence_manager = ConfluenceManager(
            api_root,
            username,
            password,
            api_token,
            verify_ssl=verify_ssl,
            logger=siemplify.LOGGER,
        )

        child_pages = confluence_manager.get_child_pages(page_id, max_records)
        child_pages_json = child_pages.to_json()
        if child_pages_json.get("results"):
            siemplify.result.add_result_json(child_pages_json)
            output_message = (
                "Successfully found child pages for the provided "
                f"Atlassian Confluence Server page id: {page_id}"
            )
            result_value = True
        else:
            output_message = (
                "No child pages were found for the provided "
                f"Atlassian Confluence Server page id {page_id}"
            )
            result_value = False

        status = EXECUTION_STATE_COMPLETED

    except Exception as error:
        output_message = (
            f"Error executing action '{siemplify.script_name}'. Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
