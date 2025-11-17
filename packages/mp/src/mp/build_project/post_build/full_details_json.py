"""Utility to write full integration details to a JSON file.

This module provides a function to serialize and save the complete
information about an integration into a structured JSON file within a
specified destination directory.
"""

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

import json
from typing import TYPE_CHECKING

import rich

import mp.core.constants

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.data_models.integration import BuiltFullDetails


def write_full_details(full_details: BuiltFullDetails, destination: Path) -> None:
    """Write a full details file in `destination` containing `full_details` content.

    Args:
        full_details: The full details content to write
        destination: The path to write the content to

    """
    rich.print("Writing full details file to integration")
    details_json_name: str = mp.core.constants.INTEGRATION_FULL_DETAILS_FILE.format(
        full_details["Identifier"],
    )
    details_json_path: Path = destination / details_json_name
    details_json_path.write_text(
        json.dumps(full_details, indent=4, sort_keys=True),
        encoding="utf-8",
    )
