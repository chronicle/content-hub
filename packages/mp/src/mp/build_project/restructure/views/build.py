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

import dataclasses
import json
import logging
from typing import TYPE_CHECKING

import mp.core.constants
from mp.core.data_models.common.widget.data import WidgetType
from mp.core.data_models.playbooks.overview.metadata import Overview
from mp.core.utils import to_snake_case

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.data_models.playbooks.overview.metadata import BuiltOverview

logger: logging.Logger = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True)
class ViewBuilder:
    view_path: Path
    out_path: Path

    def build(self) -> None:
        """Build a specific view to its "out" path."""
        logger.info("Loading view from non-built path: %s", self.view_path)
        overview: Overview = Overview.from_non_built_view_path(self.view_path)

        logger.info("Loading widgets from external files...")
        self._load_widgets_html_content(overview)

        built_view: BuiltOverview = overview.to_built()

        # Ensure out directory exists
        self.out_path.mkdir(exist_ok=True, parents=True)

        built_view_path = self.out_path / f"{to_snake_case(self.view_path.stem)}{mp.core.constants.JSON_SUFFIX}"
        built_view_path.write_text(json.dumps(built_view, indent=4), encoding="utf-8")
        logger.info("View built successfully to: %s", built_view_path)

    def _load_widgets_html_content(self, overview: Overview) -> None:
        widgets_folder_path: Path = self.view_path / mp.core.constants.WIDGETS_DIR
        for w in overview.widgets:
            if w.type is WidgetType.HTML:
                html_file_path = widgets_folder_path / f"{w.title}.html"
                if html_file_path.exists():
                    if hasattr(w.data_definition, "html_content"):
                        w.data_definition.html_content = html_file_path.read_text(encoding="utf-8")
                    else:
                        logger.warning(
                            "HTML content file exists for widget %s, but data_definition does not have"
                            " 'html_content' attribute (type is %s)",
                            w.title,
                            type(w.data_definition),
                        )
                else:
                    logger.warning("HTML content file not found for widget: %s", w.title)
