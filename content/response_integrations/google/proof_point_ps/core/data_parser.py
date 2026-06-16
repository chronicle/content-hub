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

from .data_models import QuarantineRecord


class DataParser:
    """Data parser for ProofPointPS."""

    @staticmethod
    def parse_quarantine_record(data: dict) -> QuarantineRecord:
        """Parse a raw record into QuarantineRecord.

        Args:
            data: The raw JSON dictionary.

        Returns:
            A QuarantineRecord object.

        """
        return QuarantineRecord(
            processingserver=data.get("processingserver"),
            date=data.get("date"),
            subject=data.get("subject"),
            messageid=data.get("messageid"),
            folder=data.get("folder"),
            size=(int(data.get("size")) if data.get("size") is not None else None),
            rcpts=data.get("rcpts") or [],
            from_address=data.get("from"),
            spamscore=(
                int(data.get("spamscore"))
                if data.get("spamscore") is not None
                else None
            ),
            guid=data.get("guid"),
            host_ip=data.get("host_ip"),
            localguid=data.get("localguid"),
        )

    def parse_quarantine_records(self, data: dict) -> list[QuarantineRecord]:
        """Parse a list of raw records.

        Args:
            data: The raw JSON payload containing 'records' key.

        Returns:
            A list of QuarantineRecord objects.

        """
        records = data.get("records") or []
        return [self.parse_quarantine_record(r) for r in records]
