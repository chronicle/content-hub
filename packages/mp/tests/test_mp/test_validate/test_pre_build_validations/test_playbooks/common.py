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

from typing import TYPE_CHECKING

import mp.core.constants
import mp.core.file_utils
from mp.core.data_models.playbooks.meta.metadata import PlaybookMetadata
from mp.core.data_models.playbooks.overview.metadata import Overview
from mp.core.data_models.playbooks.step.metadata import Step
from mp.core.data_models.playbooks.step.step_debug_data import StepDebugData
from mp.core.data_models.playbooks.step.step_parameter import StepParameter
from mp.core.file_utils.playbooks.file_utils import open_display_info

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

    from mp.core.data_models.playbooks.meta.display_info import PlaybookDisplayInfo


def update_single_step(playbook_path: Path, updates: dict) -> None:
    """Update step params and values."""
    step: Step = Step.from_non_built_path(playbook_path)[0]

    new_params = updates.pop("parameters")
    if updates.get("is_automatic"):
        step.is_automatic = updates["is_automatic"]
    for new_param in new_params:
        found = False
        for existing_param in step.parameters:
            if existing_param.name == new_param["name"]:
                existing_param.value = new_param["value"]
                found = True
                break
        if not found:
            step.parameters.append(
                StepParameter(
                    name=new_param["name"],
                    value=new_param["value"],
                    step_id="1",
                    playbook_id="1",
                )
            )
    mp.core.file_utils.save_yaml(
        step.to_non_built(),
        playbook_path / mp.core.constants.STEPS_DIR / f"{step.instance_name}.yaml",
    )


def update_single_overview_roles(playbook_path: Path, new_roles: list[str]) -> None:
    """Update overview roles"""

    overviews: list[Overview] = Overview.from_non_built_path(playbook_path)
    overview: Overview = overviews[0]
    overview.role_names = new_roles

    mp.core.file_utils.save_yaml(
        [overview.to_non_built()], playbook_path / mp.core.constants.OVERVIEWS_FILE_NAME
    )


def ingest_new_steps(playbook_path: Path, steps: list[Step]) -> None:
    for step in steps:
        mp.core.file_utils.save_yaml(
            step.to_non_built(),
            playbook_path / mp.core.constants.STEPS_DIR / f"{step.instance_name}.yaml",
        )


def update_playbook_definition(playbook_path: Path, updates: dict[str, Any]) -> None:
    """Update the playbook definition file with the provided attributes.

    Args:
        playbook_path: The path to the playbook directory.
        updates: A dictionary of attribute names and values to apply.

    """
    def_file: PlaybookMetadata = PlaybookMetadata.from_non_built_path(playbook_path)

    for key, value in updates.items():
        setattr(def_file, key, value)

    mp.core.file_utils.save_yaml(
        def_file.to_non_built(), playbook_path / mp.core.constants.DEFINITION_FILE
    )


def update_display_info(playbook_path: Path, updates: dict) -> None:
    """Update display info."""
    display_info: PlaybookDisplayInfo = open_display_info(playbook_path)
    for key, value in updates.items():
        setattr(display_info, key, value)
    mp.core.file_utils.save_yaml(
        display_info.to_non_built(),
        playbook_path / mp.core.constants.DISPLAY_INFO_FILE_MAME,
    )


def update_step_with_debug_data(
    playbook_path: Path, is_debug_mock_data: bool, has_debug_data: bool
) -> None:
    """Update step with debug data."""
    step: Step = Step.from_non_built_path(playbook_path)[0]
    step.is_debug_mock_data = is_debug_mock_data
    if has_debug_data:
        step.step_debug_data = StepDebugData(
            step_id=step.identifier,
            playbook_id=step.playbook_id,
            creation_time=0,
            modification_time=0,
            result_value=None,
            result_json=None,
            scope_entities_enrichment_data=[],
        )
    else:
        step.step_debug_data = None
    mp.core.file_utils.save_yaml(
        step.to_non_built(),
        playbook_path / mp.core.constants.STEPS_DIR / f"{step.instance_name}.yaml",
    )
