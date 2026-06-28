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

import datetime as dt
from typing import NamedTuple, TYPE_CHECKING

from TIPCommon.base.interfaces import Apiable

from proofpoint_cloud_threat_response.core.api_utils import get_full_url, validate_response
from proofpoint_cloud_threat_response.core.data_parser import ProofpointCTRParser
from requests import Response

from proofpoint_cloud_threat_response.core.auth import AuthenticatedSession

if TYPE_CHECKING:
    from TIPCommon.base.interfaces.logger import ScriptLogger
    from TIPCommon.types import SingleJson

    from proofpoint_cloud_threat_response.core.data_models import ProofpointIncident, ProofpointMessage


class ApiParameters(NamedTuple):
    api_root: str


class ProofpointCloudThreatResponseApiClient(Apiable):
    def __init__(
        self,
        authenticated_session: AuthenticatedSession,
        configuration: ApiParameters,
        logger: ScriptLogger,
    ) -> None:
        super().__init__(
            authenticated_session=authenticated_session,
            configuration=configuration,
        )
        self.logger: ScriptLogger = logger
        self.api_root: str = configuration.api_root
        self.parser = ProofpointCTRParser()

    def test_connectivity(self) -> None:
        """Test connectivity to API."""
        url: str = get_full_url(api_root=self.api_root, endpoint_id="ping")
        payload: SingleJson = {
            "endRow": 1,
            "sortParams": [{"sort": "desc", "colId": "createdAt"}],
            "startRow": 0,
        }
        response: Response = self.session.post(url, json=payload)
        validate_response(response)

    def list_incidents(
        self,
        start_time: dt.datetime,
        end_time: dt.datetime,
        end_row: int,
        filters: SingleJson,
    ) -> list[ProofpointIncident]:
        """List incidents.

        Args:
            start_time (dt.datetime): Start date from where to list the incidents.
            end_time (dt.datetime): End date upto list the incidents.
            end_row (int): Number of incidents to list.
            filters (SingleJson): Filters to be used to filter the incidents.

        Returns:
            list[ProofpointIncident]: List of ProofpointIncident object.
        """
        url = get_full_url(api_root=self.api_root, endpoint_id="list_incidents")
        start_time = start_time + dt.timedelta(seconds=1)
        payload = {
            "startRow": 0,
            "endRow": end_row,
            "sortParams": [{"sort": "asc", "colId": "createdAt"}],
            "filters": {
                "time_range_filter": {
                    "start": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "end": end_time.strftime("%Y-%m-%d %H:%M:%S"),
                },
                **filters,
            },
        }
        response: Response = self.session.post(url, json=payload)
        validate_response(response)
        return self.parser.parse_incidents(response.json())

    def get_incident_messages(self, incident_id: str) -> list[ProofpointMessage]:
        """Get the messages related to incidents.

        Args:
            incident_id (str): Incident id.

        Returns:
            list[ProofpointMessage]: List of ProofpointMessage object.
        """
        payload = {
            "startRow": 0,
            "endRow": 499,
            "sortParams": [{"sort": "asc", "colId": "createdAt"}],
        }
        url: str = get_full_url(
            api_root=self.api_root,
            endpoint_id="get_incident_messages",
            incident_id=incident_id,
        )
        response: Response = self.session.post(url, json=payload)
        validate_response(response)
        return self.parser.parse_messages(response.json())
