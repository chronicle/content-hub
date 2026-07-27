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
from .datamodels import *


class TalosParser:
    def build_base_object(self, raw_data):
        return BaseModel(raw_data=raw_data)

    def build_whois_report_object(self, raw_data):
        return WhoisReport(raw_data=raw_data)

    def build_reputation_object(self, raw_data, reputation_type):
        return Reputation(raw_data=raw_data, reputation_type=reputation_type)
