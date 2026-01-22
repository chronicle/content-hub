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

from typing import TYPE_CHECKING
from urllib.parse import urljoin

from TIPCommon.data_models import Container
from TIPCommon.utils import get_sdk_api_uri

if TYPE_CHECKING:
    import requests

    from TIPCommon.rest.custom_types import HttpMethod
    from TIPCommon.types import ChronicleSOAR, SingleJson


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
        self.chronicle_soar.LOGGER.info(
            f"Calling API endpoint: {method.value} {url}"
        )
        request_kwargs = {
            "params": params,
            "json": json_payload,
        }

        if headers:
            request_kwargs["headers"] = headers

        response = self.chronicle_soar.session.request(
            method.value,
            url,
            **request_kwargs,
        )
        return response
