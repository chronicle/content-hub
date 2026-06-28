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

from TIPCommon.base.action import Action

from sysdig_secure.core.SysdigSecureAuthManager import AuthManager, build_auth_manager_params
from sysdig_secure.core.SysdigSecureManager import ApiManager


class BaseAction(Action, ABC):
    """Base action class."""

    def _init_api_clients(
            self,
    ) -> ApiManager:
        """Prepare API client"""
        auth_manager_params = build_auth_manager_params(self.soar_action)
        auth_manager = AuthManager(auth_manager_params, self.logger)

        return ApiManager(
            api_root=auth_manager.api_root,
            session=auth_manager.prepare_session(),
            logger=self.logger
        )
