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

from collections.abc import Collection, Iterable, MutableMapping

from ...core.SplunkParser import SplunkParser
from ...core.datamodels import NotableEvent
from ...tests.common import EventIdNotFoundError


class Splunk(abc.ABC):

    def __init__(self) -> None:
        self._notable_events: MutableMapping[str, NotableEvent] = {}

    def list_notable_events(self) -> Collection[NotableEvent]:
        return self._notable_events.values()

    def get_notable_events(self, event_ids: Iterable[str]) -> Collection[NotableEvent]:
        return [self.get_notable_event(event_id) for event_id in event_ids]

    def get_notable_event(self, event_id: str) -> NotableEvent:
        if event_id not in self._notable_events:
            raise EventIdNotFoundError(f"Mock Error: Invalid Event ID {event_id}")

        return self._notable_events[event_id]

    def add_notable_events(self, events: Iterable[NotableEvent]) -> None:
        for event in events:
            self.add_notable_event(event)

    def add_notable_event(self, event: NotableEvent) -> None:
        if event.event_id in self._notable_events:
            raise EventIdNotFoundError(f"Mock Error: Invalid Event ID {event.event_id}")

        self._notable_events[event.event_id] = event

    def update_notable_event(
        self,
        event_id: str,
        status: str | None = None,
        urgency: str | None = None,
        new_owner: str | None = None,
        comments: str | Iterable[str] | None = None,
        disposition: str | None = None,
    ) -> None:
        """Update a notable event in Splunk"""
        if event_id not in self._notable_events:
            raise EventIdNotFoundError(f"Mock Error: Invalid Event ID {event_id}")

        if status is not None:
            self._notable_events[event_id].status = status

        if urgency is not None:
            self._notable_events[event_id].urgency = urgency

        if new_owner is not None:
            self._notable_events[event_id].raw_data["owner"] = new_owner

        if comments is not None:
            if not self._notable_events[event_id].comments:
                self._notable_events[event_id].comments = []

            self._notable_events[event_id].comments.extend(
                SplunkParser().build_comments_list(comments)
            )

        if disposition is not None:
            self._notable_events[event_id].raw_data["disposition"] = disposition
