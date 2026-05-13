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

from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.BlueLivManager import BlueLivManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.consts import INTEGRATION_NAME, ADD_COMMENT_TO_THREAT_ACTION


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_COMMENT_TO_THREAT_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="User Name",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        print_value=False,
    )
    organization_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Organization ID",
        is_mandatory=True,
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
    )

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""

    try:
        siemplify.LOGGER.info("----------------- Main - Started -----------------")
        module_id = extract_action_param(
            siemplify,
            param_name="Module ID",
            is_mandatory=True,
            print_value=True,
            input_type=str,
        )
        module_type = extract_action_param(
            siemplify,
            param_name="Module Type",
            is_mandatory=True,
            print_value=True,
            input_type=str,
        )
        module_type = module_type.lower()
        threat_id = extract_action_param(
            siemplify,
            param_name="Resource ID",
            is_mandatory=True,
            print_value=True,
            input_type=str,
        )
        comment = extract_action_param(
            siemplify,
            param_name="Comment Text",
            is_mandatory=True,
            print_value=True,
            input_type=str,
        )

        blueliv_manager = BlueLivManager(
            api_root=api_root,
            username=username,
            password=password,
            organization_id=organization_id,
            verify_ssl=verify_ssl,
        )
        result = blueliv_manager.add_comment_to_threat(
            module_id=module_id,
            module_type=module_type,
            threat_id=threat_id,
            comment=comment,
        )

        if result:
            output_message = (
                f"Successfully added the comment to threat ID: {threat_id}."
            )
            siemplify.result.add_result_json([comment.to_json() for comment in result])
            siemplify.result.add_entity_table(
                f"Threat ID {threat_id} Comments",
                construct_csv([comment.to_table() for comment in result]),
            )

        else:
            output_message = (
                f"The action wasn't able to add comment to threat ID: {threat_id}."
            )
            result_value = False

    except Exception as e:
        output_message += f"Failed to perform action {ADD_COMMENT_TO_THREAT_ACTION} {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
