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

from typing import TYPE_CHECKING

from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon.base.action import Action
from TIPCommon.extraction import (
    extract_action_param,
    extract_configuration_param,
)
from TIPCommon.transformation import string_to_multi_value

from okta.core.OktaManager import OktaManager
from okta.core.exceptions import HTTPException
from okta.core.constants import (
    CLEAR_OKTA_USER_SESSION_SCRIPT_NAME,
    INTEGRATION_IDENTIFIER,
    NOT_FOUND_STATUS_CODE,
)
if TYPE_CHECKING:
    from typing import Never, NoReturn


class ClearOktaUserSessionAction(Action):
    """Clear Okta User Session action implementation."""

    def __init__(self) -> None:
        super().__init__(CLEAR_OKTA_USER_SESSION_SCRIPT_NAME)
        self.successful_users: list[str] = []
        self.failed_users: list[str] = []

    def _init_api_clients(self) -> OktaManager:
        api_root = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Api Root",
            is_mandatory=True,
            print_value=True,
        )
        api_token = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Api Token",
        )
        client_id = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Client ID",
        )
        verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Verify SSL",
            input_type=bool,
            is_mandatory=True,
            print_value=True,
        )
        use_oauth_authentication = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Use Oauth Authentication",
            input_type=bool,
            print_value=True,
        )
        key_id = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Key ID",
        )
        private_key = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Private Key",
        )

        return OktaManager(
            api_root=api_root,
            api_token=api_token,
            client_id=client_id,
            use_oauth_authentication=use_oauth_authentication,
            key_id=key_id,
            private_key=private_key,
            verify_ssl=verify_ssl,
            logger=self.logger,
        )

    def _extract_action_parameters(self) -> None:
        self.params.user_ids_or_logins = extract_action_param(
            self.soar_action,
            param_name="User IDs Or Logins",
            print_value=True,
        )
        self.params.run_on_scope = extract_action_param(
            self.soar_action,
            param_name="Also Run On Scope",
            input_type=bool,
            print_value=True,
        )

    def _perform_action(self, _: Never) -> None:
        target_users = self._get_target_users()

        if not target_users:
            self.result_value = True
            self.output_message = "No users were found to clear sessions."
            return

        try:
            self._process_users(target_users)
        finally:
            self._finalize_output()

    def _get_target_users(self) -> list[str]:
        users = set(
            string_to_multi_value(self.params.user_ids_or_logins)
        )

        if not self.params.run_on_scope:
            return list(users)

        for entity in self.soar_action.target_entities:
            if entity.entity_type == EntityTypes.USER:
                users.add(entity.identifier)

        return list(users)

    def _process_users(self, identifiers: list[str]) -> None:
        for identifier in identifiers:
            try:
                user = self.api_client.get_user(identifier)
                if not user:
                    self.failed_users.append(identifier)
                    self.logger.info(
                        f"User with identifier '{identifier}' was not found in Okta."
                    )
                    continue
                user_id = user.get("id")
                self.logger.info(f"Clearing sessions for user: {user_id}")
                self.api_client.clear_user_sessions(user_id)
                self.successful_users.append(identifier)
            except HTTPException as e:
                if e.status_code in NOT_FOUND_STATUS_CODE:
                    self.failed_users.append(identifier)
                    self.logger.error(
                        f"Failed to clear sessions for user {identifier}. Error: {e}"
                    )
                    self.logger.exception(e)
                else:
                    raise

    def _finalize_output(self) -> None:
        if self.successful_users:
            self.result_value = True
            self.output_message += (
                "\nSuccessfully cleared sessions for the following users: "
                f"{', '.join(self.successful_users)}"
            )
        else:
            self.result_value = False

        if self.failed_users:
            self.output_message += (
                "\nThe sessions failed to clear for the following user in Okta: "
                f"{', '.join(set(self.failed_users))}\n"
            )

        if not self.successful_users and not self.failed_users:
            self.result_value = True


def main() -> NoReturn:
    ClearOktaUserSessionAction().run()


if __name__ == "__main__":
    main()
