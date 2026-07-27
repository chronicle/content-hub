# Copyright 2025 Google LLC
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

import copy
from typing import TYPE_CHECKING

from file_utilities.tests.common import (
    ALERTS_FULL_DETAILS_KEY,
    CASE_METADATA_KEY,
    MOCK_DATA,
)

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class MockAttachmentMetadata:
    """Mock attachment metadata exposing to_json interface."""

    def __init__(self, metadata: SingleJson) -> None:
        self._metadata = metadata

    def to_json(self) -> SingleJson:
        return self._metadata


class FileUtilitiesProduct:
    """Product simulator tracking attachment metadata and binary content states."""

    def __init__(self) -> None:
        """Initialize internal simulation state mappings."""
        self._metadata_records: list[SingleJson] = []
        self._blobs: dict[str, bytes] = {}
        self._case_metadata: SingleJson = {}
        self._alerts_full_details: list[SingleJson] = []

    def set_metadata_records(self, records: list[SingleJson]) -> None:
        """Populate internal mock attachment metadata records mapping."""
        self._metadata_records = records

    def set_blob(self, evidence_id: str, content: bytes) -> None:
        """Register binary content payload for targeted attachment evidence."""
        self._blobs[str(evidence_id)] = content

    def set_case_metadata(self, metadata: SingleJson) -> None:
        """Configure mock case metadata return block."""
        self._case_metadata = metadata

    def set_alerts_full_details(self, alerts: list[SingleJson]) -> None:
        """Configure mock alerts full details list configuration."""
        self._alerts_full_details = alerts

    def get_case_metadata(self, case_id: str) -> SingleJson:
        """Retrieve pre-configured simulation case metadata block."""
        if self._case_metadata:
            return self._case_metadata
        default_meta: SingleJson = copy.deepcopy(MOCK_DATA[CASE_METADATA_KEY])
        default_meta["identifier"] = str(case_id)
        return default_meta

    def get_alerts_full_details(self, case_id: str) -> list[SingleJson]:
        """Retrieve pre-configured simulation full details alerts list block."""
        if self._alerts_full_details:
            return self._alerts_full_details
        default_alerts: list[SingleJson] = copy.deepcopy(
            MOCK_DATA[ALERTS_FULL_DETAILS_KEY]
        )
        if default_alerts:
            default_alerts[0]["case_identifier"] = str(case_id)
        return default_alerts

    def get_attachments_metadata(self, case_id: str) -> list[MockAttachmentMetadata]:
        """Simulate SOAR backend get_attachments_metadata query."""
        return [MockAttachmentMetadata(rec) for rec in self._metadata_records]

    def get_attachment_blob(self, evidence_id: str) -> bytes:
        """Simulate attachment binary stream retrieval."""
        key: str = str(evidence_id)
        if key in self._blobs:
            return self._blobs[key]
        raise KeyError(f"Attachment content for evidence ID {key} not found.")
