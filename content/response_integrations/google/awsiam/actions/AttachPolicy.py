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
from TIPCommon import extract_configuration_param, extract_action_param
from ..core import utils
from ..core.AWSIAMManager import AWSIAMManager
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED, EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import (
    INTEGRATION_NAME,
    ATTACH_POLICY_SCRIPT_NAME,
    GROUP_IDENTITY_TYPE,
    USER_IDENTITY_TYPE,
    ROLE_IDENTITY_TYPE,
)
from ..core.exceptions import AWSIAMEntityNotFoundException, AWSIAMValidationException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {ATTACH_POLICY_SCRIPT_NAME}"
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

    identity_type = extract_action_param(
        siemplify,
        param_name="Identity Type",
        is_mandatory=True,
        print_value=True,
        default_value=GROUP_IDENTITY_TYPE,
    )
    identity_name = extract_action_param(
        siemplify, param_name="Identity Name", is_mandatory=True, print_value=True
    )
    policy_name = extract_action_param(
        siemplify, param_name="Policy Name", is_mandatory=True, print_value=True
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

        if not (
            utils.is_name_valid(identity_name) and utils.is_name_valid(policy_name)
        ):
            raise AWSIAMValidationException(
                f"Could not attach {policy_name} to {identity_type}:{identity_name}. "
                "Names must contain only alphanumeric characters and/or the "
                "following: +=,.@_-"
            )

        policy_arn = manager.get_policy_arn(policy_name)

        try:
            if identity_type == GROUP_IDENTITY_TYPE:
                manager.attach_group_policy(
                    group_name=identity_name, policy_arn=policy_arn
                )
            elif identity_type == USER_IDENTITY_TYPE:
                manager.attach_user_policy(
                    user_name=identity_name, policy_arn=policy_arn
                )
            elif identity_type == ROLE_IDENTITY_TYPE:
                manager.attach_role_policy(
                    role_name=identity_name, policy_arn=policy_arn
                )
            else:
                raise Exception("Failed to validate IAM identity type.")

            output_message = f"Policy was attached to {identity_type}:{identity_name}."
            result_value = True
            status = EXECUTION_STATE_COMPLETED

        except AWSIAMEntityNotFoundException as error:
            output_message = (
                f"Could not attach {policy_name} to {identity_type}: {identity_name}. "
                f"{identity_type} {identity_name} could not be found."
            )
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.exception(error)

    except AWSIAMValidationException as error:
        output_message = f"{error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    except AWSIAMEntityNotFoundException as error:
        output_message = (
            f"Could not attach {policy_name} to {identity_type}: {identity_name}. "
            "Policy could not be found."
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    except Exception as error:
        output_message = (
            f"Error executing action {ATTACH_POLICY_SCRIPT_NAME}. Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
