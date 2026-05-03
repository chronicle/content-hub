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
from urllib.parse import urljoin
import requests
from .constants import (
    ENDPOINTS,
    ACCESS_TOKEN_PAYLOAD,
    REFRESH_TOKEN_PAYLOAD,
    API_ROOT_TO_AUTH_URL,
    REQUEST_DATE_FORMAT,
)
from .UtilsManager import (
    validate_response,
    filter_old_alerts,
    filter_alerts_by_timestamp,
    convert_time_to_given_offset,
)
from .Site24x7Parser import Site24x7Parser
from .Site24x7Exceptions import Site24x7Exception


class Site24x7Manager:
    def __init__(
        self,
        api_root,
        client_id,
        client_secret,
        refresh_token,
        verify_ssl=False,
        siemplify_logger=None,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} API root of the Site24x7 instance.
        :param client_id: {str} Client ID of the Site24x7 instance.
        :param client_secret: {str} Client Secret of the Site24x7 instance.
        :param refresh_token: {str} Refresh Token of the Site24x7 instance.
        :param verify_ssl: {bool} If enabled, verify the SSL certificate for the connection to the server is valid.
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.auth_url = API_ROOT_TO_AUTH_URL.get(self.api_root)
        if not self.auth_url:
            raise Site24x7Exception(
                "Please provide a valid API Root in integration configuration."
            )
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.logger = siemplify_logger
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.parser = Site24x7Parser()
        self.access_token = self._generate_access_token(
            self.client_id, self.client_secret, self.refresh_token
        )
        self.session.headers.update(
            {
                "Authorization": f"Zoho-oauthtoken {self.access_token}",
                "Content-Type": "application/json",
            }
        )

    def _generate_access_token(self, client_id, client_secret, refresh_token):
        """
        Request access token
        :param client_id: {str} Client ID of the Site24x7 instance.
        :param client_secret: {str} Client Secret of the Site24x7 instance.
        :param refresh_token: {str} Refresh Token of the Site24x7 instance.
        :return: Access token
        """
        ACCESS_TOKEN_PAYLOAD["client_id"] = client_id
        ACCESS_TOKEN_PAYLOAD["client_secret"] = client_secret
        ACCESS_TOKEN_PAYLOAD["refresh_token"] = refresh_token
        request_url = self._get_full_url(self.auth_url, "token")
        response = requests.post(request_url, data=ACCESS_TOKEN_PAYLOAD)
        validate_response(response, "Unable to generate access token for Site24x7")

        return response.json().get("access_token")

    @staticmethod
    def generate_refresh_token(api_root, client_id, client_secret, code):
        """
        Request refresh token
        :param api_root: {str} The API root of the Site24x7 instance.
        :param client_id: {str} Client ID of the Site24x7 instance.
        :param client_secret: {str} Client Secret of the Site24x7 instance.
        :param code: {str} Authorization code for generating Refresh Token.
        :return: Refresh token
        """
        REFRESH_TOKEN_PAYLOAD["client_id"] = client_id
        REFRESH_TOKEN_PAYLOAD["client_secret"] = client_secret
        REFRESH_TOKEN_PAYLOAD["code"] = code
        auth_url = API_ROOT_TO_AUTH_URL.get(
            api_root[:-1] if api_root.endswith("/") else api_root
        )

        if not auth_url:
            raise Site24x7Exception(
                "Please provide a valid API Root in integration configuration."
            )

        request_url = urljoin(auth_url, ENDPOINTS["token"])
        response = requests.post(request_url, data=REFRESH_TOKEN_PAYLOAD)
        validate_response(response, "Unable to generate refresh token for Site24x7")

        return response.json().get("refresh_token")

    def _get_full_url(self, root_url, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param root_url: {str} The API root for the request
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(root_url, ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity
        """
        request_url = self._get_full_url(self.api_root, "ping")
        response = self.session.get(request_url)
        validate_response(response)

    def get_monitors(self):
        """
        Get all available monitors
        :return: {list} List of Monitor objects
        """
        request_url = self._get_full_url(self.api_root, "monitors")
        response = self.session.get(request_url)
        validate_response(response)
        return self.parser.build_monitors_list(response.json())

    def get_alert_logs(self, existing_ids, limit, start_time, utc_offset):
        """
        Get alert logs
        :param existing_ids: {list} The list of existing ids
        :param limit: {int} The limit for results
        :param start_time: {datetime} The start datetime from where to fetch
        :param utc_offset: {float} UTC offset of server time
        :return: {list} The list of filtered AlertLog objects
        """
        request_url = self._get_full_url(self.api_root, "alert_logs")
        start_time = convert_time_to_given_offset(
            time_param=start_time, utc_offset=utc_offset
        )
        params = {"date": start_time.strftime(REQUEST_DATE_FORMAT)}
        response = self.session.get(request_url, params=params)
        validate_response(response)
        alert_logs = self.parser.build_alert_logs_list(response.json())
        filtered_by_timestamp = filter_alerts_by_timestamp(
            logger=self.logger,
            alerts=alert_logs,
            last_success_time=start_time,
            existing_ids=existing_ids,
        )
        filtered_logs = filter_old_alerts(
            logger=self.logger, alerts=filtered_by_timestamp, existing_ids=existing_ids
        )
        return sorted(filtered_logs, key=lambda log: log.sent_time)[:limit]
