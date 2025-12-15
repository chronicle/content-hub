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

import mp.core.config
import mp.core.constants

if TYPE_CHECKING:
    from pathlib import Path


def create_or_get_content_dir() -> Path:
    """Get the content path.

    If the directory doesn't exist, it creates it

    Returns:
        The root/content/integrations directory path

    """
    return create_dir_if_not_exists(
        mp.core.config.get_marketplace_path() / mp.core.constants.CONTENT_DIR_NAME
    )


def create_or_get_out_contents_dir() -> Path:
    """Get the out/content/ path.

    If the directory doesn't exist, it creates it

    Returns:
        The out/content/ directory path

    """
    return create_dir_if_not_exists(create_or_get_out_dir() / mp.core.constants.CONTENT_DIR_NAME)


def create_or_get_out_dir() -> Path:
    """Get the out/ path.

    If the directory doesn't exist, it creates it

    Returns:
        The out/ directory path

    """
    return create_dir_if_not_exists(
        mp.core.config.get_marketplace_path() / mp.core.constants.OUT_DIR_NAME
    )


def create_dir_if_not_exists(p: Path, /) -> Path:
    """Create the provided path as a directory if it doesn't exist.

    Doesn't raise any error if the dir already exists

    Args:
        p: The dir's path to create if it doesn't exist

    Returns:
        The created path

    """
    p.mkdir(parents=True, exist_ok=True)
    return p
