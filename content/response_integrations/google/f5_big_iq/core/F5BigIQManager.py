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

# ==============================================================================
# title           :F5BigIQManager.py
# description     :This Module contain all F5BigIQ API functionality
# author          :victor@siemplify.co
# date            :31-01-18
# python_version  :2.7
# ==============================================================================
# Get events by id: https://bigiq-cm-restapi-reference.readthedocs.io/en/latest/HowToGuides/ASM/t_get_event_log_record_by_support_id.html
# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations

import urllib.parse

import requests

# =====================================
#            Json payloads            #
# =====================================
GET_EVENTS_PAYLOAD = {
    "query": {"query_string": {"query": "support_id: {0}"}},
    "from": 0,
    "size": 1,
    "sort": {"date_time": "desc"},
}

CHANGE_POLICY_ENFORCEMENT_MODE_PAYLOAD = {"enforcementMode": "(0)"}

# =====================================
#               CONSTS                #
# =====================================
# Formats
QUERY_FORMAT = "support_id: {0}"

# Headers
GET_EVENT_URL = "mgmt/cm/shared/es/logiq/asmindex/_search"
CHANGE_POLICY_ENFORCEMENT_MODE_URL = (
    "/mgmt/cm/asm/working-config/policies/{0}"  # {0} - Policy ID
)
# Login URL.
OBTAIN_TOKEN_URL = "/mgmt/shared/authn/login"

# Header
HEADERS = {"Content-Type": "application/json"}


# =====================================
#              CLASSES                #
# =====================================
class F5BigIQManager:

    def __init__(self, host, username, password, verify_ssl=False):
        """:param host: Server Host Address {string}
        :param username: BigIQ Username {string}
        :param password: BigIQ Password {string}
        """
        self.host = f"https://{host}/"
        self.username = username
        self.password = password
        self.verify = verify_ssl
        # Empty token because its is still not obtained.
        self.token = ""
        self.login()

    def login(self):
        """Obtain BigIQ token and add it to self.headers."""
        # Form request URL.
        request_url = urllib.parse.urljoin(self.host, OBTAIN_TOKEN_URL)
        # Get response.
        response = requests.post(
            request_url,
            json={"username": self.username, "password": self.password},
            verify=self.verify,
        )

        # Extend token life time.
        requests.patch(
            urllib.parse.urljoin(self.host, f"mgmt/shared/authz/tokens/{self.token}"),
            json={"timeout": 4200},
            verify=self.verify,
        )

        # Validate response
        response.raise_for_status()

        self.token = response.json()["token"]["token"]

        HEADERS["X-F5-Auth-Token"] = self.token

    def get_event_logs_by_blocking_id(self, blocking_id):
        """Get events log for a blocking id.
        :param blocking_id: {string}
        :return: request response {JSON}
        """
        # Form request url.
        request_url = urllib.parse.urljoin(self.host, GET_EVENT_URL)
        # Organize payload.
        GET_EVENTS_PAYLOAD["query"]["query_string"]["query"] = QUERY_FORMAT.format(
            blocking_id
        )

        # Get response.
        response = requests.post(
            request_url, json=GET_EVENTS_PAYLOAD, headers=HEADERS, verify=self.verify
        )

        response.raise_for_status()

        return response.json()

    def change_policy_enforcement_mode(self, policy_id, enforcement_mode):
        """Modify the enforcement mode of a policy by it's id.
        :param policy_id: {string}
        :param enforcement_mode: {string}
        :return: success status {bool}
        """
        # Build request URL.
        request_url = urllib.parse.urljoin(
            self.host, CHANGE_POLICY_ENFORCEMENT_MODE_URL.format(policy_id)
        )
        # Organize payload.
        CHANGE_POLICY_ENFORCEMENT_MODE_PAYLOAD["enforcementMode"] = enforcement_mode

        # Get response.
        response = requests.patch(
            request_url,
            json=CHANGE_POLICY_ENFORCEMENT_MODE_PAYLOAD,
            headers=HEADERS,
            verify=self.verify,
        )

        response.raise_for_status()

        return True
