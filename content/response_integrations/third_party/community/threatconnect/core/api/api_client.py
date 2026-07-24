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

"""ThreatConnect V3 core API client."""

from __future__ import annotations

import dataclasses
import urllib.parse
from typing import TYPE_CHECKING

import requests
from TIPCommon.base.interfaces import Apiable

from ..data_models import IndicatorData
from ..exceptions import ThreatConnectHTTPError
from .api_utils import get_full_url, validate_response

if TYPE_CHECKING:
    from logging import Logger

    from TIPCommon.types import SingleJson

    from ..auth import AuthenticatedSession


@dataclasses.dataclass(slots=True)
class ApiParameters:
    """ThreatConnect V3 API Configuration Parameters."""

    api_root: str
    verify_ssl: bool


class ThreatConnectApiClient(Apiable[ApiParameters]):
    """ThreatConnect V3 API Client implementing Apiable interface."""

    def __init__(
        self,
        authenticated_session: AuthenticatedSession,
        configuration: ApiParameters,
        logger: Logger,
    ) -> None:
        super().__init__(
            authenticated_session=authenticated_session,
            configuration=configuration,
        )
        self.api_root = configuration.api_root
        self.logger = logger

    def test_connectivity(self) -> None:
        """Verify connectivity by calling the securityLabels API endpoint."""
        url = get_full_url(self.api_root, "ping")
        self.logger.info(f"Testing connectivity via: {url}")

        params = {"resultLimit": 1}
        response = self.session.get(url, params=params)
        validate_response(
            response,
            error_msg="Failed to connect to the ThreatConnect server"
        )

    def execute_request(
        self,
        method: str,
        url: str,
        *,
        params: SingleJson | None = None,
        headers: SingleJson | None = None,
        cookies: SingleJson | None = None,
        data: str | None = None,
        timeout: int | None = None,
    ) -> requests.Response:
        """Execute an arbitrary HTTP request."""
        response = self.session.request(
            method=method,
            url=url,
            params=params,
            headers=headers,
            cookies=cookies,
            data=data,
            timeout=timeout,
        )
        validate_response(
            response,
            error_msg=f"Failed to execute {method} request to {url}"
        )
        return response

    def get_indicator_info(
        self,
        indicator_value: str,
        owner_names: list[str] | None = None,
    ) -> list[IndicatorData]:
        """Get enrichment info for a specific indicator value from V3 API."""
        encoded_value = urllib.parse.quote(indicator_value, safe="")
        url = get_full_url(
            self.api_root,
            "indicator_details", encoded_value=encoded_value
        )

        params: SingleJson = {
            "fields": [
                "tags",
                "attributes",
                "securityLabels",
                "associatedGroups",
                "associatedGroups.tags",
                "associatedGroups.attributes",
                "associatedGroups.securityLabels",
                "associatedIndicators",
                "associatedIndicators.threatAssess",
                "threatAssess",
            ]
        }

        results: list[IndicatorData] = []
        owners: list[str | None] = owner_names or [None]

        for owner in owners:
            query_params = params.copy()
            if owner:
                query_params["owner"] = owner

            try:
                response = self.execute_request("GET", url, params=query_params)
                data = response.json().get("data")
                if data:
                    results.append(IndicatorData(data))
            except ThreatConnectHTTPError as e:
                if e.status_code == 404:
                    self.logger.debug(
                        f"Indicator {indicator_value} not found in owner {owner}."
                    )
                else:
                    self.logger.warn(
                        f"Failed to fetch data for indicator {indicator_value} "
                        f"from owner {owner}: {e}"
                    )
            except Exception as e:
                self.logger.warn(
                    f"Failed to fetch data for indicator {indicator_value} "
                    f"from owner {owner}: {e}"
                )

        return results
