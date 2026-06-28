# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
