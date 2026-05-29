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
from .datamodels import Incident
from .constants import SIEM_TO_SYMANTEC_PRIORITY


class SymantecATPParser:
    @staticmethod
    def build_incident(incident_data):
        return Incident(incident_data, **incident_data)

    @staticmethod
    def convert_siem_priorities_to_symantec(priorities):
        return [
            SIEM_TO_SYMANTEC_PRIORITY.get(priority.upper()) for priority in priorities
        ]
