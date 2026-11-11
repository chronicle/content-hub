from __future__ import annotations
from TIPCommon.types import ChronicleSOAR

from extrahop.core.AuthenticationManager import AuthenticateSession
from extrahop.core.UtilsManager import get_integration_parameters
from extrahop.core import ExtrahopManager as api_manager
from extrahop.core.datamodels import IntegrationParameters


def create_api_client(soar_action: ChronicleSOAR) -> api_manager.ExtrahopManager:
    """Create Extrahop ApiManager client object.

    Args:
        soar_action (ChronicleSOAR): SiemplifyAction object.

    Returns:
        api_manager.ApiManager: ApiManager object.
    """
    params: IntegrationParameters = get_integration_parameters(soar_action)
    authenticator: AuthenticateSession[IntegrationParameters] = AuthenticateSession()
    session = authenticator.authenticate_session(params)
    api_params = api_manager.ApiParameters(
        api_root=params.api_root,
        client_id=params.client_id,
        client_secret=params.client_secret,
    )

    return api_manager.ExtrahopManager(
        session=session,
        api_parameters=api_params,
    )
