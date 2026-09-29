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

import mimetypes

import base64
import io
import os
import re
from typing import Any
import requests
from requests.structures import CaseInsensitiveDict

import pyzipper

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyLogger import SiemplifyLogger
from TIPCommon.data_models import CaseWallAttachment
from TIPCommon.rest.soar_api import save_attachment_to_case_wall
from TIPCommon.types import ChronicleSOAR

from .constants import (
    CA_CERTIFICATE_FILE_NAME,
    FILE_NAME,
    ZIP_FILE_EXTENSION,
    ZIP_FILE_PASSWORD,
)
from .exceptions import HTTPV2CertificateException, HTTPV2FileException


def format_dict(dictionary, **kwargs):
    """Format a dictionary with provided key/value arguments

    Args:
        dictionary (dict): dictionary to format
        **kwargs (dict): key/value arguments passed for dictionary formatting

    Returns:
        dict: formatted dictionary
    """
    for key, value in dictionary.items():
        for arg_key, arg_value in kwargs.items():
            if arg_key in value:
                dictionary[key] = value.replace(arg_key, arg_value)

    return dictionary


def validate_expected_values(data: Any, expected_values: dict):
    """Validate data by recursively checking expected values

    Args:
        data (Any): data to validate
        expected_values (dict): expected values

    Returns:
        bool: True if expected values are in data False otherwise
    """
    if not isinstance(data, dict):
        return False

    if not data and expected_values:
        return False

    def _validate_value(key, value):
        if isinstance(value, dict):
            return all(
                _validate_value(nested_key, nested_value)
                for nested_key, nested_value in value.items()
            )

        if isinstance(value, list):
            return all(_validate_value(key, list_item) for list_item in value)

        if key not in expected_values.keys():
            return True

        expected_value = expected_values.get(key)

        if (isinstance(expected_value, list) and value in expected_value) or (
            isinstance(expected_value, str) and value == expected_value
        ):
            return True

        return False

    return all(_validate_value(key, value) for key, value in data.items())


def convert_to_base_64(data: Any):
    """Convert data to base 64 encoded string

    Args:
        data (Any): data to convert

    Returns:
        str: base 64 encoded string
    """
    base64_bytes = base64.b64encode(str(data).encode())
    return base64_bytes.decode()


def save_certificate_file(chronicle_soar: ChronicleSOAR, ca_certificate: str) -> str:
    """Save certificate to file

    Args:
        chronicle_soar: Chronicle SOAR SDK object
        ca_certificate: certificate to save

    Returns:
        str: certificate file path
    """
    try:
        file_content = base64.b64decode(ca_certificate).decode()
        file_path = os.path.join(
            chronicle_soar.get_temp_folder_path(), CA_CERTIFICATE_FILE_NAME
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_content)

        return str(file_path)

    except Exception as e:
        raise HTTPV2CertificateException(f"Certificate Error: {e}") from e


def sava_attachment_to_case_wall(
    soar_action: SiemplifyAction,
    response: requests.Response,
    password_protect_zip: bool,
    logger: SiemplifyLogger,
):
    """Save attachment to case wall

    Args:
        soar_action (SiemplifyAction): SiemplifyAction object
        response (requests.Response): requests.Response object
        password_protect_zip (bool): specifies if zip should be password protected
        logger (SiemplifyLogger): SiemplifyLogger object
    """
    try:
        file_extension = extract_file_extension(response.headers)
        file_name = extract_file_name(response.headers)
        memory_file = io.BytesIO()  # mimic the zip file in the filesystem

        if password_protect_zip:
            with pyzipper.AESZipFile(
                memory_file,
                "w",
                compression=pyzipper.ZIP_DEFLATED,
                encryption=pyzipper.WZ_AES,
            ) as zf:
                zf.setpassword(ZIP_FILE_PASSWORD)
                zf.writestr(f"{file_name}{file_extension}", response.content)
        else:
            with pyzipper.AESZipFile(
                memory_file, "w", compression=pyzipper.ZIP_DEFLATED
            ) as zf:
                zf.writestr(f"{file_name}{file_extension}", response.content)

        memory_file.seek(0)
        zip_bytes = memory_file.read()
        zip_base64 = base64.b64encode(zip_bytes).decode()

        save_attachment_to_case_wall(
            soar_action,
            CaseWallAttachment(
                name=file_name,
                base64_blob=zip_base64.strip(),
                file_type=ZIP_FILE_EXTENSION,
                is_important=False,
            ),
        )
        soar_action.validate_siemplify_error(response)
        logger.info(f"Successfully added file to {soar_action.case_id} case.")

    except Exception as err:
        logger.error(
            f"Failed to attach file to {soar_action.case_id} case. Reason: {err}"
        )


def extract_file_extension(response_headers: CaseInsensitiveDict[str]) -> str:
    """Extract file extension from response headers

    Args:
        response_headers (CaseInsensitiveDict[str]): response headers

    Returns:
        str: file extension
    """
    mimetype = response_headers.get("Content-Type")

    if not mimetype:
        raise HTTPV2FileException(
            "Unable to extract file extension from response headers"
        )

    return mimetypes.guess_extension(mimetype.partition(";")[0].strip())


def extract_file_name(response_headers: CaseInsensitiveDict[str]) -> str:
    """Extract file name from response headers

    Args:
        response_headers (CaseInsensitiveDict[str]): response headers

    Returns:
        str: file name
    """
    content_disposition = response_headers.get("Content-Disposition", "")
    file_name = re.findall(r'filename="([^"]*)\.', content_disposition)

    if file_name:
        return file_name[0]

    return FILE_NAME
