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
import pathlib
import abc

import dataclasses

from service_desk_plus.core.datamodels import WorkOrder

@dataclasses.dataclass
class ServiceDeskPlus(abc.ABC):

    def __init__(self):
        super().__init__()
        self._requests: list[WorkOrder] = []
        self._add_request_mock: WorkOrder | None = None

    @property
    def requests(self) -> list[WorkOrder]:
        return self._requests

    def add_request(self, request: WorkOrder) -> None:
        self._requests.append(request)

    def get_requests(self) -> list[WorkOrder]:
        return self._requests

    def set_add_request_mock(self, request: WorkOrder) -> None:
        self._add_request_mock = request

    def get_add_request_mock(self) -> WorkOrder | None:
        return self._add_request_mock
