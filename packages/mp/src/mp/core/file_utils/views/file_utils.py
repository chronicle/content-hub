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
from typing import TYPE_CHECKING, Any

import mp.core.constants
import mp.core.file_utils.common.utils

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


def create_or_get_views_root_dir() -> Path:
    """Get the content-hub views root folder path (views dir).

    Returns:
        root "views" folder path.

    """
    return mp.core.file_utils.common.utils.create_dir_if_not_exists(
        mp.core.file_utils.common.utils.create_or_get_content_dir() / mp.core.constants.VIEWS_DIR_NAME
    )


def get_view_out_dir() -> Path:
    """Get the output directory for built views.

    Returns:
        The path to the output directory for built views.

    """
    return mp.core.file_utils.common.utils.create_dir_if_not_exists(
        get_view_out_base_dir() / mp.core.constants.VIEW_OUT_DIR_NAME
    )


def get_view_out_base_dir() -> Path:
    """Get the base output directory for built views.

    Returns:
        The path to the base output directory for built views.

    """
    return mp.core.file_utils.common.utils.create_dir_if_not_exists(
        mp.core.file_utils.common.utils.create_or_get_out_contents_dir() / mp.core.constants.VIEW_BASE_OUT_DIR_NAME
    )


def is_non_built_view(view_path: Path) -> bool:
    """Check whether a view is in non-built format.

    Returns:
        Whether the view is in a non-built format.

    """
    if not view_path.is_dir():
        return False

    view_file: Path = view_path / mp.core.constants.VIEW_FILE_NAME
    return view_file.exists()


def is_built_view(path: Path) -> bool:
    """Check whether a path is a built view template.

    Returns:
        Whether the provided path is a built view.

    """
    if not path.exists() or path.is_dir() or path.suffix != ".json":
        return False

    try:
        with path.open(encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)

        required_keys = {"OverviewTemplate", "Roles"}
        if not required_keys.issubset(data.keys()):
            logger.error(
                "View is invalid, File %s is missing one or more required keys: %s",
                path.name,
                required_keys - data.keys(),
            )
            return False

    except json.JSONDecodeError:
        logger.exception("View is invalid, File %s is not a valid JSON file.", path.name)
        return False
    except OSError:
        logger.exception("Error reading file %s", path.name)
        return False

    return True
