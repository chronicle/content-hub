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
import logging
import re
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING

import mp.core.constants
import mp.core.file_utils
from mp.core.data_models.common.widget.data import WidgetType

if TYPE_CHECKING:
    from mp.core.data_models.playbooks.overview.metadata import NonBuiltOverview, Overview
    from mp.core.data_models.playbooks.widget.metadata import NonBuiltPlaybookWidgetMetadata

logger: logging.Logger = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True, frozen=True)
class ViewDeconstructor:
    overview: Overview
    out_path: Path

    def deconstruct(self) -> None:
        """Deconstruct a View's code to its "out" path."""
        non_built_view: NonBuiltOverview = self.overview.to_non_built()

        # Create the views folder
        self.out_path.mkdir(exist_ok=True, parents=True)

        self._create_view_file(non_built_view)
        self._create_widgets_files()

    def _create_view_file(self, non_built_view: NonBuiltOverview) -> None:
        """Create the view metadata YAML file in the destination folder.

        Args:
            non_built_view: The NonBuiltOverview dictionary representing the view.

        """
        logger.info("Creating view file")
        view_path: Path = self.out_path / mp.core.constants.VIEW_FILE_NAME
        mp.core.file_utils.save_yaml(non_built_view, view_path)

    def _create_widgets_files(self) -> None:
        """Create separate YAML and HTML files for all widgets in the view.

        Raises:
            OSError: If writing a widget file fails.

        """
        if not self.overview.widgets:
            return

        logger.info("Creating widgets files")
        widgets_path: Path = self.out_path / mp.core.constants.WIDGETS_DIR
        widgets_path.mkdir(exist_ok=True)

        non_built_widgets: list[NonBuiltPlaybookWidgetMetadata] = [w.to_non_built() for w in self.overview.widgets]

        for i, w in enumerate(non_built_widgets):
            sanitized_title = sanitize_widget_filename(w.get("title") or "")
            filename = sanitized_title or f"widget_{w.get('identifier') or i}"
            widget_path: Path = widgets_path / f"{filename}{mp.core.constants.YAML_SUFFIX}"
            try:
                mp.core.file_utils.save_yaml(w, widget_path)
            except OSError:
                logger.exception(
                    "Failed to create a file for a widget with name '%s' at path '%s'."
                    " Please verify this type of widget title can be created as a file in your"
                    " system",
                    widget_path.stem,
                    widget_path,
                )
                raise

        for w in self.overview.widgets:
            if w.type is WidgetType.HTML:
                sanitized_title = sanitize_widget_filename(w.title or "")
                filename = sanitized_title or f"widget_{w.identifier}"
                widget_filename = f"{filename}.{mp.core.constants.HTML_SUFFIX}"
                widget_path: Path = widgets_path / widget_filename
                html_content: str = ""
                if hasattr(w.data_definition, "html_content"):
                    html_content = w.data_definition.html_content or ""
                else:
                    logger.warning(
                        "Widget %s type is HTML, but data_definition does not have"
                        " 'html_content' attribute (type is %s)",
                        w.title,
                        type(w.data_definition),
                    )
                widget_path.write_text(html_content, encoding="utf-8")


def sanitize_widget_filename(filename: str) -> str:
    """Sanitizes a filename to be used as a YAML file name.

    Args:
        filename: The filename to sanitize.

    Returns:
        The sanitized filename.

    """
    invalid_chars: str = r'[.\\/<>!@#$%^&*()+={};:~`"\[\]?|]'
    sanitized: str = re.sub(invalid_chars, " ", filename)

    return " ".join(sanitized.split())
