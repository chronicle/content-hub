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

import base64
import json
from typing import Iterable
from urllib.parse import quote

from google.auth.transport.requests import AuthorizedSession
import requests

from TIPCommon.base.interfaces import Apiable
from TIPCommon.base.utils import NewLineLogger
from ..core import WebRiskConstants
from ..core import WebRiskDatamodels
from ..core.WebRiskExceptions import WebRiskManagerException


ENDPOINTS = {
    "hashes.search": "hashes:search",
    "uris.search": "uris:search",
    "projects.uris.submit": "projects/{project_id}/uris:submit",
    "projects.operations.get": "{operation_name}"
}
THREAT_TYPES = tuple(
    tt.value for tt in WebRiskDatamodels.ThreatTypeEnum
    if tt != WebRiskDatamodels.ThreatTypeEnum.THREAT_TYPE_UNSPECIFIED
)


class ApiManager(Apiable):
    def __init__(
        self,
        api_root: str,
        session: AuthorizedSession,
        project_id: str,
        logger: NewLineLogger,
    ) -> None:
        """Manager for handling API interactions.

        Args:
            api_root: Api root for Vertex API
            session: Session object with corresponding headers
            project_id: Project ID to be used for request
            logger: The logger object
        """
        self.api_root = api_root
        self.session = session
        self.project_id = project_id
        self.logger = logger

    def _get_url(self, endpoint: str, **kwargs) -> str:
        """Get full url from url identifier."""
        api_root = (
            self.api_root if self.api_root.endswith("/")
            else f"{self.api_root}/"
        )
        return api_root + ENDPOINTS[endpoint].format(**kwargs)

    def test_connectivity(self) -> None:
        """Test connectivity."""
        self.search_uri(WebRiskConstants.URI_EXAMPLE)

    @staticmethod
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
            try:
                error_details = response.json()["error"]["details"][0]["detail"]
                if error_details:
                    raise WebRiskManagerException(
                        f"{error_msg}: {error_details}"
                    ) from error
            except (KeyError, IndexError, json.decoder.JSONDecodeError):
                pass

            raise WebRiskManagerException(
                f"{error_msg}: {error} {error.response.content}"
            ) from error

    def search_hash(
            self,
            hash_: str,
            threat_types: Iterable[str] = THREAT_TYPES,
    ) -> list[WebRiskDatamodels.ThreatObject]:
        """Search threat matches by hash prefix.

        Hash will be truncated to the most significant 4-32 bytes and encoded to base64.
        """
        hash_prefix = base64.b64encode(hash_[:8].encode()).decode()
        url = self._get_url("hashes.search") + f"?hashPrefix={hash_prefix}"
        for threat_type in threat_types:
            url += f"&threatTypes={threat_type}"

        response = self.session.get(url)
        self.validate_response(response)
        return [
            WebRiskDatamodels.ThreatObject.from_json(threat_hash_data)
            for threat_hash_data in response.json().get("threats", [])
        ]

    def search_uri(
            self,
            uri: str,
            threat_types: Iterable[str] = THREAT_TYPES,
    ) -> WebRiskDatamodels.ThreatObject | None:
        """Search threat matches by uri."""
        url = self._get_url("uris.search") + f"?uri={quote(uri)}"
        for threat_type in threat_types:
            url += f"&threatTypes={threat_type}"

        response = self.session.get(url)
        self.validate_response(response)
        threat_obj = response.json().get("threat")
        return (
            WebRiskDatamodels.ThreatObject.from_json(threat_obj)
            if threat_obj is not None else None
        )

    def submit_uri(
            self,
            submission: WebRiskDatamodels.Submission,
    ) -> WebRiskDatamodels.Operation:
        """Submit uri to WebRisk API."""
        url = self._get_url("projects.uris.submit", project_id=self.project_id)
        response = self.session.post(url, json=submission.to_payload())
        self.validate_response(response)
        return WebRiskDatamodels.Operation.from_json(response.json())

    def get_operation(
            self,
            operation_name: str,
    ):
        """Get operation from WebRisk API."""
        url = self._get_url("projects.operations.get", operation_name=operation_name)
        response = self.session.get(url)
        self.validate_response(response)
        return WebRiskDatamodels.Operation.from_json(response.json())
