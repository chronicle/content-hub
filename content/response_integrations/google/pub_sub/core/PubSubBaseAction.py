from __future__ import annotations

from abc import ABC

from TIPCommon.base.action import Action

from pub_sub.core.PubSubAuthManager import AuthManager, build_auth_manager_params
from pub_sub.core.PubSubManager import ApiManager


class BaseAction(Action, ABC):
    """This is a base action class."""

    def _init_api_clients(
            self,
    ) -> ApiManager:
        """Prepare API client."""
        auth_manager_params = build_auth_manager_params(self.soar_action)
        auth_manager = AuthManager(auth_manager_params, self.logger)

        return ApiManager(
            auth_manager.prepare_client(),
            logger=self.logger
        )
