from __future__ import annotations
from dataclasses import dataclass

from TIPCommon.types import ChronicleSOAR

from .MicrosoftGraphSecurityManager import (
    MicrosoftGraphSecurityManager,
    MicrosoftGraphSecurityManagerV2,
)


@dataclass(slots=True)
class GraphSecurityManagerConfig:
    client_id: str
    secret_id: str
    certificate_path: str
    certificate_password: str
    tenant: str
    verify_ssl: str
    chronicle_soar: ChronicleSOAR


def init_graph_security_manager(
    config: GraphSecurityManagerConfig,
    use_v2_api: bool,
) -> MicrosoftGraphSecurityManager | MicrosoftGraphSecurityManagerV2:
    """Returns the correct Microsoft Graph Security Manager based on API version.
    Args:
        config(GraphSecurityManagerConfig): Configuration params.
        use_v2_api(bool): If true, alerts V2 API is used.

    Returns:
        MicrosoftGraphSecurityManager | MicrosoftGraphSecurityManagerV2: Microsoft Graph
        Security Manager.
    """
    manager_class = (
        MicrosoftGraphSecurityManagerV2 if use_v2_api else MicrosoftGraphSecurityManager
    )
    return manager_class(
        client_id=config.client_id,
        client_secret=config.secret_id,
        certificate_path=config.certificate_path,
        certificate_password=config.certificate_password,
        tenant=config.tenant,
        verify_ssl=config.verify_ssl,
        siemplify=config.chronicle_soar,
    )
