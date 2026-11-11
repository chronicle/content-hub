from __future__ import annotations
from TIPCommon.types import ChronicleSOAR

from proof_point_tap.core.AuthenticationManager import AuthenticateSession
from proof_point_tap.core.utils import get_integration_parameters
from proof_point_tap.core import ProofPointTapManager as api_manager
from proof_point_tap.core.datamodels import IntegrationParameters


def create_api_client(soar_action: ChronicleSOAR) -> api_manager.ProofPointTapManager:
    """Create ProofPointTap ApiManager client object.

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
    )

    return api_manager.ProofPointTapManager(
        session=session,
        api_parameters=api_params,
    )
