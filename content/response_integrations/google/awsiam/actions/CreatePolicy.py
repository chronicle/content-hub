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
import json
from ..core import utils
from ..core.AWSIAMManager import AWSIAMManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.consts import INTEGRATION_NAME, CREATE_POLICY_SCRIPT_NAME
from ..core.exceptions import (
    AWSIAMEntityAlreadyExistsException,
    AWSIAMValidationException,
    AWSIAMMalformedPolicyDocument,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {CREATE_POLICY_SCRIPT_NAME}"
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

    policy_name = extract_action_param(
        siemplify, param_name="Policy Name", is_mandatory=True, print_value=True
    )
    policy_document = extract_action_param(
        siemplify, param_name="Policy Document", is_mandatory=True, print_value=True
    )
    policy_description = extract_action_param(
        siemplify,
        param_name="Description",
        is_mandatory=False,
        print_value=True,
        default_value=None,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_FAILED
    result_value = False

    try:
        manager = AWSIAMManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            verify_ssl=verify_ssl,
        )

        siemplify.LOGGER.info("Connecting to AWS IAM Server..")
        manager.test_connectivity()
        siemplify.LOGGER.info(
            "Successfully connected to the AWS IAM server with the provided "
            "credentials!"
        )

        try:
            siemplify.LOGGER.info("Validating policy document")
            try:
                policy_document = json.loads(policy_document)
                policy_document_str = json.dumps(policy_document)
            except Exception as error:
                raise AWSIAMMalformedPolicyDocument(
                    "Failed to load JSON policy document"
                ) from error
            siemplify.LOGGER.info("Successfully validated policy document")

            siemplify.LOGGER.info(f"Validating policy name {policy_name}")
            if not utils.is_name_valid(policy_name):
                raise AWSIAMValidationException(
                    f"Failed to validate policy name {policy_name}"
                )
            siemplify.LOGGER.info(f"Successfully validate policy name {policy_name}")

            siemplify.LOGGER.info(f"Creating new policy with name: {policy_name}")

            policy = manager.create_policy(
                policy_name=policy_name,
                policy_document=policy_document_str,
                description=policy_description,
            )
            siemplify.LOGGER.info(
                f"Successfully created new policy with name: {policy_name}"
            )

            siemplify.result.add_result_json(policy.as_json())
            output_message = f"{policy_name} policy was successfully created."
            result_value = True
            status = EXECUTION_STATE_COMPLETED

        except AWSIAMEntityAlreadyExistsException as error:
            output_message = (
                f"Could not create {policy_name} policy. Policy names must be unique "
                "within an account."
            )
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.exception(error)

        except AWSIAMValidationException as error:
            output_message = (
                f"Could not create {policy_name} policy. Policy names must contain "
                "only alphanumeric characters and/or the following: +=,.@_-."
            )
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.exception(error)

        except AWSIAMMalformedPolicyDocument as error:
            output_message = (
                f"Could not create {policy_name} policy. The policy document was "
                f"malformed. Reason: {error}"
            )
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.exception(error)

    except Exception as error:
        siemplify.LOGGER.error(
            f"Error executing action {CREATE_POLICY_SCRIPT_NAME}. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        output_message = (
            f"Error executing action {CREATE_POLICY_SCRIPT_NAME}. Reason: {error}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
