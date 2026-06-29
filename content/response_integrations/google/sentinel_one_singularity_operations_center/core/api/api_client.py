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

from typing import TYPE_CHECKING, NamedTuple

from TIPCommon.base.interfaces import Apiable

from ..constants import REQUEST_TIMEOUT
from .api_utils import get_full_url, validate_response
from .queries import TEST_CONNECTIVITY_QUERY

if TYPE_CHECKING:
    from requests import Response, Session
    from TIPCommon.base.interfaces.logger import ScriptLogger


class ApiParameters(NamedTuple):
    api_root: str


class SentinelOneSingularityOperationsCenterApiClient(Apiable):
    PAGE_SIZE = 100

    def __init__(
        self,
        authenticated_session: Session,
        configuration: ApiParameters,
        logger: ScriptLogger,
    ) -> None:
        super().__init__(
            authenticated_session=authenticated_session,  # type: ignore # noqa: PGH003
            configuration=configuration,
        )
        self.logger: ScriptLogger = logger
        self.api_root: str = configuration.api_root

    def test_connectivity(self) -> None:
        """Test connectivity to SentinelOne Singularity Operations Center."""
        url: str = get_full_url(self.api_root, "graphql")

        # Payload to list 1 alert with limited fields as per specification
        payload = {
            "query": TEST_CONNECTIVITY_QUERY,
            "variables": {
                "first": 1,
                "viewType": "ALL",
            },
        }

        # Send request
        response: Response = self.session.post(
            url,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        validate_response(
            response,
            error_msg="Failed to connect to the SentinelOne Singularity Operations Center server",
        )
