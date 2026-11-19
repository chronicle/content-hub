from __future__ import annotations

from TIPCommon.base.interfaces import Authable
from zoho_desk.core.datamodels import IntegrationParameters


class AuthenticateSession(Authable[IntegrationParameters]):

    def authenticate_session(self, params: IntegrationParameters) -> None:
        self.session.verify = params.verify_ssl
        self.session.headers.update(
            {"Authorization": f"Zoho-oauthtoken {params.oauth_token}"}
        )
