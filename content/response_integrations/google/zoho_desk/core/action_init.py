from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction

from zoho_desk.core.UtilsManager import get_integration_parameters
from zoho_desk.core.AuthManager import AuthenticateSession
from zoho_desk.core.ZohoDeskApiManager import ZohoDeskApiClient
from zoho_desk.core.datamodels import IntegrationParameters


def create_api_client(soar_action: SiemplifyAction) -> ZohoDeskApiClient:
    params: IntegrationParameters = get_integration_parameters(soar_action)
    authenticator: AuthenticateSession[IntegrationParameters] = AuthenticateSession()
    authenticator.authenticate_session(params)
    return ZohoDeskApiClient(authenticator.session, params)
