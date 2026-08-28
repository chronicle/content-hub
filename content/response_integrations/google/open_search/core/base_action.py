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
from typing import TYPE_CHECKING

from .auth import build_auth_params
from .os_client import OpenSearchManager
from TIPCommon.base.action import Action

if TYPE_CHECKING:
    from .data_models import IntegrationParameters


class BaseAction(Action, ABC):
    """Base action class for OpenSearch integration."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _init_api_clients(self) -> OpenSearchManager:
        """
        Initializes the OpenSearchManager.
        This method is called by the Action's run method and its return value
        is used to set the api_client property.
        """
        integration_parameters: IntegrationParameters = build_auth_params(
            self.soar_action
        )
        return OpenSearchManager(
            integration_parameters=integration_parameters,
            logger=self.logger,
        )

    @property
    def result_value(self) -> bool:
        return self._result_value

    @result_value.setter
    def result_value(self, value: bool) -> None:
        self._result_value = value
