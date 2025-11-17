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

from . import constants
from .data_models.integrations.script.parameter import ScriptParamType

if TYPE_CHECKING:
    from collections.abc import Collection
    from pathlib import Path

    from .data_models.integrations.connector.parameter import ConnectorParameter
    from .data_models.integrations.integration_meta.parameter import IntegrationParameter


def validate_ssl_parameter(
    script_name: str,
    parameters: Collection[IntegrationParameter | ConnectorParameter],
) -> None:
    """Validate the Verify SSL parameter.

    Validates the presence and correctness of a 'Verify SSL' parameter in the provided
    integration or connector's parameters. Ensures that the parameter exists, is of the
    correct type, and has the correct default value unless the script is explicitly
    excluded from verification.

    Args:
        script_name: The name of the integration or connector script.
        parameters: collection of parameters associated with the component.

    Raises:
        ValueError: If the 'Verify SSL' parameter is missing or its default value is
            not true
        TypeError: If the 'Verify SSL' parameter exists but is not of type boolean.

    """
    if script_name in constants.EXCLUDED_NAMES_WITHOUT_VERIFY_SSL:
        return

    ssl_param: IntegrationParameter | ConnectorParameter | None = next(
        (p for p in parameters if p.name in constants.VALID_SSL_PARAM_NAMES),
        None,
    )
    msg: str
    if ssl_param is None:
        msg = f"{script_name} is missing a 'Verify SSL' parameter"
        raise ValueError(msg)

    if ssl_param.type_ is not ScriptParamType.BOOLEAN:
        msg = f"The 'verify ssl' parameter in {script_name} must be of type 'boolean'"
        raise TypeError(msg)

    if script_name in constants.EXCLUDED_NAMES_WHERE_SSL_DEFAULT_IS_NOT_TRUE:
        return

    if ssl_param.default_value is not True:
        msg = f"The default value of the 'Verify SSL' param in {script_name} must be a boolean true"
        raise ValueError(msg)


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
