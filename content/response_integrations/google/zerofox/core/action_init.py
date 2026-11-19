from __future__ import annotations

from TIPCommon.types import ChronicleSOAR

from zerofox.core.utils import get_integration_parameters
from zerofox.core.AuthenticationManager import AuthenticateSession
from zerofox.core import ZerofoxManager as api_manager
from zerofox.core.datamodels import IntegrationParameters


def create_api_client(soar_action: ChronicleSOAR) -> api_manager.ApiManager:
    """Create Zerofox ApiManager client object.

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
        api_token=params.api_token,
    )

    return api_manager.ApiManager(
        session=session,
        api_parameters=api_params,
        logger=params.siemplify_logger,
    )
