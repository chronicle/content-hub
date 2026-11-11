from __future__ import annotations

from typing import TYPE_CHECKING

from proofpoint_cloud_threat_response.core.data_models import ProofpointIncident, ProofpointMessage

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class ProofpointCTRParser:

    def parse_incidents(self, raw_data: SingleJson) -> list[ProofpointIncident]:
        """Parse incidents."""
        return [
            ProofpointIncident.from_json(item) for item in raw_data.get("incidents", [])
        ]

    def parse_messages(self, raw_data: SingleJson) -> list[ProofpointMessage]:
        """Parse messages."""
        return [
            ProofpointMessage.from_json(item) for item in raw_data.get("messages", [])
        ]
