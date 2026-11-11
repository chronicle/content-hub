from __future__ import annotations

from typing import Any

import google.auth.credentials
import google_auth_httplib2
import httplib2
from TIPCommon.base.action import Action
from google_cloud_armor.core import api_utils
from google_cloud_armor.core import constants
from google_cloud_armor.core import AuthenticationManager as auth_manager
from google_cloud_armor.core import GoogleCloudArmorManager as api_manager


class Ping(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.service_name: str
        self.output_message = (
            f"Successfully connected to the {constants.PROVIDER_NAME} service with the "
            "provided connection parameters!"
        )
        self.error_output_message = (
            f"Failed to connect to the {constants.PROVIDER_NAME} service!"
        )

    def _extract_parameters(self) -> None:
        integration_params = api_utils.get_integration_params(self.soar_action)
        self.params.session_auth_params = integration_params.auth_params
        self.params.api_params = integration_params.api_params

    def _validate_params(self) -> None:
        api_utils.validate_configuration_params(
            soar_action=self.soar_action,
            auth_params=self.params.session_auth_params,
            api_params=self.params.api_params,
        )

    def _init_managers(self) -> api_manager.ApiManager:
        credentials = self._get_authentication_credentials()
        session = self._get_authenticated_session(credentials=credentials)
        return api_manager.ApiManager(
            session=session, api_parameters=self.params.api_params, logger=self.logger
        )

    def _get_authentication_credentials(self) -> google.auth.credentials.Credentials:
        return auth_manager.get_authentication_credentials_or_raise_error(
            session_parameters=self.params.session_auth_params
        )

    def _get_authenticated_session(
        self, credentials
    ) -> httplib2.Http | google_auth_httplib2.AuthorizedHttp:
        return auth_manager.get_authenticated_session(
            credentials=credentials,
            verify_ssl=self.params.session_auth_params.verify_ssl,
        )

    def _perform_action(self, manager: Any | None = None, _=None) -> None:
        manager.test_connectivity()


def main() -> None:
    Ping(constants.PING_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
