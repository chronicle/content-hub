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

from ..core.AWSIAMManager import AWSIAMManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import INTEGRATION_NAME, REMOVE_USER_FROM_GROUP_SCRIPT_NAME
from ..core.exceptions import AWSIAMLimitExceededException, AWSIAMEntityNotFoundException
from ..core.utils import load_csv_to_list


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {REMOVE_USER_FROM_GROUP_SCRIPT_NAME}"
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

    group_name = extract_action_param(
        siemplify, param_name="Group Name", is_mandatory=True, print_value=True
    )
    user_names = extract_action_param(
        siemplify, param_name="User Name", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    not_found_entities = ""
    output_message = ""
    failed_users = []
    exceeding_limit_usernames = []
    successful_users = []
    result_value = False

    try:
        user_names = load_csv_to_list(user_names, param_name="User Name")
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

        for user_name in user_names:
            try:
                siemplify.LOGGER.info(
                    f"Removing user {user_name} from group {group_name}"
                )
                manager.remove_user_from_group(
                    group_name=group_name, user_name=user_name
                )
                successful_users.append(user_name)

            except AWSIAMEntityNotFoundException as error:
                siemplify.LOGGER.error(
                    f"Specified group {group_name} or user {user_name} doesn't exist."
                )
                siemplify.LOGGER.exception(error)
                # This exception catches both non existing User/Group. Saving error message as output message
                not_found_entities += f" {error}\n"

            except AWSIAMLimitExceededException as error:
                siemplify.LOGGER.error(
                    f"Could not remove {user_name} from {group_name} because it "
                    "attempted to create resources beyond the current AWS account "
                    "limits."
                )
                siemplify.LOGGER.exception(error)
                exceeding_limit_usernames.append(user_name)

            except Exception as error:
                siemplify.LOGGER.error(
                    f"Could not remove {user_name} from {group_name}"
                )
                siemplify.LOGGER.exception(error)
                failed_users.append(user_name)

        if successful_users:
            siemplify.LOGGER.info(
                f"{', '.join(successful_users)} has been removed from group: "
                f"{group_name}"
            )
            output_message += (
                f"{', '.join(successful_users)} has been removed from group: "
                f"{group_name}\n"
            )
            result_value = True

        if exceeding_limit_usernames:
            output_message += (
                f"Could not remove {', '.join(exceeding_limit_usernames)} from "
                f"{group_name} because it attempted to create resources beyond the "
                "current AWS account limits.\n"
            )

        if not_found_entities:
            output_message += not_found_entities

        if failed_users:
            output_message += (
                f"Could not remove {', '.join(failed_users)} from {group_name}.\n"
            )

    except Exception as error:
        siemplify.LOGGER.error(
            f"Error executing action '{REMOVE_USER_FROM_GROUP_SCRIPT_NAME}'. "
            f"Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action '{REMOVE_USER_FROM_GROUP_SCRIPT_NAME}'. "
            f"Reason: {error}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
