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

# ============================================================================#
# title           :ProtectwiseManager.py
# description     :This Module contain all Protectwise operations functionality
# author          :avital@siemplify.co
# date            :22-02-2018
# python_version  :2.7
# libreries       : requests
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #

from __future__ import annotations
import requests
from functools import reduce

# ============================== CONSTS ===================================== #

API_ROOT = r"https://api.protectwise.com/api/v1"
FIELDS = ["threat", "ip", "geo"]

# ============================= CLASSES ===================================== #


class ProtectwiseManagerError(Exception):
    """
    General Exception for Protectwise manager
    """

    pass


class ProtectwiseManager:
    def __init__(self, email, password):
        """
        Connect to Protectwise
        """
        try:
            url = f"{API_ROOT}/token"

            response = requests.post(
                url=url, data={"email": email, "password": password}
            )

            response.raise_for_status()
            token = response.json()["token"]

            self.headers = {"X-Access-Token": token, "Content-Type": "application/json"}

        except requests.HTTPError as error:
            raise ProtectwiseManagerError(error.response.json()["error"]["info"])

        except Exception as error:
            raise ProtectwiseManagerError(
                f"Unable to connect to Protectwise: {error} {error}"
            )

    def get_ip_reputation(self, ip, start_time, end_time):
        """
        Get reputation for an ip
        :param ip: The ip
        :param start_time: (unixtime) Start time to fetch threat intel from
        :param end_time:(unixtime) End time to fetch threat intel from
        :return: {dict} Reputation
        """
        try:
            url = f"{API_ROOT}/reputations/ips/{ip}"

            response = requests.get(
                url=url,
                headers=self.headers,
                params={
                    "details": ",".join(FIELDS),
                    "start": start_time,
                    "end": end_time,
                },
            )

            response.raise_for_status()
            return response.json()

        except requests.HTTPError as error:
            raise ProtectwiseManagerError(error.response.json()["error"]["info"])

        except Exception as error:
            raise ProtectwiseManagerError(
                f"Unable to get reputation of {ip}: {error} {error}"
            )

    def get_domain_reputation(self, domain, start_time, end_time):
        """
        NOTICE - API Endpoint not working!
        Get reputation for a domain
        :param domain: The domain
        :param start_time: (unixtime) Start time to fetch threat intel from
        :param end_time: (unixtime) End time to fetch threat intel from
        :return: {dict} Reputation
        """
        try:
            url = f"{API_ROOT}/reputations/domains/{domain}"

            response = requests.get(
                url=url,
                headers=self.headers,
                params={
                    "details": ",".join(FIELDS),
                    "start": start_time,
                    "end": end_time,
                },
            )

            response.raise_for_status()
            return response.json()

        except requests.HTTPError as error:
            raise ProtectwiseManagerError(error.response.json()["error"]["info"])

        except Exception as error:
            raise ProtectwiseManagerError(
                f"Unable to get reputation of {domain}: {error} {error}"
            )

    def get_file_reputation(self, hash, start_time, end_time):
        """
        NOTICE - API Endpoint not working!
        Get reputation for an hash
        :param hash: The hash
        :param start_time: (unixtime) Start time to fetch threat intel from
        :param end_time: (unixtime) End time to fetch threat intel from
        :return: {dict} Reputation
        """
        try:
            url = f"{API_ROOT}/reputations/files/{hash}"

            response = requests.get(
                url=url,
                headers=self.headers,
                params={
                    "details": ",".join(FIELDS),
                    "start": start_time,
                    "end": end_time,
                },
            )

            response.raise_for_status()
            return response.json()

        except requests.HTTPError as error:
            raise ProtectwiseManagerError(error.response.json()["error"]["info"])

        except Exception as error:
            raise ProtectwiseManagerError(
                f"Unable to get reputation of {hash}: {error} {error}"
            )

    def download_pcap(self, event_id):
        """
        Download Pcap of a specific event by its id
        :param event_id: The event id
        :return: pcap file content
        """
        try:
            url = f"{API_ROOT}/pcaps/events/{event_id}"

            response = requests.get(url=url, headers=self.headers)

            response.raise_for_status()
            return response.content  # PCAP file content

        except requests.HTTPError as error:
            raise ProtectwiseManagerError(error.response.json()["error"]["info"])

        except Exception as error:
            raise ProtectwiseManagerError(
                f"Unable to download pcap for {event_id}: {error} {error}"
            )

    def get_events(self, start_time, end_time):
        """
        Get events in a time frame
        :param start_time: (unixtime) Start time to fetch events from
        :param end_time: (unixtime) End time to fetch events from
        :return: {list} List of events
        """
        try:
            url = f"{API_ROOT}/events"

            response = requests.get(
                url=url,
                headers=self.headers,
                params={"start": start_time, "end": end_time},
            )

            response.raise_for_status()
            return response.json()["events"]

        except requests.HTTPError as error:
            raise ProtectwiseManagerError(error.response.json()["error"]["info"])

        except Exception as error:
            raise ProtectwiseManagerError(f"Unable to get events: {error} {error}")

    def construct_csv(self, results):
        """
        Construct a csv from results
        :param results: The results (list of flat dicts). i.e: list of flat events
        :return: {str} csv formatted string
        """
        csv_output = []
        headers = reduce(set.union, list(map(set, list(map(dict.keys, results)))))

        csv_output.append(",".join(map(str, headers)))

        for result in results:
            csv_output.append(
                ",".join(
                    [
                        s.replace(",", " ")
                        for s in map(str, [result.get(h, None) for h in headers])
                    ]
                )
            )

        return csv_output
