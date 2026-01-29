"""Base action class for Silverfort integration."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

from TIPCommon.base.action import Action  # type: ignore[import-not-found]

from .auth import (
    AuthenticatedSession,
    SessionAuthenticationParameters,
    build_auth_params,
    get_app_credentials,
)
from .constants import ApiType
from .policy_client import PolicyApiClient, PolicyApiParameters
from .risk_client import RiskApiClient, RiskApiParameters
from .service_account_client import ServiceAccountApiClient, ServiceAccountApiParameters

if TYPE_CHECKING:
    import requests

    from .data_models import IntegrationParameters


class SilverfortAction(Action, ABC):
    """Base action class for Silverfort integration."""

    def _init_api_clients(self) -> None:
        """Initialize API clients placeholder.

        Note: This returns None as Silverfort requires different clients
        for different APIs. Use specific initialization methods instead.
        """
        return None

    def _get_integration_params(self) -> IntegrationParameters:
        """Get integration parameters from SOAR configuration.

        Returns:
            IntegrationParameters with configuration values.
        """
        if not hasattr(self, "_integration_params"):
            self._integration_params = build_auth_params(self.soar_action)
        return self._integration_params

    def _get_authenticated_session(
        self,
        api_type: ApiType | None = None,
    ) -> requests.Session:
        """Get an authenticated session for API requests.

        Args:
            api_type: Type of API to authenticate for. If None, only uses External API Key.

        Returns:
            Authenticated requests Session.
        """
        params = self._get_integration_params()

        app_credentials = None
        if api_type:
            app_credentials = get_app_credentials(params, api_type)

        session_params = SessionAuthenticationParameters(
            api_root=params.api_root,
            external_api_key=params.external_api_key,
            verify_ssl=params.verify_ssl,
            app_credentials=app_credentials,
            api_type=api_type,
        )

        authenticator = AuthenticatedSession()
        authenticator.authenticate_session(session_params)
        return authenticator.session

    def _get_risk_client(self) -> RiskApiClient:
        """Get a Risk API client.

        Returns:
            Configured RiskApiClient instance.
        """
        params = self._get_integration_params()
        session = self._get_authenticated_session(ApiType.RISK)

        return RiskApiClient(
            authenticated_session=session,
            configuration=RiskApiParameters(api_root=params.api_root),
            logger=self.logger,
        )

    def _get_service_account_client(self) -> ServiceAccountApiClient:
        """Get a Service Account API client.

        Returns:
            Configured ServiceAccountApiClient instance.
        """
        params = self._get_integration_params()
        session = self._get_authenticated_session(ApiType.SERVICE_ACCOUNTS)

        return ServiceAccountApiClient(
            authenticated_session=session,
            configuration=ServiceAccountApiParameters(api_root=params.api_root),
            logger=self.logger,
        )

    def _get_policy_client(self) -> PolicyApiClient:
        """Get a Policy API client.

        Returns:
            Configured PolicyApiClient instance.
        """
        params = self._get_integration_params()
        session = self._get_authenticated_session(ApiType.POLICIES)

        return PolicyApiClient(
            authenticated_session=session,
            configuration=PolicyApiParameters(api_root=params.api_root),
            logger=self.logger,
        )

    @property
    def result_value(self) -> bool:
        """Get the result value."""
        return self._result_value

    @result_value.setter
    def result_value(self, value: bool) -> None:
        """Set the result value."""
        self._result_value = value
