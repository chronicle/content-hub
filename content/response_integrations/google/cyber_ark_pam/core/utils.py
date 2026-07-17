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

"""Utility functions for CyberArk PAM."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

import requests
from TIPCommon.extraction import extract_configuration_param

from .constants import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_NOT_FOUND,
    INTEGRATION_NAME,
    MIN_MASK_LENGTH,
    URLS,
)
from .datamodels import IntegrationParameters
from .exceptions import (
    CyberArkPamAccountNotManagedError,
    CyberArkPamManagerError,
    CyberArkPamNotFoundError,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from TIPCommon.base.interfaces import ScriptLogger
    from TIPCommon.types import ChronicleSOAR, SingleJson


def validate_response(response: requests.Response) -> None:
    """Validate HTTP response and raise appropriate exceptions on failure.

    Args:
        response: The Response object to validate.

    Raises:
        CyberArkPamNotFoundError: If HTTP status code is 404.
        CyberArkPamAccountNotManagedError: If account is not managed by CPM.
        CyberArkPamManagerError: If any other HTTP error status is returned.

    """
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        error_code = ""
        try:
            error_json = response.json()
            error_message = error_json.get("ErrorMessage", "")
            error_code = error_json.get("ErrorCode", "")
            msg = error_message or (response.reason or str(e))
        except Exception:  # ruff:ignore[BLE001]
            msg = response.reason or str(e)

        if response.status_code == HTTP_STATUS_NOT_FOUND:
            raise CyberArkPamNotFoundError(msg) from e
        if response.status_code == HTTP_STATUS_BAD_REQUEST and (
            error_code == "CAWS00001E" or "not managed by the cpm" in msg.lower()
        ):
            raise CyberArkPamAccountNotManagedError(msg) from e
        raise CyberArkPamManagerError(msg) from e


def mask_id(value: str) -> str:
    """Mask a secret ID for safe logging.

    Args:
        value (str): The secret ID to mask.

    Returns:
        str: The masked secret ID.

    """
    if len(value) <= MIN_MASK_LENGTH:
        return "***"

    return f"{value[:3]}***{value[-3:]}"


def build_lookup_with_warnings(
    items: list[Any],
    get_key: Callable[[Any], Any],
    get_value: Callable[[Any], Any],
    entity_type: str,
    logger: ScriptLogger,
) -> SingleJson:
    """Build a lookup dictionary from a list and warn on duplicates.

    Args:
        items: The list of items to process.
        get_key: Function to extract the key from an item.
        get_value: Function to extract the value from an item.
        entity_type: Label for logging (e.g., 'job name').
        logger: The logger instance to use for warnings.

    Returns:
        The constructed dictionary mapping.

    """
    lookup: dict = {}
    for item in items:
        key = get_key(item)
        if not key:
            continue
        if key in lookup:
            logger.warn(f"Duplicate {entity_type} '{key}' detected. Later entry will overwrite.")
        lookup[key] = get_value(item)

    return lookup


def extract_integration_parameters(
    soar_object: ChronicleSOAR,
) -> IntegrationParameters:
    """Extract global integration configuration parameters for CyberArk PAM.

    Args:
        soar_object: The Chronicle SOAR action, job, or connector SDK object.

    Returns:
        IntegrationParameters: An IntegrationParameters instance with extracted values.

    """
    api_root = extract_configuration_param(
        soar_object,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        soar_object,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        soar_object,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        soar_object,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=False,
        input_type=bool,
        default_value=True,
        print_value=True,
    )
    ca_certificate = extract_configuration_param(
        soar_object,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate",
    )
    client_certificate = extract_configuration_param(
        soar_object,
        provider_name=INTEGRATION_NAME,
        param_name="Client Certificate",
    )
    client_certificate_passphrase = extract_configuration_param(
        soar_object,
        provider_name=INTEGRATION_NAME,
        param_name="Client Certificate Passphrase",
        remove_whitespaces=False,
    )
    return IntegrationParameters(
        api_root=api_root,
        username=username,
        password=password,
        verify_ssl=verify_ssl,
        ca_certificate=ca_certificate,
        client_certificate=client_certificate,
        client_certificate_passphrase=client_certificate_passphrase,
    )


def build_full_url(api_root: str, url_key: str, **kwargs: object) -> str:
    """Build the full URL from an API root and a URL key in URLS.

    Args:
        api_root: Base URL of the CyberArk PAM instance.
        url_key: The key in URLS dictionary mapping to the endpoint path.
        **kwargs: Variables passed for URL path formatting.

    Returns:
        The formatted full URL.

    """
    return urljoin(api_root, URLS[url_key].format(**kwargs))
