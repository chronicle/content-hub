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

import yaml

import mp.core.constants
from mp.core.data_models.widget.data import WidgetType

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.data_models.playbooks.meta.display_info import NonBuiltPlaybookDisplayInfo
    from mp.core.data_models.playbooks.meta.metadata import NonBuiltPlaybookMetadata
    from mp.core.data_models.playbooks.overview.metadata import NonBuiltOverview
    from mp.core.data_models.playbooks.playbook import NonBuiltPlaybook, Playbook
    from mp.core.data_models.playbooks.step.metadata import NonBuiltStep
    from mp.core.data_models.playbooks.trigger.metadata import NonBuiltTrigger
    from mp.core.data_models.playbooks.widget.metadata import NonBuiltPlaybookWidgetMetadata
    from mp.core.data_models.release_notes.metadata import NonBuiltReleaseNote


@dataclasses.dataclass(slots=True, frozen=True)
class DeconstructPlaybook:
    playbook: Playbook
    out_path: Path

    def deconstruct_playbook_files(self) -> None:
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
        step_dir: Path = self.out_path / mp.core.constants.STEPS_DIR
        step_dir.mkdir(exist_ok=True)

        for step in non_built_steps:
            step_path: Path = step_dir / f"{step['instance_name']}.yaml"
            step_path.write_text(yaml.dump(step, indent=4), encoding="utf-8")

    def _create_trigger_file(self, non_built_trigger: NonBuiltTrigger) -> None:
        trigger_path: Path = self.out_path / mp.core.constants.TRIGGER_FILE_NAME
        trigger_path.write_text(yaml.dump(non_built_trigger, indent=4), encoding="utf-8")

    def _create_overviews_file(self, non_built_overviews: list[NonBuiltOverview]) -> None:
        overviews_path: Path = self.out_path / mp.core.constants.OVERVIEWS_FILE_NAME
        overviews_path.write_text(yaml.dump(non_built_overviews, indent=4), encoding="utf-8")

    def _create_display_info_file(
        self, non_built_display_info: NonBuiltPlaybookDisplayInfo
    ) -> None:
        display_info_path: Path = self.out_path / mp.core.constants.DISPLAY_INFO_FILE_MAME
        display_info_path.write_text(yaml.dump(non_built_display_info, indent=4), encoding="utf-8")

    def _create_definition_file(self, non_built_meta_data: NonBuiltPlaybookMetadata) -> None:
        definition_path: Path = self.out_path / mp.core.constants.DEFINITION_FILE
        definition_path.write_text(yaml.dump(non_built_meta_data, indent=4), encoding="utf-8")

    def _create_release_notes_file(
        self, non_built_release_notes: list[NonBuiltReleaseNote]
    ) -> None:
        release_notes_path: Path = self.out_path / mp.core.constants.RELEASE_NOTES_FILE
        release_notes_path.write_text(
            yaml.dump(non_built_release_notes, indent=4), encoding="utf-8"
        )

    def _create_widgets_files(
        self, non_built_widgets: list[NonBuiltPlaybookWidgetMetadata]
    ) -> None:
        widgets_path: Path = self.out_path / mp.core.constants.WIDGETS_DIR
        widgets_path.mkdir(exist_ok=True)

        for w in non_built_widgets:
            widget_path: Path = widgets_path / f"{w['title']}.yaml"
            widget_path.write_text(yaml.dump(w, indent=4), encoding="utf-8")

        for w in self.playbook.widgets:
            widget_path: Path = widgets_path / f"{w.title}.html"
            html_content: str = w.data_definition.html_content if w.type == WidgetType.HTML else ""
            if html_content:
                widget_path.write_text(html_content)
