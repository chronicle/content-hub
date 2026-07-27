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

import json
import pathlib

from integration_testing.common import create_entity
from TIPCommon.base.action import EntityTypesEnum
from TIPCommon.types import Entity, SingleJson

from misp.core.constants import INTEGRATION_NAME

INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}

MOCK_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: SingleJson = json.loads(MOCK_PATH.read_text(encoding="utf-8")) if MOCK_PATH.exists() else {}

GET_EVENT: SingleJson = MOCK_DATA.get("get_event", {})
ADD_ATTRIBUTE_HOSTNAME: SingleJson = MOCK_DATA.get("add_attribute_hostname", {})
ADD_ATTRIBUTE_IP: SingleJson = MOCK_DATA.get("add_attribute_ip", {})

EVENT_ID: str = "12345"
INVALID_EVENT_ID: str = "99999"
CATEGORY: str = "Network activity"
DISTRIBUTION: str = "Community"
COMMENT: str = "Unit test comment"

HOSTNAME_ENTITY_ID: str = "example.com"
IP_ENTITY_ID: str = "1.2.3.4"

HOSTNAME_ENTITY: Entity = create_entity(
    identifier=HOSTNAME_ENTITY_ID, type_=EntityTypesEnum.HOST_NAME
)

SUCCESS_OUTPUT_MESSAGE: str = (
    "Successfully added the following attributes based on entities to the "
    "event with "
    f"ID {EVENT_ID} in {INTEGRATION_NAME}: \n"
    f" {HOSTNAME_ENTITY_ID} \n"
)

FAILED_OUTPUT_MESSAGE: str = (
    f"Error executing action MISP - Add Attribute. Reason: "
    f"Event with ID {INVALID_EVENT_ID} was not found in {INTEGRATION_NAME}"
)

DEFAULT_PARAMETERS: dict[str, str] = {
    "Event ID": EVENT_ID,
    "Category": CATEGORY,
    "Distribution": DISTRIBUTION,
    "For Intrusion Detection System": "false",
    "Comment": COMMENT,
    "Fallback IP Type": "Source Address",
    "Fallback Email Type": "Source Email Address",
    "Extract Domain": "true",
}

FAILED_PARAMETERS: dict[str, str] = {
    "Event ID": INVALID_EVENT_ID,
    "Category": CATEGORY,
    "Distribution": DISTRIBUTION,
    "For Intrusion Detection System": "false",
    "Comment": COMMENT,
    "Fallback IP Type": "Source Address",
    "Fallback Email Type": "Source Email Address",
    "Extract Domain": "true",
}


class EventIdNotFoundError(Exception):
    """Accessed Event ID cannot be found."""
