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

from TIPCommon.base.action import Action

from palo_alto_cortex_xdr.core.action_init import create_api_client
from palo_alto_cortex_xdr.core.XDRManager import XDRManager

if TYPE_CHECKING:
    import requests


class BaseAction(Action, ABC):
    """Base action class."""

    def _init_api_clients(self) -> XDRManager:
        """Prepare API client"""
        return create_api_client(self.soar_action)

    @property
    def result_value(self) -> bool:
        return self._result_value

    @result_value.setter
    def result_value(self, value: bool) -> None:
        self._result_value = value
