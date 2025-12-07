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
    PLAYBOOK_TYPE_TO_DISPLAY_INFO_TYPE,
    BuiltPlaybookDisplayInfo,
    PlaybookDisplayInfo,
    PlaybookType,
)
from mp.core.data_models.playbooks.playbook import (
    BuiltPlaybook,
)
from mp.core.data_models.playbooks.step.metadata import StepType
from mp.core.data_models.release_notes.metadata import ReleaseNote

if TYPE_CHECKING:
    from mp.build_project.playbooks_repo import PlaybooksRepo
    from mp.core.data_models.playbooks.playbook import BuiltPlaybook
    from mp.core.data_models.playbooks.step.metadata import BuiltStep
    from mp.core.data_models.playbooks.step.step_parameter import BuiltStepParameter


class ReleaseNotesDisplayInfo(NamedTuple):
    creation_time: int
    update_time: int
    version: float


def write_playbooks_json(
    commercial_playbooks: PlaybooksRepo, community_playbooks: PlaybooksRepo
) -> None:
    """Generate and writes the playbooks.json file."""
    commercial_playbooks_json: list[BuiltPlaybookDisplayInfo] = _generate_playbooks_display_info(
        commercial_playbooks.repository_base_path, commercial_playbooks.out_dir
    )
    community_playbooks_json: list[BuiltPlaybookDisplayInfo] = _generate_playbooks_display_info(
        community_playbooks.repository_base_path, community_playbooks.out_dir
    )
    out_path: Path = commercial_playbooks.out_dir.parent / mp.core.constants.PLAYBOOKS_JSON_NAME
    playbooks_json: list[BuiltPlaybookDisplayInfo] = (
        commercial_playbooks_json + community_playbooks_json
    )
    with Path.open(out_path, "w") as f:
        json.dump(playbooks_json, f, indent=4)


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

        built_playbook_path: Path | None = _find_built_playbook_in_out_folder(
            non_built_playbook_path.name, out_path
        )
        if not built_playbook_path:
            rich.print(
                f"{non_built_playbook_path.stem} could not be found in the out folder. Skipping..."
            )
            continue

        built_display_info: BuiltPlaybookDisplayInfo = PlaybookDisplayInfo.from_non_built(
            yaml.safe_load(display_info_path.read_text(encoding="utf-8"))
        ).to_built()

        built_playbook: BuiltPlaybook = json.loads(built_playbook_path.read_text(encoding="utf-8"))
        _update_display_info(built_playbook, built_display_info, non_built_playbook_path, out_path)
        res.append(built_display_info)

    return res


def _find_built_playbook_in_out_folder(non_built_playbook_name: str, out_path: Path) -> Path | None:
    built_playbook_name: str = non_built_playbook_name + ".json"
    if (out_path / built_playbook_name).exists():
        return out_path / built_playbook_name
    return None


def _update_display_info(
    built_playbook: BuiltPlaybook,
    built_display_info: BuiltPlaybookDisplayInfo,
    rn_path: Path,
    out_path: Path,
) -> None:
    rn_values: ReleaseNotesDisplayInfo = _extract_display_info_from_rn(rn_path)

    built_display_info["Identifier"] = built_playbook["Definition"]["Identifier"]
    built_display_info["CreateTime"] = rn_values.creation_time
    built_display_info["UpdateTime"] = rn_values.update_time
    built_display_info["Version"] = rn_values.version
    built_display_info["Type"] = PLAYBOOK_TYPE_TO_DISPLAY_INFO_TYPE[
        built_playbook["Definition"]["PlaybookType"]
    ]
    built_display_info["Integrations"] = _extract_integrations(built_playbook, out_path)
    built_display_info["DependentPlaybookIds"] = (
        _extract_block_identifier(built_playbook)
        if built_playbook.get("Definition").get("PlaybookType") == PlaybookType.PLAYBOOK.value
        else []
    )


def _extract_integrations(
    built_playbook: BuiltPlaybook, parent_folder: Path | None = None
) -> list[str]:
    result: set[str] = set()
    steps: list[BuiltStep] = built_playbook["Definition"]["Steps"]
    for step in steps:
        step_type: int = step.get("Type")
        if step_type == StepType.BLOCK.value:
            _extract_from_block(step, parent_folder, result)
        else:
            _extract_from_step(step, result)

    return list(result)


def _extract_from_step(step: BuiltStep, result: set[str]) -> None:
    integration_name: str = step.get("Integration")
    if integration_name not in {"Flow", None}:
        result.add(integration_name)


def _extract_from_block(step: BuiltStep, parent_folder: Path | None, result: set[str]) -> None:
    step_parameters: list[BuiltStepParameter] = step.get("Parameters")
    for param in step_parameters:
        if param.get("Name") == "NestedWorkflowIdentifier":
            temp = _extract_integrations_from_nested_block(param.get("Value"), parent_folder)
            result.update(temp)


def _extract_integrations_from_nested_block(block_identifier: str, base_folder: Path) -> set[str]:
    result: set[str] = set()
    for file in base_folder.iterdir():
        if file.is_dir():
            continue

        with Path.open(file) as block_file:
            block_json: dict = json.load(block_file)

        if not _is_specific_block(block_json, block_identifier):
            continue

        steps: list[dict] = block_json.get("Definition").get("Steps")
        for step in steps:
            integration_name: str = step.get("Integration")
            if integration_name not in {"Flow", None}:
                result.add(integration_name)

        break

    return result


def _is_specific_block(block_json: dict, block_identifier: str) -> bool:
    return (
        block_json.get("Definition").get("PlaybookType") == PlaybookType.BLOCK.value
        and block_json.get("Definition").get("Identifier") == block_identifier
    )


def _extract_block_identifier(built_playbook: BuiltPlaybook) -> list[str]:
    result: set[str] = set()
    steps: list[BuiltStep] = built_playbook.get("Definition").get("Steps")
    for step in steps:
        step_type: int = step.get("Type")
        if step_type != StepType.BLOCK.value:
            continue
        step_parameters: list[BuiltStepParameter] = step.get("Parameters")
        for param in step_parameters:
            if param.get("Name") == "NestedWorkflowIdentifier":
                result.add(param.get("Value"))
                break
    return list(result)


def _extract_display_info_from_rn(rn_path: Path) -> ReleaseNotesDisplayInfo:
    release_notes: list[ReleaseNote] = ReleaseNote.from_non_built_path(rn_path)
    latest_version: float = max(float(rn.version) for rn in release_notes)
    creation_time: int = min(rn.publish_time for rn in release_notes)
    update_time: int = max(rn.publish_time for rn in release_notes)
    return ReleaseNotesDisplayInfo(creation_time, update_time, latest_version)
