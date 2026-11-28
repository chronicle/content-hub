from __future__ import annotations

from abc import ABC

from TIPCommon.base.action import Action

from .api_client import ApiParameters, DarkEyeApiClient
from .auth import build_integration_params, create_session


class DarkEyeAction(Action, ABC):
    """Base action class."""

    def _init_api_clients(self) -> DarkEyeApiClient:
        """Prepare the API client."""
        params = build_integration_params(self.soar_action)
        return DarkEyeApiClient(
            authenticated_session=create_session(params.verify_ssl),
            configuration=ApiParameters(
                haveibeenransom_api_key=params.haveibeenransom_api_key,
                breach_house_api_key=params.breach_house_api_key,
            ),
            logger=self.logger,
        )
