from __future__ import annotations

from abc import ABC

from TIPCommon.base.action import Action

from .api.api_client import ApiParameters, SignalSciencesApiClient
from .auth import AuthenticatedSession, SessionAuthenticationParameters, build_auth_params


class SignalSciencesAction(Action, ABC):
    """Base action class for SignalSciences."""

    def _init_api_clients(self) -> SignalSciencesApiClient:
        """Prepare API client"""
        auth_params = build_auth_params(self.soar_action)
        authenticator = AuthenticatedSession()
        session_params = SessionAuthenticationParameters(
            email=auth_params.email,
            api_token=auth_params.api_token,
            verify_ssl=auth_params.verify_ssl,
        )
        authenticator.authenticate_session(session_params)

        return SignalSciencesApiClient(
            authenticated_session=authenticator.session,
            configuration=ApiParameters(
                api_root=auth_params.api_root,
                corp_name=auth_params.corp_name
            ),
            logger=self.logger,
        )
