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


@dataclasses.dataclass(slots=True)
class QuarantineRecord:
    """Represents a quarantined email record."""

    processingserver: str | None
    date: str | None
    subject: str | None
    messageid: str | None
    folder: str | None
    size: int | None
    rcpts: list[str]
    from_address: str | None
    spamscore: int | None
    guid: str | None
    host_ip: str | None
    localguid: str | None

    def to_json(self) -> dict:
        """Convert the record to a standard JSON dict.

        Returns:
            A JSON dictionary.

        """
        return {
            "processingserver": self.processingserver,
            "date": self.date,
            "subject": self.subject,
            "messageid": self.messageid,
            "folder": self.folder,
            "size": self.size,
            "rcpts": self.rcpts,
            "from": self.from_address,
            "spamscore": self.spamscore,
            "guid": self.guid,
            "host_ip": self.host_ip,
            "localguid": self.localguid,
        }
