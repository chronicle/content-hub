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

import defusedxml.ElementTree as SafeElementTree
from PIL import Image, UnidentifiedImageError

import mp.core.constants

if TYPE_CHECKING:
    from pathlib import Path


def validate_param_name(name: str) -> str:
    """Validate a parameter's name.

    Ensure it adheres to the maximum allowed
    number of words as specified by PARAM_NAME_MAX_WORDS. If the name exceeds
    this limit, a ValueError is raised.

    Args:
        name: The parameter name to validate.

    Returns:
        The name of the parameter after the validation

    Raises:
        ValueError: If the parameter name exceeds the maximum number of allowed words.

    """
    if name in mp.core.constants.EXCLUDED_PARAM_NAMES_WITH_TOO_MANY_WORDS:
        return name

    if len(name.split()) > mp.core.constants.PARAM_NAME_MAX_WORDS:
        msg: str = f"Parameter name '{name}' exceeds maximum number of words"
        raise ValueError(msg)

    return name


def validate_svg_content(path: Path) -> str:
    """Read and validate an SVG file.

    Args:
        path: The path to the SVG file.

    Returns:
        The text content of the SVG file.

    Raises:
        ValueError: If the file is not found, empty, or not a valid SVG.

    """
    try:
        # Read content
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        msg = f"Failed to read or validate SVG file: {path}"
        raise ValueError(msg) from e

    if not content.strip():
        msg = f"SVG file is empty: {path}"
        raise ValueError(msg)

    try:
        # Parse the content as XML to check for well-formedness
        tree = SafeElementTree.fromstring(content)

    except SafeElementTree.ParseError as e:
        msg = f"Invalid XML syntax in SVG file: {path}"
        raise ValueError(msg) from e

    if "svg" not in tree.tag.lower():
        msg = f"File is not a valid SVG (missing <svg> root tag): {path}"
        raise ValueError(msg)

    return content


def validate_png_content(path: Path) -> bytes:
    """Read and validate a PNG file.

    Args:
        path: The path to the PNG file.

    Returns:
        The raw byte content of the PNG file.

    Raises:
        ValueError: If the file is not found, corrupted, or not a valid PNG.

    """
    try:
        with Image.open(path) as img:
            img.verify()

            if img.format != "PNG":
                msg = f"Invalid image format. Expected PNG but found {img.format} at {path}"
                raise ValueError(msg)

        return path.read_bytes()
    except UnidentifiedImageError as e:
        msg = f"File is not a valid image or is corrupted: {path}"
        raise ValueError(msg) from e
