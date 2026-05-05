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

from mp.build_project.flow.integrations.flow import build_integrations

if TYPE_CHECKING:
    import pathlib

logger: logging.Logger = logging.getLogger(__name__)


def build_integration_for_pack(
    integration_name: str, version: str | None, build_src: pathlib.Path, temp_build_path: pathlib.Path
) -> None:
    """Build the integration for packing.

    Args:
        integration_name: The name of the integration.
        version: The version number.
        build_src: The source path to build from.
        temp_build_path: The destination path to build to.

    """
    if version is not None:
        build_integrations(
            integrations=[integration_name],
            repositories=[],
            src=build_src.parent,
            dst=temp_build_path,
            custom_integration=True,
        )
    else:
        build_integrations(
            integrations=[integration_name],
            repositories=[],
            dst=temp_build_path,
        )


def set_is_custom(def_path: pathlib.Path) -> None:
    """Set IsCustom=True in the integration definition file.

    Args:
        def_path: The path to the integration definition file.

    """
    try:
        with def_path.open("r+", encoding="utf-8") as f:
            def_data: dict[str, Any] = json.load(f)
            def_data["IsCustom"] = True
            f.seek(0)
            json.dump(def_data, f, indent=4)
            f.truncate()
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Failed to set IsCustom in %s: %s", def_path, e)
