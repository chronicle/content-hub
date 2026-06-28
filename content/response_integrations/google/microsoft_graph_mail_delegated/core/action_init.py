from __future__ import annotations

from TIPCommon.types import ChronicleSOAR

from .utils import get_integration_parameters
from .AuthenticationManager import AuthenticateSession
from . import MicrosoftGraphMailDelegatedManager as api_manager
from .datamodels import IntegrationParameters


def create_api_client(soar_action: ChronicleSOAR) -> api_manager.ApiManager:
    """Create MicrosoftGraphMailDelegated ApiManager client object.

    Args:
        soar_action (ChronicleSOAR): SiemplifyAction object.

    Returns:
        api_manager.ApiManager: ApiManager object.
    """
    params: IntegrationParameters = get_integration_parameters(soar_action)
    authenticator: AuthenticateSession[IntegrationParameters] = AuthenticateSession()
    session = authenticator.authenticate_session(params)
    api_params = api_manager.ApiParameters(
        api_root=params.microsoft_graph_endpoint,
        client_id=params.client_id,
        client_secret=params.secret_id,
        tenant=params.tenant,
        mail_address=params.user_mailbox,
    )

    return api_manager.ApiManager(
        session=session,
        api_parameters=api_params,
        mail_field_source=params.mail_field_source,
        logger=params.siemplify_logger,
    )
