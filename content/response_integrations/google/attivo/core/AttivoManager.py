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
from .constants import ENDPOINTS, RESULTS_MAX_COUNT, ACKNOWLEDGE_STATUS
from .UtilsManager import validate_response, filter_old_alerts
from .AttivoParser import AttivoParser
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from base64 import b64encode
from .AttivoExceptions import InvalidVulnerabilityException


class AttivoManager:
    def __init__(
        self, api_root, username, password, verify_ssl=False, siemplify_logger=None
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} API root of the Attivo instance.
        :param username: {str} Attivo API Username.
        :param password: {str} Attivo API Password.
        :param verify_ssl: {bool} If enabled, verify the SSL certificate for the connection to the server is valid.
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.username = username
        self.password = password
        self.logger = siemplify_logger
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.parser = AttivoParser()
        self.access_token = self._generate_access_token(self.username, self.password)
        self.session.headers.update(
            {"Sessionkey": f"{self.access_token}", "Content-Type": "application/json"}
        )

    def _generate_access_token(self, username, password):
        """
        Request access token
        :param username: {str} Attivo API Username.
        :param password: {str} Attivo API Password.
        :return: Access token
        """
        request_url = self._get_full_url("token")
        payload = {
            "userName": str(b64encode(username.encode("utf-8")), "utf-8"),
            "password": str(b64encode(password.encode("utf-8")), "utf-8"),
        }
        response = self.session.post(request_url, json=payload)
        validate_response(response, "Unable to generate session key for Attivo")

        return response.json().get("sessionKey")

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param root_url: {str} The API root for the request
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity
        """
        request_url = self._get_full_url("ping")
        response = self.session.post(request_url)
        validate_response(response)

    def get_alerts(
        self,
        existing_ids,
        limit,
        start_timestamp,
        end_timestamp,
        status,
        start_severity,
    ):
        """
        Get alerts
        :param existing_ids: {list} The list of existing ids
        :param limit: {int} The limit for results
        :param start_timestamp: {datetime} The timestamp for oldest message to fetch
        :param end_timestamp: {datetime} Last run timestamp + 12 hours interval
        :param status: {list} Status filter to apply
        :param start_severity: {list} Lowest severity to fetch
        :return: {list} The list of filtered Event objects
        """
        request_url = self._get_full_url("get_events")
        payload = {
            "timestampStart": start_timestamp,
            "timestampEnd": end_timestamp,
            "severity_start": start_severity,
            "severity_end": 15,
            "acknowledged": status,
        }
        response = self.session.post(request_url, json=payload)
        validate_response(response)
        results = response.json().get("eventdata", [])
        events = self.parser.build_events_list(results)

        while len(results) >= RESULTS_MAX_COUNT:
            payload["timestampEnd"] = convert_string_to_unix_time(
                sorted(events, key=lambda event: event.timestamp)[0].timestamp
            )
            response = self.session.post(request_url, json=payload)
            validate_response(response)
            results = response.json().get("eventdata", [])
            events.extend(self.parser.build_events_list(results))

        filtered_events = filter_old_alerts(
            logger=self.logger, alerts=events, existing_ids=existing_ids
        )
        return sorted(filtered_events, key=lambda event: event.timestamp)[:limit]

    def update_comment(self, event_id, comment):
        """
        Update event comment
        :param event_id: {str} Id of the event
        :param comment: {str} Comment to update
        """
        request_url = self._get_full_url("update_event")
        payload = {
            "indexes": ["all"],
            "action": "comment-list",
            "comment": comment,
            "eventId": [event_id],
        }
        response = self.session.post(request_url, json=payload)
        validate_response(response)

    def update_status(self, event_id, status):
        """
        Update event status
        :param event_id: {str} Id of the event
        :param status: {str} Status to update
        """
        request_url = self._get_full_url("update_event")
        payload = {
            "indexes": ["all"],
            "action": (
                "acknowledge-list"
                if status == ACKNOWLEDGE_STATUS
                else "unacknowledge-list"
            ),
            "eventId": [event_id],
        }
        response = self.session.post(request_url, json=payload)
        validate_response(response)

    def get_hostname_info(self, identifier, is_hostname):
        """
        Get hostname info
        :param identifier: {str} Entity identifier
        :param is_hostname: {bool} Whether the entity is hostname or ip
        :return: {Hostname} Hostname object
        """
        request_url = self._get_full_url("get_entity_info")

        if is_hostname:
            payload = {
                "feature": "endpoints",
                "filter": {
                    "and": [
                        {
                            "search": True,
                            "value": identifier,
                            "strictMatch": True,
                            "field": "hostName",
                        }
                    ]
                },
            }
        else:
            payload = {
                "feature": "endpoints",
                "filter": {
                    "and": [{"search": True, "value": identifier, "strictMatch": True}]
                },
                "indexes": ["endpoints"],
                "size": 1,
                "from": 0,
                "sort": [{"field": "lastModifiedTime", "order": "desc"}],
            }

        response = self.session.post(request_url, json=payload)
        validate_response(response)

        return self.parser.build_hostname_object(response.json())

    def get_threatpaths(self, hostname, limit):
        """
        Get ThreatPaths for Host
        :param hostname: {str} Hostname
        :param limit: {int} The limit for results
        :return: {list} List of ThreatPath objects
        """
        request_url = self._get_full_url("get_threatpaths")
        payload = {"hostName": hostname}
        response = self.session.post(request_url, json=payload)
        validate_response(response)

        return self.parser.build_threatpaths_list(response.json())[:limit]

    def get_credentials(self, hostname, limit):
        """
        Get Credentials for Host
        :param hostname: {str} Hostname
        :param limit: {int} The limit for results
        :return: {list} List of Credential objects
        """
        request_url = self._get_full_url("get_credentials")
        payload = {"hostName": hostname}
        response = self.session.post(request_url, json=payload)
        validate_response(response)

        return self.parser.build_credentials_list(response.json())[:limit]

    def get_vulnerabilities(self, hostname, limit):
        """
        Get Vulnerabilities for Host
        :param hostname: {str} Hostname
        :param limit: {int} The limit for results
        :return: {list}
        """
        request_url = self._get_full_url("get_vulnerabilities")
        payload = {"hostName": hostname}
        response = self.session.post(request_url, json=payload)
        validate_response(response)

        return response.json().get("vulnerabilities", [])[:limit]

    def get_critical_threatpaths(self):
        """
        Get Critical ThreatPaths
        :return: {list} List of ThreatPath objects
        """
        request_url = self._get_full_url("get_critical_threatpath")
        payload = {}
        response = self.session.post(request_url, json=payload)
        validate_response(response)

        return self.parser.build_critical_threatpaths_list(response.json())

    def get_service_threatpaths(self, service, limit):
        """
        Get ThreatPaths for Service
        :param service: {str} Service name
        :param limit: {int} The limit for results
        :return: {list} List of ThreatPath objects
        """
        request_url = self._get_full_url("get_service_threatpaths")
        payload = {"service": service}
        response = self.session.post(request_url, json=payload)
        validate_response(response)

        return self.parser.build_threatpaths_list(response.json())[:limit]

    def get_vulnerability_hosts(self, vulnerability, limit):
        """
        Get Hosts for Vulnerability
        :param vulnerability: {str} Vulnerability name
        :param limit: {int} The limit for results
        :return: {list}
        """
        request_url = self._get_full_url("get_vulnerability_hosts")
        payload = {"vulName": vulnerability}
        response = self.session.post(request_url, json=payload)
        validate_response(response)
        hostnames = response.json().get("hostNames")
        if not hostnames:
            raise InvalidVulnerabilityException
        return hostnames[:limit]
