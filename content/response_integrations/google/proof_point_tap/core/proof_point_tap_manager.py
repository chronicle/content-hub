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
from urllib.parse import urljoin

from TIPCommon.types import SingleJson

from ..core.constants import API_EVENT_TYPE_MAPPING, ENDPOINTS
from ..core import datamodels
from ..core.exceptions import (
    ProofPointTapManagerError,
    ProofPointTapNotFoundError,
    ThreatIdNotFoundError,
)
from ..core import proof_point_tap_parser as parser
from ..core.utils import get_time_range, generate_time_intervals, resolve_threat_statuses


@dataclasses.dataclass(slots=True)
class ApiParameters:
    api_root: str


@dataclasses.dataclass(slots=True)
class SearchEventsParameters:
    event_type: str
    threat_status: str
    time_frame: str
    max_results: int
    custom_start: str = None
    custom_end: str = None


class ProofPointTapManager:
    """
    ProofPoint TAP Manager
    """

    def __init__(
        self,
        session: requests.Session,
        api_parameters: ApiParameters,
        force_check_connectivity: bool = False,
    ) -> None:
        self.server_address = self._get_adjusted_root_url(api_parameters.api_root)
        self.session = session
        if force_check_connectivity:
            self.test_connectivity()

    @staticmethod
    def _get_adjusted_root_url(api_root):
        return api_root if api_root[-1] == r"/" else f"{api_root}/"

    @staticmethod
    def _get_url(url_id, **kwargs):
        """
        Get url from url identifier.
        :param url_id: {str} The id of url
        :param general_api: {bool} whether to use general api or not
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The url
        """
        return ENDPOINTS[url_id].format(**kwargs)

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param general_api: {bool} whether to use general api or not
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.server_address, self._get_url(url_id, **kwargs))

    def test_connectivity(self):
        """
        Test connectivity to ProofPoint
        :return: {bool} True if successful, exception otherwise.
        """
        params = {"size": 1}
        campaign_id = "fd50bbd0-5529-41b5-b8a4-257e861f2aca"
        response = self.session.get(
            self._get_full_url("ping", campaign_id=campaign_id), params=params
        )
        self.validate_response(response)

        return True

    def decode_urls(self, urls=None):
        """
        Decode urls
        :param urls: {list} List of encoded urls
        :return: {list} List of decoded urls
        """
        payload = {"urls": urls}

        response = self.session.post(self._get_full_url("decode_urls"), json=payload)
        self.validate_response(response, "Unable to resolve urls")

        return parser.build_results(
            raw_json=response.json(), method=parser.build_decode_url, data_key="urls"
        )

    def get_campaign(self, campaign_id):
        """
        Get campaign info
        :param campaign_id: {str} The campaign id
        :return: {datamodels.Campaign} The campaign object
        """
        response = self.session.get(
            self._get_full_url("get_campaign", campaign_id=campaign_id)
        )
        self.validate_response(response, f"Unable to get campaign {campaign_id}")

        return parser.build_campaign_obj(response.json())

    def get_campaign_forensics(self, campaign_id, filters, limit):
        """
        Get campaign forensics
        :param campaign_id: {str} The campaign id
        :param filters: {str} filters for getting forensics by type
        :param limit: {int} limit how many forensics should be returned
        :return: {datamodels.Campaign} The campaign object
        """
        params = {"campaignId": campaign_id}
        response = self.session.get(self._get_full_url("get_forensics"), params=params)
        self.validate_response(response)

        return parser.build_forensic_data_object(
            response.json(), filters=filters, limit=limit
        )

    def search_events(
        self,
        search_params: SearchEventsParameters,
    ) -> list[datamodels.Event]:
        """
        Search for events based on specified criteria.

        Args:
            search_params (SearchEventsParameters): An object containing the search
            parameters.

        Returns:
            list[datamodels.Event]: A list of Event objects matching the criteria.

        Raises:
            ValueError: If the start time is more than 7 days ago or if the start time
            is not before the end time.
            ProofPointTapManagerError: If there is an error during the API request.
        """
        start_time, end_time = get_time_range(
            search_params.time_frame,
            search_params.custom_start,
            search_params.custom_end,
        )
        intervals = generate_time_intervals(start_time, end_time, hours=1)

        event_type_value = API_EVENT_TYPE_MAPPING.get(search_params.event_type)
        threat_statuses = resolve_threat_statuses(search_params.threat_status)

        results = []
        for status in threat_statuses:
            for interval in intervals:
                if len(results) >= search_params.max_results:
                    break

                url = self._get_full_url(
                    "search_events",
                    event_type=event_type_value,
                    start_time=interval.start_time,
                    end_time=interval.end_time,
                )
                url += f"&threatStatus={status}"
                response = self.session.get(url)
                self.validate_response(response)
                result = response.json()

                items = parser.build_events_results(result, search_params.event_type)
                results.extend(items)
                if len(results) >= search_params.max_results:
                    break

        return results[: search_params.max_results]

    def list_campaigns(
        self,
        time_frame: str,
        max_results: int,
        custom_start: str = None,
        custom_end: str = None,
    ) -> list[SingleJson]:
        """
        List campaigns within a specified time frame.

        Args:
            time_frame (str): The time frame to search within.
            max_results (int): The maximum number of results to return.
            custom_start (str, optional): Custom start time. Defaults to None.
            custom_end (str, optional): Custom end time. Defaults to None.

        Returns:
            list[SingleJson]: A list of campaign objects.
        """
        start_time, end_time = get_time_range(time_frame, custom_start, custom_end)
        intervals = generate_time_intervals(start_time, end_time, hours=24)
        results = []
        for interval in intervals:
            if len(results) >= max_results:
                break

            url = self._get_full_url(
                "list_campaigns",
                start_time=interval.start_time,
                end_time=interval.end_time,
            )
            response = self.session.get(url)
            self.validate_response(response)
            result = response.json()

            items = parser.build_campaigns_results(result)
            results.extend(items)
            if len(results) >= max_results:
                break

        return results[:max_results]

    def get_threat_forensics(
        self,
        threat_id: str,
        include_campaign_forensics: bool,
        max_results: int,
    ) -> list[datamodels.ThreatReport]:
        """
        Get threat forensics for a given threat ID.

        Args:
            threat_id (str): The ID of the threat to get forensics for.
            include_campaign_forensics (bool): Whether to include campaign forensics.
            max_results (int): The maximum number of forensics to return.

        Returns:
            list[datamodels.ThreatReport]: A list of ThreatReport objects.
        """
        response = self.session.get(
            self._get_full_url(
                "get_threat",
                threat_id=threat_id,
                includeCampaignForensics=include_campaign_forensics,
            )
        )
        self.validate_response(response)
        result = response.json()

        return [
            parser.build_threat_report(report, max_results)
            for report in result.get("reports", [])
        ]

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            if (
                response.status_code == 404
                and "threatId not found" in error.response.text
            ):
                raise ThreatIdNotFoundError("Invalid Threat ID") from error

            if response.status_code == 404 and not error.response.text:
                raise ProofPointTapNotFoundError from error

            if response.status_code == 429:
                raise ProofPointTapManagerError(
                    "The user has made too many requests over the past 24 hours and "
                    "has been throttled."
                ) from error

            raise ProofPointTapManagerError(
                f"{error_msg}: {error} - {error.response.content}"
            ) from error
