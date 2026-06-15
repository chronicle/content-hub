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

"""
Disable User Access in AWS by adding an explicit deny inline policy.
Action works with SOAR User entity type.
"""
from __future__ import annotations

from __future__ import annotations

from TIPCommon.base import EntityTypesEnum, ExecutionState
from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.types import Entity
from ..core import exceptions
from ..core.AWSIAMManager import AWSIAMManager
from ..core.consts import DISABLE_USER_SCRIPT_NAME, INTEGRATION_NAME


class DisableUserAccess(Action):
    """AWS IAM action that change user policy to DisableUserAccessPolicy"""

    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.successful_users = []
        self.failed_users = {}

    def _extract_parameters(self) -> None:
        self.params.aws_access_key_id = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="AWS Access Key ID",
            is_mandatory=True,
            print_value=True,
        )
        self.params.aws_secret_key = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="AWS Secret Key",
            is_mandatory=True,
            remove_whitespaces=False,
        )
        self.params.verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Verify SSL",
            input_type=bool,
            print_value=True,
            default_value=True,
        )

    def _validate_params(self) -> None:
        pass  # No parameters

    def _init_managers(self) -> AWSIAMManager:
        return AWSIAMManager(
            aws_access_key=self.params.aws_access_key_id,
            aws_secret_key=self.params.aws_secret_key,
            verify_ssl=self.params.verify_ssl,
        )

    def _get_entity_types(self) -> list[EntityTypesEnum]:
        return [EntityTypesEnum.USER]

    def _perform_action(
        self, manager: AWSIAMManager = None, current_entity: Entity = None
    ) -> None:
        username = _get_username_from_arn(current_entity.original_identifier)
        manager.disable_user_access(username)
        self.successful_users.append(current_entity.original_identifier)
        self.json_results[current_entity.original_identifier] = (
            "Successfully added to the user the deny "
            'policy "DisableUserAccessPolicy".'
        )

    def _on_entity_failure(
        self,
        _: AWSIAMManager | None = None,
        current_entity: Entity | None = None,
        error: Exception | None = None,
    ) -> None:
        user = current_entity.original_identifier
        error_msg = get_reason_from_error_message(str(error))
        self.failed_users[user] = error_msg
        self.json_results[user] = (
            "Failed to add the user to the deny policy "
            f'"DisableUserAccessPolicy". Reason: {error_msg}'
        )
        if not isinstance(error, exceptions.AWSIAMEntityNotFoundException):
            self.execution_state = ExecutionState.FAILED
            self.result_value = False

    def _finalize_action_on_success(self) -> None:
        self.output_message = ""
        if self.successful_users:
            users = "\n".join(self.successful_users)
            self.output_message += (
                "Successfully added deny policy to the following users in AWS "
                f"IAM:\n{users}\n\n"
            )
        else:
            self.result_value = False
            self.execution_state = ExecutionState.FAILED

        if self.failed_users:
            failed_users = [f"{u} - Reason: {e}" for u, e in self.failed_users.items()]
            users = "\n".join(failed_users)
            self.output_message += (
                "Action wasn't able to add deny policy to the following users "
                f"in AWS IAM:\n{users}"
            )


def _get_username_from_arn(user_full_arn: str) -> str:
    return user_full_arn.split("/")[-1]


def get_reason_from_error_message(error_msg: str) -> str:
    """Extract the reason message from a manager general error message

    Manager error message has the following structure:
    "{Some message}. Reason: {the message from AWS} Response: {full response}"
    This function will extract the Reason part of the message

    Args:
        error_msg: The error message to extract its reason

    Returns:
        The error's reason
    """
    if "Reason: " not in error_msg or "Response: " not in error_msg:
        return error_msg

    return error_msg.split("Reason: ")[-1].split("Response: ")[0].strip()


def main() -> None:
    DisableUserAccess(DISABLE_USER_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
