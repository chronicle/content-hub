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

import datetime
import sys
import zipfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pathlib

import typer

from mp.core.file_utils import get_marketplace_integration_path
from mp.core.utils import str_to_snake_case


def find_integration_src_path(integration_name: str) -> tuple[pathlib.Path, str]:
    """Find the source path of the integration, trying snake_case if needed.

    Args:
        integration_name: The name of the integration.

    Returns:
        tuple[pathlib.Path, str]: The source path and the resolved integration name.

    Raises:
        typer.BadParameter: If the integration is not found.

    """
    src_path: pathlib.Path | None = get_marketplace_integration_path(integration_name)
    resolved_name: str = integration_name

    if src_path is None:
        snake_name: str = str_to_snake_case(integration_name)
        src_path: pathlib.Path | None = get_marketplace_integration_path(snake_name)
        if src_path is not None:
            resolved_name = snake_name

    if src_path is None:
        msg: str = f"Integration '{integration_name}' not found."
        raise typer.BadParameter(msg)

    return src_path, resolved_name


def create_zip(built_dir: pathlib.Path, identifier: str, zip_dir: pathlib.Path) -> pathlib.Path:
    """Create a ZIP archive of the built integration.

    Args:
        built_dir: The built integration directory.
        identifier: The integration identifier.
        zip_dir: The directory to save the ZIP file.

    Returns:
        pathlib.Path: The path to the created ZIP file.

    """
    date: str = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d")
    zip_name: str = f"{identifier}{date}.zip"
    zip_path: pathlib.Path = zip_dir / zip_name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in built_dir.rglob("*"):
            if file_path.is_file():
                zipf.write(file_path, arcname=file_path.relative_to(built_dir))

    return zip_path


def is_tty() -> bool:
    """Check if the current process is running in a TTY.

    Returns:
        bool: True if running in a TTY, False otherwise.

    """
    return sys.stdout.isatty()
