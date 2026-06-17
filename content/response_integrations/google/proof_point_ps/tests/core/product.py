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

import dataclasses
from typing import Any


@dataclasses.dataclass(slots=True)
class ProofPointPSProduct:
    """Mock database for Proofpoint PS quarantined messages and actions."""

    records: dict[str, list[dict[str, Any]]] = dataclasses.field(
        default_factory=lambda: {
            "Quarantine": [],
            "Spam": [],
            "Virus": [],
        }
    )
    actions_executed: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    email_contents: dict[str, bytes] = dataclasses.field(default_factory=dict)

    def add_record(
        self, folder: str, record: dict[str, Any], raw_content: bytes | None = None
    ) -> None:
        """Add mock record to specific folder."""
        if folder not in self.records:
            self.records[folder] = []
        self.records[folder].append(record)
        guid = record.get("guid") or record.get("localguid")
        if guid and raw_content:
            self.email_contents[guid] = raw_content

    def search_records(
        self,
        sender: str | None = None,
        recipient: str | None = None,
        subject: str | None = None,
        folder: str | None = None,
        guid: str | None = None,
        msgid: str | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Filter records in-memory."""
        results = []
        folders_to_search = [folder] if folder else self.records.keys()

        for f in folders_to_search:
            for record in self.records.get(f, []):
                if sender and sender != "*":
                    sender_lower = sender.lower()
                    if sender.startswith("@"):
                        if not record.get("from", "").lower().endswith(sender_lower):
                            continue
                    elif record.get("from", "").lower() != sender_lower:
                        continue
                if recipient:
                    recipient_lower = recipient.lower()
                    if recipient.startswith("@"):
                        if not any(
                            r.lower().endswith(recipient_lower)
                            for r in record.get("rcpts", [])
                        ):
                            continue
                    elif not any(
                        r.lower() == recipient_lower for r in record.get("rcpts", [])
                    ):
                        continue
                if subject and record.get("subject") != subject:
                    continue
                if guid and guid not in {
                    record.get("guid"),
                    record.get("localguid"),
                }:
                    continue
                if msgid and record.get("messageid") != msgid:
                    continue
                results.append(record)
        return results

    def execute_action(self, action_data: dict[str, Any]) -> None:
        """Track execution and delete records in-memory if action is 'delete'."""
        self.actions_executed.append(action_data)
        action = action_data.get("action")
        folder = action_data.get("folder")
        localguid = action_data.get("localguid")
        if action == "delete" and folder in self.records and localguid is not None:
            guids_to_delete = (
                {g.strip().lower() for g in localguid.split(",")}
                if isinstance(localguid, str)
                else {g.strip().lower() for g in localguid}
            )
            self.records[folder] = [
                r
                for r in self.records[folder]
                if not {
                    r.get("guid", "").lower(),
                    r.get("localguid", "").lower(),
                }.intersection(guids_to_delete)
            ]

    def get_email_content(self, guid: str) -> bytes:
        """Get raw email content or default bytes."""
        return self.email_contents.get(
            guid,
            b"From: sender@test.com\nTo: recipient@test.com\nSubject: Mock Email\n\nDefault Mock Email Content",
        )
