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
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon.extraction import extract_action_param
from TIPCommon.base.action import Action
from TIPCommon.transformation import (
    convert_dict_to_json_result_dict,
)
from TIPCommon.validation import ParameterValidator

from ..core.action_init import create_api_client
from ..core.consts import REVOKE_USER_SESSIONS_SCRIPT_NAME
from ..core.exceptions import GSuiteNotFoundException
from ..core.GSuiteManager import GSuiteManager


SUPPORTED_ENTITIES = [EntityTypes.USER.casefold()]

SUCCESS_MESSAGE = (
    "Successfully signed out the following users using Google Workspace: {}\n"
)
NOT_FOUND_MESSAGE = (
    "Action wasn’t able to sign out the following users using Google Workspace: {}"
)
NO_USERS_FOUND_MESSAGE = (
    "None of the provided users were found in Google Workspace."
)


class RevokeUserSessions(Action):
    def __init__(self) -> None:
        super().__init__(REVOKE_USER_SESSIONS_SCRIPT_NAME)
        self.output_message = NO_USERS_FOUND_MESSAGE
        self.result_value = False
        self.json_results = {}

    def _extract_action_parameters(self) -> None:
        self.params.user_email_addresses = extract_action_param(
            self.soar_action,
            param_name="User Email Addresses",
            print_value=True,
        )

    def _validate_params(self) -> None:
        """Validate action input params."""
        validator = ParameterValidator(self.soar_action)
        user_emails = validator.validate_csv(
            "User Email Addresses",
            csv_string=self.params.user_email_addresses
        )
        for email in user_emails:
            validator.validate_email(
                "User Email Addresses",
                email
            )

        self.params.user_emails = {
            entity.identifier.lower()
            for entity in self.soar_action.target_entities
            if entity.entity_type.casefold() in SUPPORTED_ENTITIES
        }
        for email in self.params.user_emails:
            validator.validate_email(
                "Entities",
                email
            )

        self.params.user_emails.update(
            email.lower() for email in user_emails
        )


    def _init_api_clients(self) -> GSuiteManager:
        return create_api_client(self.soar_action)

    def _perform_action(self, _: None) -> None:
        failed_users = []
        json_results = {}

        for primary_email in self.params.user_emails:
            try:
                self.api_client.sign_out_user(primary_email)
                json_results[primary_email] = {"Status": "done"}
            except GSuiteNotFoundException as e:
                failed_users.append(primary_email)
                json_results[primary_email] = {
                    "Status": "not found",
                    "ErrorMessage": str(e),
                }

        self.json_results = convert_dict_to_json_result_dict(json_results)
        successful_users = self.params.user_emails.difference(failed_users)
        if not successful_users:
            return

        self.result_value = True
        self.output_message = SUCCESS_MESSAGE.format(",".join(successful_users))
        if failed_users:
            self.output_message += NOT_FOUND_MESSAGE.format(",".join(failed_users))


def main() -> None:
    RevokeUserSessions().run()


if __name__ == "__main__":
    main()
