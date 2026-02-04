"""Base action for Google Chronicle."""

from __future__ import annotations

from abc import ABC

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_configuration_param

from .constants import INTEGRATION_NAME
from .ServiceNowManager import ServiceNowManager

DEFAULT_TABLE = "incident"


class BaseAction(Action, ABC):
    """Base action class."""

    def _init_api_clients(self) -> ServiceNowManager:
        api_root: str = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Api Root",
            print_value=True,
        )
        username: str = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Username",
        )
        password: str = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Password",
        )

        default_incident_table: str = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Incident Table",
            print_value=True,
            default_value=DEFAULT_TABLE,
        )
        verify_ssl: bool = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Verify SSL",
            default_value=True,
            input_type=bool,
        )
        client_id: str = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Client ID",
        )
        client_secret: str = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Client Secret",
        )
        refresh_token: str = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Refresh Token",
        )
        use_oauth: bool = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Use Oauth Authentication",
            default_value=False,
            input_type=bool,
        )

        return ServiceNowManager(
            api_root=api_root,
            username=username,
            password=password,
            default_incident_table=default_incident_table,
            verify_ssl=verify_ssl,
            siemplify_logger=self.logger,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            use_oauth=use_oauth,
        )
