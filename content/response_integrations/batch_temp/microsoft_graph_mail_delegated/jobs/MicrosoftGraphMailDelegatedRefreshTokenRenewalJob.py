from __future__ import annotations

from typing import NoReturn

from collections.abc import MutableMapping

from TIPCommon.base.job import RefreshTokenRenewalJob, validate_param_csv_to_multi_value

from ..core.constants import (
    INTEGRATION_NAME,
    TOKEN_RENEWAL_SCRIPT_NAME,
)
from ..core.AuthenticationManager import (
    generate_tokens,
    get_authenticated_session,
    SessionAuthenticationParameters,
)
from ..core.exceptions import InvalidParameterException


class RefreshTokenJob(RefreshTokenRenewalJob):
    """Refresh Token Renewal Job to update refresh token periodically."""

    def __init__(self, script_name: str, integration_identifier: str) -> None:
        super().__init__(script_name, integration_identifier)
        self.error_msg = f"{script_name} failed to run because "

    def _get_integration_envs(self) -> str:
        return self.params.integration_environments

    def _get_connector_names(self) -> str:
        return self.params.connector_names

    def _validate_params(self) -> None:
        """Validate the parameters values.

        Raises:
           InvalidParameterException: If both integration environments and connector
                names are not provided.
        """
        self.params.integration_environments = validate_param_csv_to_multi_value(
            param_name="Integration Environments",
            param_csv_value=self.params.integration_environments,
        )
        self.params.connector_names = validate_param_csv_to_multi_value(
            param_name="Connector Names",
            param_csv_value=self.params.connector_names,
        )
        if not self.params.integration_environments and not self.params.connector_names:
            raise InvalidParameterException(
                f"{self.error_msg} both Integration Environments "
                "and Connector Names parameters are not provided."
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
            instance_identifier=instance_settings
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
        """Refreshes the refresh token for a specific connector instance.
        Args:
            instance_identifier (str): The identifier of the connector instance.
                e.g.: "Test_OauthConnector_75098aae-de81-44cc-a807-4843d5ae7ea5"
        """
        connector_settings = self._get_connector_configuration_params(
            connector_identifier=instance_identifier,
        )
        auth_params = self._build_manager_for_instance(
            instance_identifier=connector_settings
        )
        auth_session = get_authenticated_session(auth_params)
        tokens = generate_tokens(auth_session, auth_params)
        self.soar_job.set_connector_parameter(
            connector_instance_identifier=instance_identifier,
            parameter_name="Refresh Token",
            parameter_value=tokens.refresh_token,
        )

    def _build_manager_for_instance(
        self,
        instance_identifier: MutableMapping[str, str],
    ) -> SessionAuthenticationParameters:
        """
        Builds SessionAuthenticationParameters from instance settings.

        Args:
            instance_settings(dict(str, str)):  A dictionary containing the instance
            settings.

        Returns:
            SessionAuthenticationParameters: A SessionAuthenticationParameters object.
        """
        return SessionAuthenticationParameters(
            azure_ad_endpoint=instance_identifier.get("Microsoft Entra ID Endpoint"),
            client_id=instance_identifier.get("Client ID"),
            client_secret=instance_identifier.get("Client Secret Value"),
            tenant=instance_identifier.get("Microsoft Entra ID Directory ID"),
            refresh_token=instance_identifier.get("Refresh Token"),
            verify_ssl=instance_identifier.get("Verify SSL").lower() == "true",
        )


def main() -> NoReturn:
    RefreshTokenJob(TOKEN_RENEWAL_SCRIPT_NAME, INTEGRATION_NAME).start()


if __name__ == "__main__":
    main()
