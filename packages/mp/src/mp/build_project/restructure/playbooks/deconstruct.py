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

import dataclasses
from typing import TYPE_CHECKING

import rich

import mp.core.constants
import mp.core.file_utils
from mp.core.data_models.common.widget.data import WidgetType

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.data_models.common.release_notes.metadata import NonBuiltReleaseNote
    from mp.core.data_models.playbooks.meta.display_info import NonBuiltPlaybookDisplayInfo
    from mp.core.data_models.playbooks.meta.metadata import NonBuiltPlaybookMetadata
    from mp.core.data_models.playbooks.overview.metadata import NonBuiltOverview
    from mp.core.data_models.playbooks.playbook import NonBuiltPlaybook, Playbook
    from mp.core.data_models.playbooks.step.metadata import NonBuiltStep
    from mp.core.data_models.playbooks.trigger.metadata import NonBuiltTrigger
    from mp.core.data_models.playbooks.widget.metadata import NonBuiltPlaybookWidgetMetadata


@dataclasses.dataclass(slots=True, frozen=True)
class PlaybookDeconstructor:
    playbook: Playbook
    out_path: Path

    def deconstruct(self) -> None:
        """Deconstruct a playbook's code to its "out" path."""
        non_built_playbook: NonBuiltPlaybook = self.playbook.to_non_built()

        self._create_steps_files(non_built_playbook["steps"])
        self._create_trigger_file(non_built_playbook["trigger"])
        self._create_widgets_files(non_built_playbook["widgets"])
        self._create_overviews_file(non_built_playbook["overviews"])
        self._create_display_info_file(non_built_playbook["display_info"])
        self._create_definition_file(non_built_playbook["meta_data"])
        self._create_release_notes_file(non_built_playbook["release_notes"])

    def _create_steps_files(self, non_built_steps: list[NonBuiltStep]) -> None:
        rich.print("Creating steps files")
        step_dir: Path = self.out_path / mp.core.constants.STEPS_DIR
        step_dir.mkdir(exist_ok=True)

        for step in non_built_steps:
            step_path: Path = step_dir / f"{step['instance_name']}.yaml"
            mp.core.file_utils.save_yaml(step, step_path)

    def _create_trigger_file(self, non_built_trigger: NonBuiltTrigger) -> None:
        rich.print("Creating trigger file")
        trigger_path: Path = self.out_path / mp.core.constants.TRIGGER_FILE_NAME
        mp.core.file_utils.save_yaml(non_built_trigger, trigger_path)

    def _create_overviews_file(self, non_built_overviews: list[NonBuiltOverview]) -> None:
        rich.print("Creating overviews file")
        overviews_path: Path = self.out_path / mp.core.constants.OVERVIEWS_FILE_NAME
        mp.core.file_utils.save_yaml(non_built_overviews, overviews_path)

    def _create_display_info_file(
        self, non_built_display_info: NonBuiltPlaybookDisplayInfo
    ) -> None:
        rich.print("Creating display info file")
        display_info_path: Path = self.out_path / mp.core.constants.DISPLAY_INFO_FILE_MAME
        mp.core.file_utils.save_yaml(non_built_display_info, display_info_path)

    def _create_definition_file(self, non_built_meta_data: NonBuiltPlaybookMetadata) -> None:
        rich.print("Creating definition file")
        definition_path: Path = self.out_path / mp.core.constants.DEFINITION_FILE
        mp.core.file_utils.save_yaml(non_built_meta_data, definition_path)

    def _create_release_notes_file(
        self, non_built_release_notes: list[NonBuiltReleaseNote]
    ) -> None:
        rich.print("Creating release notes file")
        release_notes_path: Path = self.out_path / mp.core.constants.RELEASE_NOTES_FILE
        mp.core.file_utils.save_yaml(non_built_release_notes, release_notes_path)

    def _create_widgets_files(
        self, non_built_widgets: list[NonBuiltPlaybookWidgetMetadata]
    ) -> None:
        rich.print("Creating widgets files")
        widgets_path: Path = self.out_path / mp.core.constants.WIDGETS_DIR
        widgets_path.mkdir(exist_ok=True)

        for w in non_built_widgets:
            widget_path: Path = widgets_path / f"{w['title']}{mp.core.constants.DEF_FILE_SUFFIX}"
            mp.core.file_utils.save_yaml(w, widget_path)

        for w in self.playbook.widgets:
            widget_path: Path = widgets_path / f"{w.title}.{mp.core.constants.HTML_SUFFIX}"
            html_content: str = w.data_definition.html_content if w.type is WidgetType.HTML else ""
            if html_content:
                widget_path.write_text(html_content)
