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
from ..core.AWSIAMManager import AWSIAMManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.consts import (
    INTEGRATION_NAME,
    LIST_GROUPS,
    DEFAULT_MAX_RESULTS,
    DEFAULT_MIN_RESULTS,
)
from ..core.exceptions import AWSIAMValidationException

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {LIST_GROUPS}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    #  INIT INTEGRATION CONFIGURATION:
    aws_access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Access Key ID",
        is_mandatory=True,
    )

    aws_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Secret Key",
        is_mandatory=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
        default_value=True,
    )

    max_groups_to_return = extract_action_param(
        siemplify,
        param_name="Max Groups to Return",
        is_mandatory=False,
        print_value=True,
        input_type=int,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_results = []
    groups_as_csv = []
    result_value = True
    output_message = ""

    try:
        manager = AWSIAMManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            verify_ssl=verify_ssl,
        )

        if not DEFAULT_MIN_RESULTS <= max_groups_to_return <= DEFAULT_MAX_RESULTS:
            raise AWSIAMValidationException(
                f'Valid Range of "Max Groups to Return" is: [{DEFAULT_MIN_RESULTS}-'
                f"{DEFAULT_MAX_RESULTS}] \n"
            )

        siemplify.LOGGER.info("Connecting to AWS IAM Server..")
        manager.test_connectivity()
        siemplify.LOGGER.info(
            "Successfully connected to the AWS IAM server with the provided "
            "credentials!"
        )

        siemplify.LOGGER.info("Listing AWS IAM account groups..")
        groups = manager.list_groups(max_groups_to_return=max_groups_to_return)
        siemplify.LOGGER.info("Successfully Listed AWS IAM account groups")

        siemplify.LOGGER.info("Creating JSON and CSV result for groups..")
        for group in groups:
            json_results.append(group.as_json())
            groups_as_csv.append(group.as_csv())

        if json_results:
            siemplify.result.add_result_json(json_results)
            siemplify.result.add_data_table("IAM Groups", construct_csv(groups_as_csv))
        siemplify.LOGGER.info("Created JSON and CSV result for groups")

        output_message += (
            "Successfully listed available groups in AWS IAM."
            if json_results
            else "No groups found in" " AWS IAM \n"
        )

        status = EXECUTION_STATE_COMPLETED

    except Exception as error:
        siemplify.LOGGER.error(f"Error executing action {LIST_GROUPS}. Reason: {error}")
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = f"Error executing action {LIST_GROUPS}. Reason: {error}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
