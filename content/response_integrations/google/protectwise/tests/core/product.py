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
import abc

from protectwise.tests.common import EventIdNotFoundError
from TIPCommon.types import SingleJson


class ProtectwiseProduct(abc.ABC):
    """Mock product representation for Protectwise server state."""

    def __init__(self) -> None:
        super().__init__()
        self._events: SingleJson = {}
        self._pcaps: dict[str, bytes] = {}
        self.should_return_empty_events: bool = False
        self.should_raise_error: bool = False

    def cleanup(self) -> None:
        """Clear all tracked simulation state."""
        self._events.clear()
        self._pcaps.clear()
        self.should_return_empty_events = False
        self.should_raise_error = False

    def seed_events(self, events_payload: SingleJson) -> None:
        """Seed the GET events response payload."""
        self._events = dict(events_payload)

    def seed_pcap(self, event_id: str, pcap_bytes: bytes) -> None:
        """Seed PCAP binary file bytes for a given event ID."""
        self._pcaps[event_id] = pcap_bytes

    def get_events(self) -> SingleJson:
        """Retrieve seeded events or raise server fault."""
        if self.should_raise_error:
            raise Exception("Simulated Protectwise API Gateway Timeout.")
        if self.should_return_empty_events:
            return {"events": []}
        return self._events

    def download_pcap(self, event_id: str) -> bytes:
        """Retrieve binary PCAP content by event ID."""
        if event_id not in self._pcaps:
            raise EventIdNotFoundError(f"PCAP for event {event_id} not found.")
        return self._pcaps[event_id]
