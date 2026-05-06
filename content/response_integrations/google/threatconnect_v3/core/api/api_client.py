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
from typing import TYPE_CHECKING

from ..constants import SECURITY_LABELS_URI
from ..exceptions import ThreatConnectV3Error

if TYPE_CHECKING:
    from logging import Logger

    import requests


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


class ThreatConnectV3ApiClient:
    """ThreatConnect V3 API Client."""

    def __init__(
        self,
        session: requests.Session,
        parameters: ApiParameters,
        logger: Logger,
    ) -> None:
        self.session = session
        self.api_root = parameters.api_root
        self.verify_ssl = parameters.verify_ssl
        self.logger = logger

    def test_connectivity(self) -> None:
        """Verify connectivity by calling the securityLabels API endpoint.

        Raises:
            ThreatConnectV3Error: If connection verification fails.

        """
        url = f"{self.api_root}{SECURITY_LABELS_URI}"
        self.logger.info(f"Testing connectivity via: {url}")  # noqa: G004

        try:
            params = {"resultLimit": 1}
            response = self.session.get(url, params=params, verify=self.verify_ssl)
            response.raise_for_status()
        except Exception as error:
            self.logger.exception("Connectivity check failed.")
            msg = f"Failed to connect to the ThreatConnect server: {error}"
            raise ThreatConnectV3Error(msg) from error
