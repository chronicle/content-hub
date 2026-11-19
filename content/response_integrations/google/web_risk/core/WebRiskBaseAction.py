from __future__ import annotations
from abc import ABC

from TIPCommon.base.action import Action
from TIPCommon.base.interfaces import ApiClient
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.types import Contains

from web_risk.core.WebRiskAuthManager import build_auth_manager_params, AuthManager
from web_risk.core.WebRiskApiManager import ApiManager
from web_risk.core.WebRiskConstants import INTEGRATION_IDENTIFIER


class BaseAction(Action, ABC):
    def _init_api_clients(self) -> Contains[ApiClient]:
        auth_params = build_auth_manager_params(self.soar_action)
        auth_manager = AuthManager(auth_params)
        return ApiManager(
            api_root=self.params.api_root,
            session=auth_manager.prepare_session(),
            project_id=auth_manager.project_id,
            logger=self.logger
        )

    def _extract_action_parameters(self) -> None:
        self.params.api_root = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="API Root",
            print_value=True
        )
        self._extract_parameters()

    def _extract_parameters(self) -> None:
        """Extract action specific parameters."""
