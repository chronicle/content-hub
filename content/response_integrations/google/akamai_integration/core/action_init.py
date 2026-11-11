from __future__ import annotations

from typing import TYPE_CHECKING
from akamai_integration.core import api_manager
from akamai_integration.core.authentication_manager import AuthenticateSession
from akamai_integration.core.datamodels import IntegrationParameters
from requests import Session
from akamai_integration.core.utils import get_integration_parameters

if TYPE_CHECKING:
    from TIPCommon.types import ChronicleSOAR


def create_api_client(soar_action: ChronicleSOAR) -> api_manager.ApiManager:
    """Create Akamai ApiManager client object.

    Args:
        soar_action (ChronicleSOAR): SiemplifyAction object.

    Returns:
        api_manager.ApiManager: ApiManager object.

    """
    params: IntegrationParameters = get_integration_parameters(soar_action)
    authenticator: AuthenticateSession[IntegrationParameters] = AuthenticateSession()
    session: Session = authenticator.authenticate_session(params)
    api_params: api_manager.ApiParameters = api_manager.ApiParameters(
        api_root=params.api_root,
    )

    return api_manager.ApiManager(
        session=session,
        api_parameters=api_params,
        logger=params.siemplify_logger,
    )
