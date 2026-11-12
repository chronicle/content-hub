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

from typing import NoReturn

from collections.abc import MutableMapping

from TIPCommon.base.job import RefreshTokenRenewalJob, validate_param_csv_to_multi_value
from TIPCommon.transformation import string_to_multi_value

from ..core.constants import (
    INTEGRATION_IDENTIFIER,
    TOKEN_RENEWAL_SCRIPT_NAME,
)
from ..core.auth import (
    generate_tokens,
    get_authenticated_session,
    SessionAuthenticationParameters,
)
from ..core.exceptions import (
    AzureApiInvalidParameterError,
    AzureApiJobNotSupportedError,
)


class RefreshTokenJob(RefreshTokenRenewalJob):
    """Refresh Token Renewal Job to update refresh token periodically."""

    def __init__(self, script_name: str, integration_identifier: str) -> None:
        super().__init__(script_name, integration_identifier)
        self.error_msg = f"{script_name} failed to run because "

    def _get_integration_envs(self) -> str:
        return self.params.integration_environments

    def _get_connector_names(self) -> str:
        """Get the names of connectors to refresh the token."""

    def _validate_params(self) -> None:
        """Validate the parameters values.

        Raises:
           AzureApiInvalidParameterError: If both integration environments and connector
                names are not provided.
        """
        self.params.integration_environments = validate_param_csv_to_multi_value(
            param_name="Integration Environments",
            param_csv_value=self.params.integration_environments,
        )
        if not self.params.integration_environments:
            raise AzureApiInvalidParameterError(
                f"{self.error_msg} Integration Environments parameter "
                "is not provided."
            )

    def _refresh_integration_token(
        self,
        instance_identifier: str,
    ) -> None:
        """Refreshes the refresh token for a specific integration instance.

        Args:
            instance_identifier (str): The identifier of the integration instance.
                e.g.: "ce0027a2-2b53-4cce-ad08-430df6d002f3"
        """
        instance_settings = self._get_integration_configuration_params(
            integration_instance_identifier=instance_identifier,
        )
        auth_params = self._build_manager_for_instance(
            instance_settings=instance_settings
        )
        auth_session = get_authenticated_session(auth_params)
        tokens = generate_tokens(auth_session, auth_params)

        self.soar_job.set_configuration_property(
            integration_instance_identifier=instance_identifier,
            property_name="Refresh Token",
            property_value=tokens.refresh_token,
        )

    def _refresh_connector_token(
        self,
        instance_identifier: str,
    ) -> None:
        """Renew refresh token and set it in connector's configuration."""

    def _build_manager_for_instance(
        self,
        instance_settings: MutableMapping[str, str],
    ) -> SessionAuthenticationParameters:
        """
        Builds SessionAuthenticationParameters from instance settings.

        Args:
            instance_settings(dict(str, str)):  A dictionary containing the instance
            settings.

        Returns:
            SessionAuthenticationParameters: A SessionAuthenticationParameters object.
        """
        refresh_token: str = instance_settings.get("Refresh Token", "")
        if not refresh_token:
            raise AzureApiJobNotSupportedError(
                "Refresh Token is not configured for the instance. "
                'Configure Integration/Connector with "Refresh Token" parameter to '
                "utilize this job."
            )
        return SessionAuthenticationParameters(
            login_api_root=instance_settings.get("Microsoft Login API Root"),
            api_root=instance_settings.get("Microsoft Graph API Root"),
            client_id=instance_settings.get("Client ID"),
            client_secret=instance_settings.get("Client Secret"),
            tenant_id=instance_settings.get("Tenant ID"),
            refresh_token=instance_settings.get("Refresh Token"),
            verify_ssl=instance_settings.get("Verify SSL").lower() == "true",
            scopes=string_to_multi_value(instance_settings.get("Scopes")),
            redirect_url=instance_settings.get("Redirect URL"),
        )


def main() -> NoReturn:
    RefreshTokenJob(TOKEN_RENEWAL_SCRIPT_NAME, INTEGRATION_IDENTIFIER).start()


if __name__ == "__main__":
    main()
