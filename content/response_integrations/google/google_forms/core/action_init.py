from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction

from google_forms.core.datamodels import IntegrationParameters
from google_forms.core.GoogleFormsAuth import build_auth_manager_params, GoogleFormsAuthManager
from google_forms.core.GoogleFormsManager import GoogleFormsManager


def create_api_client(soar_action: SiemplifyAction) -> GoogleFormsManager:
    auth_manager_params = build_auth_manager_params(soar_action)
    auth_manager = GoogleFormsAuthManager(auth_manager_params)

    return GoogleFormsManager(
        auth_manager.prepare_session(),
        IntegrationParameters(siemplify_logger=soar_action.LOGGER),
    )
