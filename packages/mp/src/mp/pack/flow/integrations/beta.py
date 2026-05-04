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
import logging
import re
import shutil
from typing import TYPE_CHECKING, Any

from mp.core import constants

if TYPE_CHECKING:
    import pathlib

logger: logging.Logger = logging.getLogger(__name__)


def apply_beta_modifications(built_dir: pathlib.Path, old_id: str, beta_name: str, version: str | None) -> None:
    """Modify built integration files for a custom beta identifier.

    Args:
        built_dir: The built integration directory.
        old_id: The original identifier.
        beta_name: The new beta identifier.
        version: The version number.

    """
    new_id: str = beta_name

    # 1. Rename and update the main .def file
    old_def_path: pathlib.Path = built_dir / constants.INTEGRATION_DEF_FILE.format(old_id)
    new_def_path: pathlib.Path = built_dir / constants.INTEGRATION_DEF_FILE.format(new_id)

    if old_def_path.exists():
        shutil.move(old_def_path, new_def_path)

        with new_def_path.open("r+", encoding="utf-8") as f:
            def_data: dict[str, Any] = json.load(f)
            def_data["Identifier"] = new_id

            # Update Display Name
            ver_str = str(def_data.get("Version", version or ""))
            def_data["DisplayName"] = f"{split_camel_case(new_id)} {ver_str}".strip()
            def_data["IsCustom"] = True

            # Update IntegrationProperties
            for prop in def_data.get("IntegrationProperties", []):
                prop["IntegrationIdentifier"] = new_id

            f.seek(0)
            json.dump(def_data, f, indent=4)
            f.truncate()

    # 2. Update component definitions
    component_dirs: list[tuple[str, bool]] = [
        (constants.OUT_ACTIONS_META_DIR, False),
        (constants.OUT_CONNECTORS_META_DIR, True),  # Is Connector
        (constants.OUT_JOBS_META_DIR, False),
        (constants.OUT_WIDGETS_META_DIR, False),
    ]

    for dir_name, is_connector in component_dirs:
        meta_dir: pathlib.Path = built_dir / dir_name
        if meta_dir.exists():
            for file_path in meta_dir.glob("*"):
                if file_path.is_file():
                    update_component_def(file_path, new_id, is_connector=is_connector)


def update_component_def(file_path: pathlib.Path, new_id: str, *, is_connector: bool) -> None:
    """Update a single component definition file with the new identifier.

    Args:
        file_path: The path to the component definition file.
        new_id: The new identifier.
        is_connector: True if the component is a connector.

    """
    try:
        with file_path.open("r+", encoding="utf-8") as f:
            data = json.load(f)

            if "Integration" in data:
                data["Integration"] = new_id
            if "IntegrationIdentifier" in data:
                data["IntegrationIdentifier"] = new_id

            if is_connector and "Name" in data and not data["Name"].startswith(f"{new_id}-"):
                data["Name"] = f"{new_id}-{data['Name']}"

            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()
    except (OSError, json.JSONDecodeError):
        logger.exception("Failed to update component def %s", file_path)


def split_camel_case(text: str) -> str:
    """Split the CamelCase string with spaces.

    Args:
        text: The string to split.

    Returns:
        str: The split string.

    """
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", text)
