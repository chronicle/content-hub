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

import logging
import typing

if typing.TYPE_CHECKING:
    from pathlib import Path

from mp.core.file_utils.common import create_or_get_content_dir

logger = logging.getLogger(__name__)


def create_or_get_custom_fields_root_dir() -> Path:
    """Create or get the custom fields root directory.

    Returns:
        The custom fields root directory Path.

    """
    content_dir = create_or_get_content_dir()
    custom_fields_dir = content_dir / "custom_fields"
    custom_fields_dir.mkdir(parents=True, exist_ok=True)
    return custom_fields_dir
