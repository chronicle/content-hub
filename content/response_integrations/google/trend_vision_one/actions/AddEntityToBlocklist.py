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

import sys

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.constants import ADD_ENTITY_TO_BLOCKLIST_SCRIPT_NAME
from ..core.TrendVisionOneManager import TrendVisionOneManager
from ..core.UtilsManager import (
    SUPPORTED_BLOCKLIST_ENTITY_TYPES,
    execute_blocklist_action,
    query_blocklist_operation_status,
    start_blocklist_operation,
)

SUPPORTED_ENTITY_TYPES = SUPPORTED_BLOCKLIST_ENTITY_TYPES


def start_operation(
    siemplify: SiemplifyAction,
    manager: TrendVisionOneManager,
    action_start_time: int,
    suitable_entities: list,
    result_data: dict,
) -> tuple[str, bool, int]:
    """Start operation for adding entities to blocklist."""
    return start_blocklist_operation(
        siemplify=siemplify,
        manager=manager,
        action_start_time=action_start_time,
        suitable_entities=suitable_entities,
        result_data=result_data,
        is_add=True,
    )


def query_operation_status(
    siemplify: SiemplifyAction,
    manager: TrendVisionOneManager,
    result_data: dict,
    action_start_time: int,
) -> tuple[str, bool, int]:
    """Query operation status for adding entities to blocklist."""
    return query_blocklist_operation_status(
        siemplify=siemplify,
        manager=manager,
        result_data=result_data,
        action_start_time=action_start_time,
        is_add=True,
    )


@output_handler
def main(is_first_run: bool) -> None:
    execute_blocklist_action(
        is_first_run=is_first_run,
        is_add=True,
        script_name=ADD_ENTITY_TO_BLOCKLIST_SCRIPT_NAME,
        action_display_name="Add Entity To Blocklist",
    )


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
