from __future__ import annotations

from abc import ABC

from google_threat_intelligence.core.api_manager import ApiManager
from google_threat_intelligence.core.auth_manager import AuthManager, build_auth_manager_params
from TIPCommon.base.action import Action


class BaseAction(Action, ABC):
    """Base action class."""

    def _init_api_clients(self) -> ApiManager:
        """Prepare API client"""
        auth_manager_params = build_auth_manager_params(self.soar_action)
        auth_manager = AuthManager(auth_manager_params, self.logger)

        return ApiManager(
            api_root=auth_manager.api_root,
            session=auth_manager.prepare_session(),
            asm_project_name=auth_manager.asm_project_name,
            logger=self.logger,
        )
