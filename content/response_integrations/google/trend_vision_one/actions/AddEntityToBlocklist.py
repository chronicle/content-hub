# Copyright 2026 Google LLC
# ruff: file-ignore[invalid-module-name]
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

from typing import TYPE_CHECKING, NoReturn

from ..core.base_action import BaseBlocklistAction
from ..core.constants import ADD_ENTITY_TO_BLOCKLIST_SCRIPT_NAME

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

    from ..core import datamodels


class AddEntityToBlocklist(BaseBlocklistAction):
    """Action to add supported Chronicle entities and indicators to the Trend Vision One blocklist."""

    SCRIPT_NAME = ADD_ENTITY_TO_BLOCKLIST_SCRIPT_NAME
    ACTION_DISPLAY_NAME = "Add Entity To Blocklist"
    ACTION_VERB = "added"
    ACTION_INFINITIVE = "add"
    ACTION_PREPOSITION = "to"
    RESULT_JSON_KEY = "added"
    ENRICHMENT_VALUE = True
    INCLUDE_DESCRIPTION = True

    def _submit_chunk(
        self, chunk: list[SingleJson]
    ) -> list[datamodels.BlocklistResponse]:
        """Submit suspicious objects to be added to the Trend Vision One blocklist.

        Args:
            chunk: Batch of suspicious object payload dictionaries.

        Returns:
            List of parsed BlocklistResponse objects.

        """
        return self.api_client.add_entities_to_blocklist(chunk)


def main() -> NoReturn:
    """Entry point for Add Entity To Blocklist action execution."""
    AddEntityToBlocklist().run()


if __name__ == "__main__":
    main()
