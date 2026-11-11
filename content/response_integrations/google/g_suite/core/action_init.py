from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction

from g_suite.core.datamodels import IntegrationParameters
from g_suite.core.GSuiteAuth import build_auth_manager
from g_suite.core.GSuiteManager import GSuiteManager


def create_api_client(soar_action: SiemplifyAction) -> GSuiteManager:
    auth_manager = build_auth_manager(soar_action)

    return GSuiteManager(
        auth_manager.prepare_session(),
        IntegrationParameters(siemplify_logger=soar_action.LOGGER),
    )
