"""Base action for Google Chronicle."""
from __future__ import annotations

from abc import ABC

from ..core.api_client import ChronicleInvestigationApiClient
from ..core.authenticator import Authenticator
from ..core.data_models import ApiParameters, SessionAuthenticationParameters
from TIPCommon.base.action import Action
from ..core.utils import build_integration_params


class BaseAction(Action, ABC):
    """Base action class."""

    def _init_api_clients(self) -> ChronicleInvestigationApiClient:
        """Prepare API client."""
        integration_params = build_integration_params(self.soar_action)
        auth_params = SessionAuthenticationParameters.from_integration_params(
            chronicle_soar=self.soar_action,
            integration_params=integration_params,
        )
        authenticator = Authenticator()
        authenticator.authenticate_session(auth_params)
        api_params = ApiParameters.from_integration_params(integration_params)

        return ChronicleInvestigationApiClient(
            api_params=api_params,
            authenticated_session=authenticator.session,
            logger=self.logger,
        )
