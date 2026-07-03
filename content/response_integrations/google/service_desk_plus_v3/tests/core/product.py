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
from ...core.datamodels import Request

@dataclasses.dataclass
class ServiceDeskPlusV3(abc.ABC):
    def __init__(self):
        super().__init__()
        self._requests: list[Request] = []

    @property
    def requests(self) -> list[Request]:
        return self._requests

    def add_request(self, request: Request) -> None:
        self._requests.append(request)

    def get_requests(self) -> list[Request]:
        return self._requests
