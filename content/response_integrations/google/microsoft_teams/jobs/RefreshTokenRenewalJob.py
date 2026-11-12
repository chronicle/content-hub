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

from TIPCommon.base.job import RefreshTokenRenewalJob, validate_param_csv_to_multi_value

from ..core.MicrosoftConstants import (
    DEFAULT_API_ROOT,
    INTEGRATION_NAME,
    DEFAULT_LOGIN_API_ROOT,
    TOKEN_RENEWAL_SCRIPT_NAME,
)
from ..core.MicrosoftManager import MicrosoftTeamsManager
from ..core.MicrosoftExceptions import MicrosoftTeamsManagerError


class RefreshTokenJob(RefreshTokenRenewalJob):
    """Refresh Token Renewal Job to update refresh token periodically."""

    def __init__(self) -> None:
        super().__init__(TOKEN_RENEWAL_SCRIPT_NAME, INTEGRATION_NAME)
        self.error_msg = f"{TOKEN_RENEWAL_SCRIPT_NAME} failed to run because "

    def _get_integration_envs(self) -> str:
        """Gets the names of environments to refresh token for.

        Returns:
            str: Environment names.
        """
        return self.params.integration_environments

    def _get_connector_names(self) -> None:
        """Get the names of connectors to refresh the token."""

    def _validate_params(self) -> None:
        """Validate the parameters values.

        Raises:
            MicrosoftTeamsManagerError: Exception if integration environment is not
                provided.
        """
        self.params.integration_environments = validate_param_csv_to_multi_value(
            param_name="Integration Environments",
            param_csv_value=self.params.integration_environments,
        )

        if not self.params.integration_environments:
            raise MicrosoftTeamsManagerError(
                f"{self.error_msg} Integration Environments parameter "
                "is not provided."
            )

    def _refresh_integration_token(
        self,
        instance_identifier: str,
    ) -> None:
        """Renew refresh token and set it in integration's configuration.

        Args:
            instance_identifier (str): integration instance identifier.
                e.g.: "ce0027a2-2b53-4cce-ad08-430df6d002f3"

        Returns:
            None
        """
        refresh_token = self.api_client.new_refresh_token
        self.soar_job.set_configuration_property(
            integration_instance_identifier=instance_identifier,
            property_name="Refresh Token",
            property_value=refresh_token,
        )

    def _refresh_connector_token(
        self,
        instance_identifier: str,
    ) -> None:
        """Renew refresh token and set it in connector's configuration."""

    def _build_manager_for_instance(
        self,
        instance_settings: dict[str, str],
    ) -> MicrosoftTeamsManager:
        """Build Manager object to get the refresh token for integration instances.

        Args:
            instance_settings (dict[str, str]): instance configuration settings.

        Returns:
            MicrosoftTeamsManager: exception while creating
                MicrosoftTeamsManager object.
        """
        return MicrosoftTeamsManager(
            client_id=instance_settings.get("Client ID"),
            client_secret=instance_settings.get("Secret ID"),
            tenant=instance_settings.get("Tenant"),
            refresh_token=instance_settings.get("Refresh Token"),
            redirect_url=instance_settings.get("Redirect URL"),
            api_root=instance_settings.get("API Root", DEFAULT_API_ROOT),
            login_api_root=instance_settings.get(
                "Login API Root",
                DEFAULT_LOGIN_API_ROOT
            ),
        )


def main() -> None:
    RefreshTokenJob().start()


if __name__ == "__main__":
    main()
