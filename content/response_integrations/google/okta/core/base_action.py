from __future__ import annotations

from abc import ABC

from okta.core.OktaManager import OktaManager
from okta.core.auth_manager import AuthManager, build_auth_manager_params
from TIPCommon.base.action import Action


class BaseAction(Action, ABC):
    """Base action class."""

    def _init_api_clients(self) -> OktaManager:
        """Prepare API Client"""
        auth_manager_params = build_auth_manager_params(self.soar_action)
        auth_manager = AuthManager(auth_manager_params, self.logger)

        return OktaManager(
            api_root=auth_manager.api_root,
            api_token=auth_manager.api_token,
            client_id=auth_manager.client_id,
            use_oauth_authentication=auth_manager.use_oauth_authentication,
            key_id=auth_manager.key_id,
            private_key=auth_manager.private_key,
            session=auth_manager.prepare_session(),
            verify_ssl=auth_manager.verify_ssl,
            logger=self.logger,
        )
