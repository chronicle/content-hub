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

from TIPCommon.types import SingleJson

from misp.tests.common import EventIdNotFoundError


class MISPProduct:
    """Mock product representation for MISP server state."""

    def __init__(self) -> None:
        self._events: dict[str, SingleJson] = {}
        self._attributes: list[SingleJson] = []
        self.should_raise_error_on_add: bool = False
        self.should_fail_second_entity: bool = False

    def cleanup_events(self) -> None:
        """Clear all tracked events and attributes."""
        self._events.clear()
        self._attributes.clear()
        self.should_raise_error_on_add = False
        self.should_fail_second_entity = False

    def add_event(self, event_id: str, event_data: SingleJson) -> None:
        """Seed an event into the mock MISP server."""
        self._events[event_id] = event_data

    def get_event(self, event_id: str) -> SingleJson:
        """Retrieve an event by ID or raise."""
        if event_id not in self._events:
            raise EventIdNotFoundError(f"Event ID {event_id} not found on server.")
        return self._events[event_id]

    def add_attribute(self, attribute_data: SingleJson) -> SingleJson:
        """Record a newly added attribute."""
        if self.should_raise_error_on_add:
            raise Exception("Simulated MISP server internal error adding attribute.")

        if self.should_fail_second_entity and len(self._attributes) == 0:
            self._attributes.append({"failed": True})
            raise Exception("Simulated entity processing failure.")

        self._attributes.append(attribute_data)
        return attribute_data

    def get_attributes(self) -> list[SingleJson]:
        """Retrieve all attributes added during the test session."""
        return self._attributes
