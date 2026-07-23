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
from typing import MutableMapping, List
from ...core.datamodels import (
    Campaign,
    Event,
    ThreatForensic,
)


class ProofPointTAP(abc.ABC):

    def __init__(self) -> None:
        self._campaigns: MutableMapping[str, Campaign] = {}
        self._events: MutableMapping[str, Event] = {}
        self._threat_forensics: MutableMapping[str, List[ThreatForensic]] = {}

    def add_campaign(self, campaign: Campaign) -> None:
        self._campaigns = campaign

    def get_campaign(self) -> Campaign:
        return self._campaigns

    def add_threat_forensics(self, threat_forensics: ThreatForensic) -> None:
        self._threat_forensics = threat_forensics

    def get_threat_forensics(self) -> ThreatForensic:
        return self._threat_forensics

    def add_event(self, event: Event) -> None:
        self._events = event

    def get_events(self) -> Event:
        return self._events
