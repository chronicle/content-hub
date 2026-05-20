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

"""ThreatConnect V3 utilities."""

from __future__ import annotations

import base64
import io
import json
import mimetypes
import re
from typing import TYPE_CHECKING, Any

import pyzipper
from TIPCommon.data_models import CaseWallAttachment
from TIPCommon.rest.soar_api import (
    save_attachment_to_case_wall as soar_save_attachment_to_case_wall,
)

if TYPE_CHECKING:
    import requests
    from requests.structures import CaseInsensitiveDict
    from SiemplifyAction import SiemplifyAction
    from SiemplifyLogger import SiemplifyLogger
    from TIPCommon.types import SingleJson

from .exceptions import ThreatConnectFileError, ThreatConnectInvalidJsonError

FILE_NAME = "threatconnect_response"
ZIP_FILE_EXTENSION = ".zip"
ZIP_FILE_PASSWORD = "infected"  # noqa: S105


def parse_string_to_dict(string: str) -> SingleJson:
    """Parse json string to dict.

    Args:
        string: string to parse.

    Returns:
        SingleJson: parsed dict.

    Raises:
        ThreatConnectInvalidJsonError: If provided JSON string is invalid.

    """
    try:
        return json.loads(string)
    except json.JSONDecodeError as err:
        msg = f"Unable to parse provided json. Error is: {err}"
        raise ThreatConnectInvalidJsonError(msg) from err


def validate_expected_values(  # noqa: PLR0911
    data: Any,  # noqa: ANN401
    expected_values: dict[str, Any],
) -> bool:
    """Validate data by recursively checking expected values.

    Args:
        data (Any): data to validate.
        expected_values (dict[str, Any]): expected values.

    Returns:
        bool: True if expected values are in data False otherwise.

    """
    if not isinstance(data, dict):
        return False

    if not expected_values:
        return True

    for expected_key, expected_val in expected_values.items():
        if expected_key not in data:
            return False

        actual_val: Any = data[expected_key]

        if isinstance(expected_val, dict):
            if not isinstance(actual_val, dict) or not validate_expected_values(
                actual_val,
                expected_val,
            ):
                return False
        elif isinstance(expected_val, list):
            if actual_val not in expected_val:
                return False
        elif actual_val != expected_val:
            return False

    return True


def convert_to_base_64(data: Any) -> str:  # noqa: ANN401
    """Convert data to base 64 encoded string.

    Args:
        data (Any): data to convert.

    Returns:
        str: base 64 encoded string.

    """
    base64_bytes: bytes = base64.b64encode(str(data).encode())
    return base64_bytes.decode()


def save_attachment_to_case_wall(
    soar_action: SiemplifyAction,
    response: requests.Response,
    *,
    password_protect_zip: bool,
    logger: SiemplifyLogger,
) -> None:
    """Save attachment to case wall.

    Args:
        soar_action (SiemplifyAction): SiemplifyAction object.
        response (requests.Response): requests.Response object.
        password_protect_zip (bool): specifies if zip should be password protected.
        logger (SiemplifyLogger): SiemplifyLogger object.

    """
    try:
        file_extension: str = extract_file_extension(response.headers)
        file_name: str = extract_file_name(response.headers)
        memory_file: io.BytesIO = io.BytesIO()

        if password_protect_zip:
            with pyzipper.AESZipFile(
                memory_file,
                "w",
                compression=pyzipper.ZIP_DEFLATED,
                encryption=pyzipper.WZ_AES,
            ) as zf:
                zf.setpassword(ZIP_FILE_PASSWORD.encode())
                zf.writestr(f"{file_name}{file_extension}", response.content)
        else:
            with pyzipper.AESZipFile(
                memory_file,
                "w",
                compression=pyzipper.ZIP_DEFLATED,
            ) as zf:
                zf.writestr(f"{file_name}{file_extension}", response.content)

        memory_file.seek(0)
        zip_bytes: bytes = memory_file.read()
        zip_base64: str = base64.b64encode(zip_bytes).decode()
        soar_save_attachment_to_case_wall(
            soar_action,
            CaseWallAttachment(
                name=file_name,
                base64_blob=zip_base64.strip(),
                file_type=ZIP_FILE_EXTENSION,
                is_important=False,
            ),
        )
        logger.info(f"Successfully added file to {soar_action.case_id} case.")  # noqa: G004

    except Exception:
        logger.exception(f"Failed to attach file to {soar_action.case_id} case.")  # noqa: G004


def extract_file_extension(response_headers: CaseInsensitiveDict[str]) -> str:
    """Extract file extension from response headers.

    Args:
        response_headers (CaseInsensitiveDict[str]): response headers.

    Returns:
        str: file extension.

    Raises:
        ThreatConnectFileError: If unable to extract file extension.

    """
    mimetype: str | None = response_headers.get("Content-Type")

    if not mimetype:
        msg = "Unable to extract file extension from response headers"
        raise ThreatConnectFileError(msg)

    extension: str | None = mimetypes.guess_extension(mimetype.partition(";")[0].strip())
    if not extension:
        msg = f"Could not determine file extension for mimetype: {mimetype}"
        raise ThreatConnectFileError(msg)
    return extension


def extract_file_name(response_headers: CaseInsensitiveDict[str]) -> str:
    """Extract file name from response headers.

    Args:
        response_headers (CaseInsensitiveDict[str]): response headers.

    Returns:
        str: file name.

    """
    content_disposition: str = response_headers.get("Content-Disposition", "")
    file_name_match: list[str] = re.findall(r'filename="([^"]*)\.', content_disposition)

    if file_name_match:
        return file_name_match[0]

    return FILE_NAME


def get_results_from_response(
    response: requests.Response,
    fields_to_return: list[str],
    *,
    base64_output: bool = False,
) -> SingleJson:
    """Get results from response.

    Args:
        response (requests.Response): request response.
        fields_to_return (list[str]): list of fields to return in results.
        base64_output (bool): specifies if response data should be converted to base64.

    Returns:
        SingleJson: results from response.

    """
    response_data: Any
    try:
        response_data = response.json()
    except json.JSONDecodeError:
        response_data = response.text

    results: dict[str, Any] = {
        "response_data": (convert_to_base_64(response_data) if base64_output else response_data),
        "redirects": [item.url for item in response.history] + [response.url],
        "response_code": response.status_code,
        "response_cookies": response.cookies.get_dict(),
        "response_headers": dict(response.headers),
        "apparent_encoding": response.apparent_encoding,
    }

    return {key: value for key, value in results.items() if key in fields_to_return}
