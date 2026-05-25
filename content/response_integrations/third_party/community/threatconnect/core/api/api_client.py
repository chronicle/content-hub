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

# Inbuilt imports
import dataclasses
import urllib.parse
from typing import TYPE_CHECKING, Any

# Third-party imports
import requests

# TIPCommon imports
from TIPCommon.base.interfaces import Apiable

# Local imports
from ..data_models import IndicatorData
from .api_utils import get_full_url, validate_response

if TYPE_CHECKING:
    from logging import Logger

    from ...core.auth import AuthenticatedSession


@dataclasses.dataclass(slots=True)
class ApiParameters:
    """ThreatConnect V3 API Configuration Parameters."""

    api_root: str
    verify_ssl: bool

    def __post_init__(self) -> None:
        """Normalize API configuration parameters."""
        api_root_clean = self.api_root.rstrip("/")
        if not api_root_clean.endswith("/api"):
            api_root_clean = f"{api_root_clean}/api"
        self.api_root = api_root_clean


class ThreatConnectApiClient(Apiable[ApiParameters]):
    """ThreatConnect V3 API Client implementing Apiable interface."""

    def __init__(
        self,
        authenticated_session: AuthenticatedSession,
        configuration: ApiParameters,
        logger: Logger,
    ) -> None:
        super().__init__(
            authenticated_session=authenticated_session,  # type: ignore[arg-type]
            configuration=configuration,
        )
        self.api_root = configuration.api_root
        self.verify_ssl = configuration.verify_ssl
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
        params: dict | None = None,
        headers: dict | None = None,
        cookies: dict | None = None,
        data: str | None = None,
        verify: bool | None = None,
        timeout: int | None = None,
    ) -> requests.Response:
        """Execute an arbitrary HTTP request."""
        if verify is None:
            verify = self.verify_ssl

        response = self.session.request(
            method=method,
            url=url,
            params=params,
            headers=headers,
            cookies=cookies,
            data=data,
            verify=verify,
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

        params: dict[str, Any] = {
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
        owners: list[str | None] = list(owner_names) if owner_names else [None]

        for owner in owners:
            query_params = params.copy()
            if owner:
                query_params["owner"] = owner

            try:
                response = self.execute_request("GET", url, params=query_params)
                data = response.json().get("data")
                if data:
                    results.append(IndicatorData(data))
            except Exception as e:
                self.logger.warning(
                    f"Failed to fetch data for indicator {indicator_value} "
                    f"from owner {owner}: {e}"
                )

        return results