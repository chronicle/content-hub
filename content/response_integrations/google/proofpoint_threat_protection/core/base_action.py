from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

from TIPCommon.base.action import Action

from proofpoint_threat_protection.core.api_client import ApiParameters, ProofpointThreatProtectionApiClient
from proofpoint_threat_protection.core.auth import (
    AuthenticatedSession,
    build_auth_params,
    SessionAuthenticationParameters,
)
from proofpoint_threat_protection.core.constants import AUTH_URL

if TYPE_CHECKING:
    import requests


class ProofpointThreatProtectionAction(Action, ABC):
    """Base action class."""

    def _init_api_clients(self) -> ProofpointThreatProtectionApiClient:
        """Prepare API client"""
        auth_params = build_auth_params(self.soar_action)
        authenticator: AuthenticatedSession = AuthenticatedSession()
        auth_params_for_session = SessionAuthenticationParameters(
            client_id=auth_params.client_id,
            client_secret=auth_params.client_secret,
            auth_url=AUTH_URL,
            verify_ssl=auth_params.verify_ssl,
        )
        authenticator.authenticate_session(auth_params_for_session)
        authenticated_session: AuthenticatedSession = authenticator.session

        api_params: ApiParameters = ApiParameters(
            api_root=auth_params.api_root,
            cluster_id=auth_params.cluster_id,
        )

        return ProofpointThreatProtectionApiClient(
            authenticated_session=authenticated_session,
            configuration=api_params,
            logger=self.logger,
        )

    @property
    def result_value(self) -> bool:
        return self._result_value

    @result_value.setter
    def result_value(self, value: bool) -> None:
        self._result_value = value
