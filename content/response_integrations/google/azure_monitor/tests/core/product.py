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

import pathlib
import abc
from typing import MutableMapping

from azure_monitor.core.data_models import AzureLogEntry


class AzureMonitor(abc.ABC):

    def __init__(self) -> None:
        self._logs: MutableMapping[str, list[AzureLogEntry]] = {}

    def add_logs(self, query: str, logs: list[AzureLogEntry]) -> None:
        self._logs[query] = logs

    def get_logs(self, query: str) -> list[AzureLogEntry]:
        return self._logs[query]

    def cleanup_logs(self) -> None:
        self._logs.clear()
