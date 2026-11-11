from __future__ import annotations

from typing import TYPE_CHECKING

from proofpoint_threat_protection.core.data_models import AllowEntry, BlockEntry

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class ProofpointTPParser:
    def parse_allow_list_entries(self, raw_data: SingleJson) -> list[AllowEntry]:
        """Parse allow list entries."""
        return [AllowEntry.from_json(item) for item in raw_data.get("entries", [])]

    def parse_block_list_entries(self, raw_data: SingleJson) -> list[BlockEntry]:
        """Parse block list entries."""
        return [BlockEntry.from_json(item) for item in raw_data.get("entries", [])]
