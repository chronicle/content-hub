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
import json
import pathlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class MockEntity:
    """Universal mock entity supporting SDK attribute lookup."""

    def __init__(
        self,
        identifier: str,
        entity_type: str = "ADDRESS",
        additional_properties: SingleJson | None = None,
    ) -> None:
        """Initialize universal mock entity.

        Args:
            identifier: Unique string identifier for the entity.
            entity_type: Type designation string for the entity.
            additional_properties: Optional custom properties mapping.
        """
        self.identifier = identifier
        self.entity_type = entity_type
        self.additional_properties = additional_properties or {}

    def to_dict(self) -> SingleJson:
        """Convert mock entity into standard dictionary format.

        Returns:
            Dictionary payload representing the mock entity attributes.
        """
        return {
            "identifier": self.identifier,
            "entity_type": self.entity_type,
            "additional_properties": self.additional_properties,
        }


CASE_METADATA_KEY: str = "case_metadata"
ALERTS_FULL_DETAILS_KEY: str = "alerts_full_details"
ATTACHMENT_METADATA_1_KEY: str = "attachment_metadata_1"
ATTACHMENT_METADATA_CASE_KEY: str = "attachment_metadata_case_scope"

EXPECTED_EVIDENCE_NAME: str = "Siemplify Picture"
EXPECTED_CASE_EVIDENCE_NAME: str = "Case Level Document"
EXPECTED_OUTPUT_MESSAGE: str = "1 attachment(s) found"
EXPECTED_BASE64_BLOB_LENGTH: int = 24
SCOPE_ALERT_PARAM: str = "Alert"
SCOPE_CASE_PARAM: str = "Case"
MOCK_CASE_IDENTIFIER: str = "11"

INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
MOCK_DATA_PATH: pathlib.Path = INTEGRATION_PATH / "tests" / "mock_data.json"
with open(MOCK_DATA_PATH, "r") as f:
    MOCK_DATA: SingleJson = json.load(f)

ALERT_1_CONTEXT: SingleJson = MOCK_DATA["alert_1_context"]

ACTION_ALERT_SCOPE_PARAMS: SingleJson = MOCK_DATA["action_alert_scope_parameters"]
ACTION_ALERT_SCOPE_CONTEXT: SingleJson = copy.deepcopy(ALERT_1_CONTEXT)

ACTION_CASE_SCOPE_PARAMS: SingleJson = MOCK_DATA["action_case_scope_parameters"]
ACTION_CASE_SCOPE_CONTEXT: SingleJson = copy.deepcopy(ALERT_1_CONTEXT)

ACTION_ALERT_SCOPE_ENTITIES: list[MockEntity] = [
    MockEntity(identifier="9069-4D83-BBB1-D37C0D494A36"),
]
