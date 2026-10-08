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
from TIPCommon.extraction import extract_configuration_param, extract_action_param

from ..core.CBCloudManager import CBCloudManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.constants import (
    INTEGRATION_NAME,
    CREATE_REPUTATION_OVERRIDE_FOR_CERTIFICATE_SCRIPT_NAME,
    NOT_SPECIFIED,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_REPUTATION_OVERRIDE_FOR_CERTIFICATE_SCRIPT_NAME

    siemplify.LOGGER.info("================= Main - Param Init =================")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    org_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Organization Key",
        is_mandatory=True,
    )
    api_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API ID",
        is_mandatory=True,
    )
    api_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Secret Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    certificate_authority = extract_action_param(
        siemplify,
        param_name="Certificate Authority",
        is_mandatory=False,
        print_value=True,
    )
    signed_by = extract_action_param(
        siemplify, param_name="Signed By", is_mandatory=True, print_value=True
    )
    description = extract_action_param(
        siemplify, param_name="Description", is_mandatory=False, print_value=True
    )
    reputation_override_list = extract_action_param(
        siemplify,
        param_name="Reputation Override List",
        is_mandatory=True,
        default_value=NOT_SPECIFIED,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED

    try:
        if reputation_override_list == NOT_SPECIFIED:
            raise Exception("Reputation Override List is not specified.")
        manager = CBCloudManager(
            api_root=api_root,
            org_key=org_key,
            api_id=api_id,
            api_secret_key=api_secret_key,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        try:
            reputation_override = manager.create_certificate_reputation_override(
                override_list=reputation_override_list,
                signed_by=signed_by,
                certificate_authority=certificate_authority,
                description=description,
            )
            siemplify.result.add_result_json(reputation_override.to_json())
            result_value = True
            output_message = f"Successfully created new reputation override: {reputation_override.id}"
        except Exception as e:
            output_message = f"Action failed to create a new certificate reputation override. Reason: {e}"
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = f"Error executing action {CREATE_REPUTATION_OVERRIDE_FOR_CERTIFICATE_SCRIPT_NAME}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
