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
import json
from typing import TYPE_CHECKING

import rich

import mp.core.constants
from mp.core.data_models.common.widget.data import WidgetType
from mp.core.utils import to_snake_case

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.data_models.playbooks.overview.metadata import Overview
    from mp.core.data_models.playbooks.playbook import BuiltPlaybook, Playbook
    from mp.core.data_models.playbooks.widget.metadata import PlaybookWidgetMetadata


@dataclasses.dataclass(slots=True)
class PlaybookBuilder:
    playbook: Playbook
    playbook_path: Path
    out_path: Path

    def build(self) -> None:
        """Build a specific playbook to its "out" path."""
        rich.print("Loading widgets from external files...")
        self._load_widgets_html_content()
        self._load_widgets_html_content_to_overviews()
        built_playbook: BuiltPlaybook = self.playbook.to_built()
        built_playbook_path = self.out_path / f"{to_snake_case(self.playbook.meta_data.name)}.json"
        built_playbook_path.write_text(json.dumps(built_playbook, indent=4))

    def _load_widgets_html_content(self) -> None:
        widgets: list[PlaybookWidgetMetadata] = self.playbook.widgets
        widgets_folder_path: Path = self.playbook_path / mp.core.constants.WIDGETS_DIR
        for w in widgets:
            if w.type is WidgetType.HTML:
                html_file_path = widgets_folder_path / f"{w.title}.html"
                w.data_definition.html_content = html_file_path.read_text(encoding="utf-8")

    def _load_widgets_html_content_to_overviews(self) -> None:
        overviews: list[Overview] = self.playbook.overviews
        widgets_folder_path: Path = self.playbook_path / mp.core.constants.WIDGETS_DIR
        for o in overviews:
            for w in o.widgets:
                if w.type.name == "HTML":
                    html_file_path = widgets_folder_path / f"{w.title}.html"
                    if html_file_path.exists():
                        w.data_definition.html_content = html_file_path.read_text(encoding="utf-8")
