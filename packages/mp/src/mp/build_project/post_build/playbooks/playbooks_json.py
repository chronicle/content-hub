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
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import rich
import yaml

import mp.core.constants
from mp.core.data_models.playbooks.meta.display_info import (
    BuiltPlaybookDisplayInfo,
    PlaybookDisplayInfo,
)
from mp.core.data_models.release_notes.metadata import ReleaseNote

if TYPE_CHECKING:
    from mp.build_project.playbooks_repo import Playbooks

BLOCK_TYPE: int = 5


class ReleaseNotesValues(NamedTuple):
    creation_time: int | None
    update_time: int | None
    version: float | None


def write_playbooks_json(commercial_playbooks: Playbooks, community_playbooks: Playbooks) -> None:
    """Generate and writes the playbooks.json file."""
    commercial_playbooks_json_data: list[BuiltPlaybookDisplayInfo] = (
        _generate_playbooks_display_info(
            commercial_playbooks.repository_base_path, commercial_playbooks.out_dir
        )
    )
    community_playbooks_json_data: list[BuiltPlaybookDisplayInfo] = (
        _generate_playbooks_display_info(
            community_playbooks.repository_base_path, community_playbooks.out_dir
        )
    )
    out_path: Path = commercial_playbooks.out_dir.parent / mp.core.constants.PLAYBOOKS_JSON_NAME
    playbooks_json_data: list[BuiltPlaybookDisplayInfo] = (
        commercial_playbooks_json_data + community_playbooks_json_data
    )
    with Path.open(out_path, "w") as f:
        json.dump(playbooks_json_data, f, indent=4)


def _generate_playbooks_display_info(
    repo_path: Path, out_path: Path
) -> list[BuiltPlaybookDisplayInfo]:
    res: list[BuiltPlaybookDisplayInfo] = []
    for non_built_playbook_path in repo_path.iterdir():
        if not non_built_playbook_path.is_dir():
            continue

        display_info_path: Path = non_built_playbook_path / mp.core.constants.DISPLAY_INFO_FILE_MAME
        if not display_info_path.exists():
            continue

        built_display_info: BuiltPlaybookDisplayInfo = PlaybookDisplayInfo.from_non_built(
            yaml.safe_load(display_info_path.read_text(encoding="utf-8"))
        ).to_built()
        built_playbook_path: Path | None = _find_built_playbook_in_out_folder(
            non_built_playbook_path.name, out_path
        )
        if not built_playbook_path:
            rich.print(
                f"{non_built_playbook_path.stem} could not be found in the out folder. Skipping..."
            )
            continue

        built_playbook: dict = json.loads(built_playbook_path.read_text(encoding="utf-8"))
        built_display_info: BuiltPlaybookDisplayInfo = _parse_built_playbook_json(
            built_playbook, built_display_info, non_built_playbook_path, out_path
        )
        res.append(built_display_info)

    return res


def _find_built_playbook_in_out_folder(non_built_playbook_name: str, out_path: Path) -> Path | None:
    built_playbook_name: str = non_built_playbook_name + ".json"
    if (out_path / built_playbook_name).exists():
        return out_path / built_playbook_name
    return None


def _parse_built_playbook_json(
    built_playbook: dict,
    built_display_info: BuiltPlaybookDisplayInfo,
    rn_path: Path,
    out_path: Path,
) -> BuiltPlaybookDisplayInfo:
    rn_values: ReleaseNotesValues = _extract_info_from_rn(rn_path)

    built_display_info["Identifier"] = built_playbook.get("Definition").get("Identifier")
    built_display_info["CreateTime"] = rn_values.creation_time
    built_display_info["UpdateTime"] = rn_values.update_time
    built_display_info["Version"] = rn_values.version
    built_display_info["Integrations"] = _extract_integrations(built_playbook, out_path)
    built_display_info["DependentPlaybookIds"] = (
        _extract_block_identifier(built_playbook)
        if built_playbook.get("Definition").get("PlaybookType") == 0
        else []
    )
    return built_display_info


def _extract_integrations(built_playbook: dict, parent_folder: Path | None = None) -> list[str]:
    result: set[str] = set()
    steps: list[dict] = built_playbook.get("Definition").get("Steps")
    for step in steps:
        step_type: int = step.get("Type")
        if step_type != BLOCK_TYPE:
            integration_name: str = step.get("Integration")
            if integration_name not in {"Flow", None}:
                result.add(integration_name)
        else:
            step_parameters: list[dict] = step.get("Parameters")
            for param in step_parameters:
                if param.get("Name") == "NestedWorkflowIdentifier":
                    temp = _extract_integrations_from_nested_block(
                        param.get("Value"), parent_folder
                    )
                    result.update(temp)

    return list(result)


def _extract_integrations_from_nested_block(block_identifier: str, base_folder: Path) -> set[str]:
    result: set[str] = set()
    for file in base_folder.iterdir():
        if file.is_dir():
            continue
        found: bool = False
        with Path.open(file) as block_file:
            block_json: dict = json.load(block_file)
            if (
                block_json.get("Definition").get("PlaybookType") == 0
                or block_json.get("Definition").get("Identifier") != block_identifier
            ):
                continue
            found = True
            steps: list[dict] = block_json.get("Definition").get("Steps")
            for step in steps:
                integration_name: str = step.get("Integration")
                if integration_name not in {"Flow", None}:
                    result.add(integration_name)
        if found:
            break

    return result


def _extract_block_identifier(built_playbook: dict) -> list[str]:
    result: set[str] = set()
    steps: list[dict] = built_playbook.get("Definition").get("Steps")
    for step in steps:
        step_type: int = step.get("Type")
        if step_type != BLOCK_TYPE:
            continue
        step_parameters: list[dict] = step.get("Parameters")
        for param in step_parameters:
            if param.get("Name") == "NestedWorkflowIdentifier":
                result.add(param.get("Value"))
                break
    return list(result)


def _extract_info_from_rn(rn_path: Path) -> ReleaseNotesValues:
    release_notes: list[ReleaseNote] = ReleaseNote.from_non_built_path(rn_path)
    latest_version: float = max(float(rn.version) for rn in release_notes)
    creation_time: int = min(rn.publish_time for rn in release_notes)
    update_time: int = max(rn.publish_time for rn in release_notes)
    return ReleaseNotesValues(creation_time, update_time, latest_version)
