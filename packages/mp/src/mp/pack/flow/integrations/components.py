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

import logging
from typing import TYPE_CHECKING

import questionary
from questionary import Choice

from mp.core import constants

if TYPE_CHECKING:
    import pathlib

logger: logging.Logger = logging.getLogger(__name__)


def discover_components(
    built_dir: pathlib.Path,
) -> tuple[
    list[Choice],
    list[tuple[str, pathlib.Path, pathlib.Path | None]],
    list[tuple[str, pathlib.Path, pathlib.Path | None]],
]:
    """Discover components in the built directory.

    Args:
        built_dir: The built integration directory.

    Returns:
        tuple: (choices, ping_components, other_components)

    """
    components_map: dict[str, tuple[str, str]] = {
        "Action": (constants.OUT_ACTIONS_META_DIR, constants.OUT_ACTION_SCRIPTS_DIR),
        "Connector": (constants.OUT_CONNECTORS_META_DIR, constants.OUT_CONNECTOR_SCRIPTS_DIR),
        "Job": (constants.OUT_JOBS_META_DIR, constants.OUT_JOB_SCRIPTS_DIR),
        "Widget": (constants.OUT_WIDGETS_META_DIR, constants.OUT_WIDGET_SCRIPTS_DIR),
    }

    choices: list[Choice] = []
    ping_components: list[tuple[str, pathlib.Path, pathlib.Path | None]] = []
    other_components: list[tuple[str, pathlib.Path, pathlib.Path | None]] = []

    for comp_type, (meta_dir_name, script_dir_name) in components_map.items():
        meta_dir: pathlib.Path = built_dir / meta_dir_name
        script_dir: pathlib.Path = built_dir / script_dir_name

        if not meta_dir.exists():
            continue

        for meta_file in meta_dir.glob("*"):
            if not meta_file.is_file():
                continue

            name: str = meta_file.stem
            script_file: pathlib.Path | None = None
            if script_dir.exists():
                scripts: list[pathlib.Path] = list(script_dir.glob(f"{name}.*"))
                if scripts:
                    script_file = scripts[0]

            if "Ping" in name:
                ping_components.append((comp_type, meta_file, script_file))
            else:
                other_components.append((comp_type, meta_file, script_file))
                choices.append(Choice(title=f"[{comp_type}] {name}", value=(meta_file, script_file), checked=True))

    return choices, ping_components, other_components


def delete_unselected_components(
    selected_files: set[pathlib.Path],
    other_components: list[tuple[str, pathlib.Path, pathlib.Path | None]],
) -> None:
    """Delete unselected component files.

    Args:
        selected_files: Set of files to keep.
        other_components: List of all other components.

    """
    for _comp_type, meta, script in other_components:
        if meta not in selected_files:
            meta.unlink(missing_ok=True)
            if script and script.exists():
                script.unlink(missing_ok=True)

            logger.info("Removed unselected component: %s", meta.stem)


def interactive_component_selection(built_dir: pathlib.Path) -> None:
    """Prompt user to select components to include in the ZIP.

    Args:
        built_dir: The built integration directory.

    """
    choices, ping_components, other_components = discover_components(built_dir)

    if not choices and not ping_components:
        return

    if not choices:
        return

    selected_values: list[tuple[pathlib.Path, pathlib.Path | None]] | None = questionary.checkbox(
        "Select Actions/Connectors/Jobs/Widgets to include (Hit <Enter> to select all):",
        choices=choices,
    ).ask()

    if not selected_values:
        logger.info("No components selected or cancelled. Including all components.")
        return

    selected_files: set[pathlib.Path] = set()
    for meta, script in selected_values:
        selected_files.add(meta)
        if script:
            selected_files.add(script)

    for _comp_type, meta, script in ping_components:
        selected_files.add(meta)
        if script:
            selected_files.add(script)

    delete_unselected_components(selected_files, other_components)
