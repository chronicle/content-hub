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
import dataclasses
import requests

from TIPCommon.base.interfaces import ScriptLogger
from TIPCommon.types import SingleJson
from ..core import api_utils
from ..core import utils


@dataclasses.dataclass(slots=True)
class ApiParameters:
    api_root: str
    api_token: str


class ApiManager:
    def __init__(
        self,
        session: requests.Session,
        api_parameters: ApiParameters,
        logger: ScriptLogger,
    ) -> None:
        self.session: requests.Session = session
        self.api_root: str = api_parameters.api_root
        self.api_token: str = api_parameters.api_token
        self.logger: ScriptLogger = logger

    def test_connectivity(self) -> None:
        """Test the connectivity to the Zerofox API."""
        url: str = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="get_alert",
        )
        response: requests.Response = self.session.get(url=url)
        api_utils.validate_response(response=response)

    def add_note_to_alert(self, alert_id: str, note: str) -> None:
        """Add a note to an alert in Zerofox.

        Args:
            alert_id (str): The ID of the alert to add the note to.
            note (str): The note to add to the alert.
        """
        body: SingleJson = {"notes": note}
        url: str = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="add_note",
            alert_id=alert_id,
        )
        response: requests.Response = self.session.post(url=url, json=body)
        api_utils.validate_response(response=response)

    def close_alert(self, alert_id: str) -> None:
        """Close an alert in Zerofox.

        Args:
            alert_id (str): The ID of the alert to close.
        """
        url: str = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="close_alert",
            alert_id=alert_id,
        )
        response: requests.Response = self.session.post(url=url)
        api_utils.validate_response(response=response)

    def request_takedown(self, alert_id: str) -> None:
        """Request takedown for an alert in Zerofox.

        Args:
            alert_id (str): The ID of the alert to request takedown for.
        """
        url: str = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="request_takedown",
            alert_id=alert_id,
        )
        response: requests.Response = self.session.post(url=url)
        api_utils.validate_response(response=response)

    def add_evidence_to_alert(self, alert_id: str, evidence_path: str) -> None:
        """Add evidence to an alert in ZeroFox.

        Args:
            alert_id (str): The ID of the alert to add evidence to.
            evidence_path (str): Path to the evidence file.
        """
        url = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="add_evidence_to_alert",
            alert_id=alert_id,
        )

        with utils.build_evidence_payload(evidence_path) as multipart_data:
            response = self.session.post(url=url, files=multipart_data)
            api_utils.validate_response(response)
