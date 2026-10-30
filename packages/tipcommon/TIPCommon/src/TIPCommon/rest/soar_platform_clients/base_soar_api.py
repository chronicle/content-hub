"""Base class and enumerations for Chronicle SOAR API clients."""

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

import json
import re
from typing import TYPE_CHECKING

import requests

from TIPCommon.data_models import Container
from TIPCommon.exceptions import InternalJSONDecoderError
from TIPCommon.utils import get_sdk_api_uri

if TYPE_CHECKING:
    from TIPCommon.rest.custom_types import HttpMethod
    from TIPCommon.types import ChronicleSOAR, SingleJson


def validate_response(
    response: requests.Response,
    validate_json: bool = False,
) -> None:
    """Validate response HTTP status and optionally JSON body.

    Args:
        response (requests.Response): The response to validate.
        validate_json (bool): Whether to validate that the response body is valid JSON.

    Raises:
        requests.HTTPError: If the response status code indicates a failure, including
            the response body when available.
        InternalJSONDecoderError: If the response failed to be parsed as JSON.

    """
    try:
        response.raise_for_status()

        if validate_json:
            response.json()

    except requests.HTTPError as he:
        err_response = he.response if he.response is not None else response
        raw_body = getattr(err_response, "text", None)
        body = raw_body.strip() if isinstance(raw_body, str) else ""
        msg = f"An error happened while requesting API, {he}"
        if body:
            msg = f"{msg} | Response body: {body}"
        raise requests.HTTPError(msg, response=err_response) from he

    except json.JSONDecodeError as je:
        msg = f"Failed to parse response as JSON.\nError: {je}\nRaw response: {response.text}"
        raise InternalJSONDecoderError(
            msg,
        ) from je


class BaseSoarApi:
    """Base class for Chronicle SOAR API clients."""

    def __init__(self, chronicle_soar: ChronicleSOAR) -> None:
        """Initialize the BaseSoarApi.

        Args:
            chronicle_soar: The ChronicleSOAR SDK object.

        """
        self.chronicle_soar = chronicle_soar
        self.params = Container()

    def _make_request(
        self,
        method: HttpMethod,
        endpoint: str,
        params: SingleJson | None = None,
        json_payload: SingleJson | None = None,
        headers: dict[str, str] | None = None,
    ) -> requests.Response:
        url = f"{get_sdk_api_uri(self.chronicle_soar)}{endpoint}"
        url = re.sub(
            r'(https?://[^/]+)/(v1alpha/.*?)/download/(integrations/.*)',
            r'\1/download/\2/\3',
            url
        )
        self.chronicle_soar.LOGGER.info(f"Calling API endpoint: {method.value} {url}")
        request_kwargs = {
            "params": params,
            "json": json_payload,
        }

        if headers:
            request_kwargs["headers"] = headers

        return self.chronicle_soar.session.request(
            method.value,
            url,
            **request_kwargs,
        )
