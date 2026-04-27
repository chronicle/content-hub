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

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import construct_csv, extract_action_param, extract_configuration_param

from ..core.FireEyeEXManager import FireEyeEXManager

INTEGRATION_NAME = "FireEyeEX"
SCRIPT_NAME = "List quarantined emails"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        input_type=str,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        input_type=str,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    start_time = extract_action_param(
        siemplify,
        param_name="Start Time",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    end_time = extract_action_param(
        siemplify,
        param_name="End Time",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    sender = extract_action_param(
        siemplify,
        param_name="Sender Filter",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    subject = extract_action_param(
        siemplify,
        param_name="Subject Filter",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Email to Return",
        is_mandatory=False,
        input_type=int,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_results = []
    status = EXECUTION_STATE_COMPLETED
    result_value = "true"

    try:
        ex_manager = FireEyeEXManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )
        quarantined_emails = ex_manager.list_quarantined_emails(
            start_time=start_time,
            end_time=end_time,
            sender=sender,
            subject=subject,
            limit=limit,
        )

        json_results = [email.raw_data for email in quarantined_emails]

        siemplify.LOGGER.info(f"Found {len(quarantined_emails)} quarantined emails.")

        if quarantined_emails:
            siemplify.result.add_data_table(
                "Quarantined Emails",
                construct_csv([email.as_csv() for email in quarantined_emails]),
            )
            output_message = "Successfully listed FireEye EX quarantined emails!"

        else:
            output_message = "No quarantined emails were found in FireEye EX!"

        ex_manager.logout()

    except Exception as e:
        siemplify.LOGGER.exception(
            f'Error executing action "List Quarantined Emails". Reason: {e}'
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = (
            f'Error executing action "List Quarantined Emails". Reason: {e}'
        )

    siemplify.result.add_result_json(json_results)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
