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

import binascii
import base64
import json
import io
import re
from typing import Any

import pyzipper
import requests
from requests.structures import CaseInsensitiveDict


from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyLogger import SiemplifyLogger
from TIPCommon.data_models import CaseWallAttachment
from TIPCommon.rest.soar_api import save_attachment_to_case_wall
from TIPCommon.types import SingleJson

from google_cloud_api.core.GoogleCloudApiConstants import (
    FILE_NAME,
    ZIP_FILE_EXTENSION,
    ZIP_FILE_PASSWORD,
)
from google_cloud_api.core.GoogleCloudApiDatamodels import IntegrationPlaceholders
from google_cloud_api.core.GoogleCloudApiExceptions import (
    GoogleCloudApiInvalidJsonException,
    GoogleCloudApiFileException,
    GoogleCloudApiHTTPException,
)


def parse_string_to_dict(string: str) -> SingleJson:
    """Parse json string to dict.

    Args:
        string: string to parse

    Raises:
        GoogleCloudApiInvalidJsonException: If provided JSON string is invalid

    Returns:
        SingleJson: parsed dict
    """
    try:
        return json.loads(string)
    except Exception as err:
        raise GoogleCloudApiInvalidJsonException(
            f"Unable to parse provided json. Error is: {err}"
        ) from err


def validate_expected_values(data: Any, expected_values: dict) -> bool:
    """ Validate data by recursively checking expected values

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
            return all(
                _validate_value(key, list_item)
                for list_item in value
            )

        if key not in expected_values.keys():
            return True

        expected_value = expected_values.get(key)

        if (
            (isinstance(expected_value, list) and value in expected_value)
            or (
                isinstance(expected_value, (str, int, float))
                and value == expected_value
            )
        ):
            return True

        return False

    return all(
        _validate_value(key, value)
        for key, value in data.items()
    )


def convert_to_base_64(data: Any) -> str:
    """Convert data to base 64 encoded string

    Args:
        data (Any): data to convert

    Returns:
        str: base 64 encoded string
    """
    base64_bytes = base64.b64encode(str(data).encode())
    return base64_bytes.decode()


def sava_attachment_to_case_wall(
    soar_action: SiemplifyAction,
    response: requests.Response,
    password_protect_zip: bool,
    logger: SiemplifyLogger
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
                encryption=pyzipper.WZ_AES
            ) as zf:
                zf.setpassword(ZIP_FILE_PASSWORD)
                zf.writestr(f"{file_name}{file_extension}", response.content)
        else:
            with pyzipper.AESZipFile(
                memory_file,
                "w",
                compression=pyzipper.ZIP_DEFLATED,
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
            )
        )
        logger.info(f"Successfully added file to {soar_action.case_id} case.")

    # pylint: disable=broad-exception-caught
    # soar_action.validate_siemplify_error is raises Exception for any HttpError
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
        raise GoogleCloudApiFileException(
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


def validate_response(
    response: requests.Response,
    error_msg: str = "An error occurred",
) -> None:
    """Validate response

    Args:
        response (requests.Response): Response to validate
        error_msg (str): Default message to display on error

    Raises:
        GoogleCloudApiHTTPException: If there is any error in the response
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        raise GoogleCloudApiHTTPException(
            f"{error_msg}: {error} {error.response.content}",
            status_code=error.response.status_code
        ) from error


def get_results_from_response(
    response: requests.Response,
    fields_to_return: [str],
    base64_output: bool = False
) -> SingleJson:
    """Get results from response

    Args:
        response (requests.Response): request response
        fields_to_return ([str]): list of fields to return in results
        base64_output (bool): specifies if response data should be converted to base64

    Returns:
        SingleJson: results from response
    """
    try:
        # try to get json from the response
        response_data = response.json()
    except json.JSONDecodeError:
        # response is not in json format, getting response text instead
        response_data = response.text

    results = {
        "response_data": (
            convert_to_base_64(response_data) if base64_output else response_data
        ),
        "redirects": (
            [item.url for item in response.history] + [response.url]
        ),
        "response_code": response.status_code,
        "response_cookies": response.cookies.get_dict(),
        "response_headers": dict(response.headers),
        "apparent_encoding": response.apparent_encoding
    }

    return {key: value for key, value in results.items() if key in fields_to_return}


def prepare_body_payload(
        body_payload_string: str,
        placeholders: IntegrationPlaceholders,
) -> SingleJson:
    """Prepare body payload by identifying payload format, either json, base64 or text

    Args:
        body_payload_string (str): body payload string
        placeholders (IntegrationPlaceholders): Integration placeholders

    Returns:
        SingleJson: body payload
    """
    try:
        return {
            "json": placeholders.apply_placeholders(json.loads(body_payload_string))
        }
    except (json.decoder.JSONDecodeError, TypeError):
        try:
            return {"data": base64.b64decode(body_payload_string)}
        except (binascii.Error, ValueError, TypeError):
            return {"data": body_payload_string}
