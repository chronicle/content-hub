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
from .MicrosoftAzureSentinelManager import MicrosoftAzureSentinelManager


CONFIG_PARAMS_MAPPING = {
    "sentinel-check": "Sentinel-Check",
    "sentinelwork01": "sentinelWork01",
}


class MicrosoftAzureSentinelManagerV2(MicrosoftAzureSentinelManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resource = self.map_config(self.resource)
        self.workspace_id = self.map_config(self.workspace_id)
        self.base_url = self._get_base_url()

    @staticmethod
    def map_config(value):
        return CONFIG_PARAMS_MAPPING.get(value, value)
