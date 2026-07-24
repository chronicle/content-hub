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
# title           :CiscoAMPManager.py
# description     :This Module contain all Cisco AMP operations functionality
# author          :avital@siemplify.co
# date            :11-04-2018
# python_version  :2.7
# libraries       :requests
# requirements     :
# product_version :1.0
# ============================================================================#

from __future__ import annotations
import requests

from TIPCommon import filter_old_alerts

from .CiscoAMPParser import CiscoAMPParser
from .consts import MAX_EVENTS_PAGE_LIMIT, DEFAULT_EVENTS_PAGE, LIMIT, EVENT_ID_FIELD


class CiscoAMPManagerError(Exception):
    """
    General Exception for CiscoAMP manager
    """

    pass


class CiscoAMPLimitManagerError(Exception):
    """
    Limit Exception for CiscoAMP manager.
    API Clients are allowed to make a limited number of requests every hour.
     Each API response will include HTTP headers detailing the status of
     their rate limit. If the limit is overrun, then an HTTP 429
     Error will be returned.
    """

    pass


class CiscoAMPManager:
    """
    CiscoAMP Manager
    """

    def __init__(
        self, server_address, client_id, api_key, use_ssl=False, siemplify=None
    ):
        self.server_address = server_address
        self.session = requests.Session()
        self.session.auth = (client_id, api_key)
        self.session.verify = use_ssl

        self.parser = CiscoAMPParser()
        self.siemplify = siemplify

    def test_connectivity(self):
        """
        Test connectivity to CiscoAMP
        :return: {bool} True if successful, exception otherwise.
        """
        url = f"{self.server_address}/v1/version"
        response = self.session.get(url)
        self.validate_response(response, "Unable to connect to CiscoAMP.")
        return True

    def get_computer_info_by_ip(self, ip, internal=False):
        """
        Get computer info by ip address (if there are multiple - get the first)
        :param ip: {str} The ip to filter by
        :param internal: {bool} Whether the ip is interanl or external
        :return: {list} List of matching computer infos.
        """
        url = f"{self.server_address}/v1/computers"
        if internal:
            params = {"internal_ip": ip, "limit": LIMIT}

        else:
            params = {"external_ip": ip}

        response = self.session.get(url, params=params)
        self.validate_response(response, f"Unable to get computer info for {ip}")

        self.validate_response_data(response, f"Computer {ip} not found.")

        return response.json().get("data")[0]

    def get_computer_info_by_hostname(self, hostname):
        """
        Get computer info by hostname (if there are multiple - get the first)
        :param hostname: {str} The hostname to filter by
        :return: {list} List of matching computer infos.
        """
        url = f"{self.server_address}/v1/computers"
        params = {"hostname[]": hostname, "limit": LIMIT}

        response = self.session.get(url, params=params)
        self.validate_response(response, f"Unable to get computer info for {hostname}")

        self.validate_response_data(response, f"Computer {hostname} not found.")

        return response.json().get("data")[0]

    def get_computer_info_by_guid(self, guid):
        """
        Get computer info by guid
        :param guid: {str} The guid to filter by
        :return: {dict} List of matching computer infos.
        """
        url = f"{self.server_address}/v1/computers/{guid}"

        response = self.session.get(url)
        self.validate_response(response, f"Unable to get computer info for {guid}")

        self.validate_response_data(response, f"Computer {guid} doesn't exists.")

        return response.json().get("data")

    def get_files_of_file_list(self, guid, include_policies=False):
        """
        Get file of a file list
        :param guid: {str} The guid to filter by
        :param include_policies: {bool} Whether to include the policies in results or not
        :return: {dict} The matching files of the file llist.
        """
        url = f"{self.server_address}/v1/file_lists/{guid}/files"

        response = self.session.get(url)
        self.validate_response(response, f"Unable to get file list {guid}")

        self.validate_response_data(response, f"File list {guid} doesn't exists.")

        data = response.json().get("data")
        # The data includes policies that are compicated and usually not
        # necessary. If include_policies is False, remove it from the results.
        if not include_policies:
            del data["policies"]

        return data

    def add_file_to_list(self, guid, filehash, description="Added by Siemplify"):
        """
        Add a file to a list by the list's guid
        :param guid: {str} The guid of the file list
        :param filehash: {str} The hash to add
        :param description: {str} Description of the file
        :return: {bool} True if successful, exception otherwise.
        """
        url = f"{self.server_address}/v1/file_lists/{guid}/files/{filehash}"
        response = self.session.post(url, json={"description": description})
        self.validate_response(
            response, f"Unable to add file {filehash} to file list {guid}"
        )
        return True

    def remove_file_from_list(self, guid, filehash):
        """
        Add a file to a list by the list's guid
        :param guid: {str} The guid of the file list
        :param filehash: {str} The hash to add
        :param description: {str} Description of the file
        :return: {bool} True if successful, exception otherwise.
        """
        url = f"{self.server_address}/v1/file_lists/{guid}/files/{filehash}"
        response = self.session.delete(url)
        self.validate_response(
            response, f"Unable to delete file {filehash} from file list {guid}"
        )
        return True

    def create_group(self, name, description="Created By Siemplify"):
        """
        Create a group
        :param name: {str} The name of the new group
        :param description: {str} The description of the group
        :return: {dict} res data
        """
        url = f"{self.server_address}/v1/groups"
        response = self.session.post(
            url, json={"name": name, "description": description}
        )
        self.validate_response(response, f"Unable to create group {name}")
        return response.json().get("data")

    def get_groups(self):
        """
        Fetch list of groups.
        :return: {list} List of found groups.
        """
        url = f"{self.server_address}/v1/groups"
        params = {"limit": LIMIT}

        response = self.session.get(url, params=params)
        self.validate_response(response, "Unable to get groups")
        # Get the data (via pagination)
        return self.paginate(url, params, "Unable to get groups")

    def get_policy_info_by_guid(self, guid):
        """
        Get policy info by guid
        :param guid: {str} The guid to filter by
        :return: {dict} The matching policy.
        """
        url = f"{self.server_address}/v1/policies/{guid}"

        response = self.session.get(url)
        self.validate_response(response, f"Unable to get policy {guid}")

        self.validate_response_data(response, f"Policy {guid} doesn't exists.")

        return response.json().get("data")

    def get_simple_custom_detections_by_guid(self, guid):
        """
        Get custom detections file list info by guid
        :param guid: {str} The guid to filter by
        :return: {dict} The matching custom detections file list.
        """
        url = f"{self.server_address}/v1/file_lists/{guid}"

        response = self.session.get(url)
        self.validate_response(response, f"Unable to get file lists {guid}")

        self.validate_response_data(response, f"File list {guid} doesn't exists.")

        return response.json().get("data")

    def get_computer_activity(self, query):
        """
        Search all computers for any events or activities associated with
        a file or network operation by query and return computers matching
        that criteria.
        Aka - get computer that connected to the activity in the query.
        :param query: {str} The query to filter by. For example:
            sovereutilizeignty.com,
            814a37d89a79aa3975308e723bc1a3a67360323b7e3584de00896fe7c59bbb8e,
            75.102.25.76,
            SearchProtocolHost.exe
        :return: {list} List of matching computer infos.
        """
        url = f"{self.server_address}/v1/computers/activity"
        params = {"q": query, "limit": LIMIT}

        computers = []
        for computer in self.paginate(url, params, "Unable to get computer activity"):
            computers.append(
                self.get_computer_info_by_guid(computer.get("connector_guid"))
            )

        return computers

    def get_computer_activity_by_user(self, user):
        """
        Fetch list of computers that have observed activity by given user name.
        :param user: {str} The username
        :return: {list} List of matching computer infos.
        """
        url = f"{self.server_address}/v1/computers/user_activity"
        params = {"q": user, "limit": LIMIT}

        response = self.session.get(url, params=params)
        self.validate_response(
            response, f"Unable to get computer activity by user {user}"
        )

        computers = []
        for computer in self.paginate(
            url, params, f"Unable to get computer activity by user {user}"
        ):
            computers.append(
                self.get_computer_info_by_guid(computer.get("connector_guid"))
            )

        return computers

    def get_simple_custom_detections_by_name(self, name):
        """
        Get custom detections file list by name (if multiple - get the first)
        :param: name {str} The name of the custom detections file list
        :return: {dict} The custom detections file list.
        """
        url = f"{self.server_address}/v1/file_lists/simple_custom_detections"
        params = {"limit": LIMIT, "name": name}

        response = self.session.get(url, params=params)
        self.validate_response(
            response, f"Unable to get custom detections file list {name}"
        )

        self.validate_response_data(
            response, f"Custom detections file list {name} doesn't exists."
        )

        file_list_guid = response.json().get("data")[0]["guid"]
        return self.get_files_of_file_list(file_list_guid)

    def get_application_blocking_by_name(self, name):
        """
        Get application blocking file list by name (if multiple - get the first)
        :param: name {str} The name of the custom detections file list
        :return: {dict} The custom detections file list.
        """
        url = f"{self.server_address}/v1/file_lists/application_blocking"
        params = {"limit": LIMIT, "name": name}

        response = self.session.get(url, params=params)
        self.validate_response(
            response, f"Unable to get application blocking file list {name}"
        )

        self.validate_response_data(
            response, f"Application blocking file list {name} doesn't exists."
        )

        file_list_guid = response.json().get("data")[0]["guid"]
        return self.get_files_of_file_list(file_list_guid)

    def get_file_list_by_name(self, name):
        """
        Get a file list info by name
        :param name: {str} The name to filter by
        :return: {dict} The info of the found file list
        """
        file_list = None

        try:
            file_list = self.get_simple_custom_detections_by_name(name)
        except CiscoAMPManagerError:
            # File list is not a custom detection file list
            pass

        try:
            file_list = self.get_application_blocking_by_name(name)
        except CiscoAMPManagerError:
            # File list is not a application blocking file list
            pass

        if not file_list:
            raise CiscoAMPManagerError(f"File list {name} doesn't exist.")

        return file_list

    def get_policy_by_name(self, name):
        """
        Get policy by name (if multiple - get the first)
        :param: name {str} The name of the policy
        :return: {dict} The policy.
        """
        url = f"{self.server_address}/v1/policies"
        params = {"limit": LIMIT, "name": name}

        response = self.session.get(url, params=params)
        self.validate_response(response, f"Unable to get policy {name}")

        self.validate_response_data(response, f"Policy {name} doesn't exists.")

        policy_guid = response.json().get("data")[0]["guid"]
        return self.get_policy_info_by_guid(policy_guid)

    def get_policies(self):
        """
        Fetch list of policies.
        :return: {list} List of found policies.
        """
        url = f"{self.server_address}/v1/policies"
        params = {"limit": LIMIT}

        response = self.session.get(url, params=params)
        self.validate_response(response, "Unable to get policies")
        return self.paginate(url, params, "Unable to get policies")

    def paginate(self, url, params, error_message):
        """
        Get results with pagination
        :param url: {str} Url to get data from
        :param params: {str} The params of the request
        :param error_message: {str} The error message to display
        :return: {list} The results
        """
        response = self.session.get(url, params=params)
        self.validate_response(response, error_message)

        total = response.json()["metadata"]["results"]["total"]
        data = response.json().get("data")

        while len(data) < total:
            params.update({"offset": params.get("offset", 0) + len(data)})
            response = self.session.get(url, params=params)
            self.validate_response(response, error_message)
            data.extend(response.json().get("data"))

        return data

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            if response.status_code == 429:
                raise CiscoAMPLimitManagerError("API request limit was reached.")

            text = response.content

            try:
                # If CiscoAMP error exists - the details of the error may be found
                # in details of the error.
                if response.json().get("errors"):
                    text = response.json()["errors"][0].get("details")
            except:
                # The error doens't contain details.
                pass

            raise CiscoAMPManagerError(f"{error_msg}: {error} {text}")

    @staticmethod
    def validate_response_data(response, error_msg="Resource not found"):
        """
        Validate that the response contains data
        :param response:
        :param error_msg:
        :return:
        """
        if not response.json().get("data"):
            raise CiscoAMPManagerError(error_msg)

    @staticmethod
    def create_computer_info(computer):
        """
        Create human readble computer info table
        :param computer: {dict} The computer info
        :return: {dict} The table
        """
        return {
            "Id": computer.get("connector_guid"),
            "Hostname": computer.get("hostname"),
            "External IP": computer.get("external_ip"),
            "Internal IPs": ",".join(computer.get("internal_ips", [])),
            "Policy Name": (
                computer["policy"].get("name") if computer.get("policy") else None
            ),
            "Active": computer.get("active"),
            "Operating System": computer.get("operating_system"),
            "Install date": computer.get("install_date"),
            "Connector Version": computer.get("connector_version"),
        }

    def isolate_machine(
        self,
        connector_guid,
        isolation_comment="Isolate Machine",
        unlock_code="unlock_code",
    ):
        """
        Create a group
        :param connector_guid: {str} connector guid of computer which will be isolated
        :param isolation_comment: {str} message describing isolation reason
        :param unlock_code: {str} code for unlock isolation
        :return: {dict} res data
        """
        url = f"{self.server_address}/v1/computers/{connector_guid}/isolation"
        params = {"comment": isolation_comment, "unlock_code": unlock_code}

        response = self.session.put(url, params=params)
        self.validate_response(response, f"Unable to Isolate {connector_guid}")
        return response.json().get("data")

    def unisolate_machine(
        self,
        connector_guid,
        unisolation_comment="Unisolate Machine",
        unlock_code="unlock_code",
    ):
        """
        Create a group
        :param connector_guid: {str} connector guid of computer which will be isolated
        :param unisolation_comment: {str} message describing unisolation reason
        :param unlock_code: {str} code for unlock isolation
        :return: {dict} res data
        """
        url = f"{self.server_address}/v1/computers/{connector_guid}/isolation"
        params = {"comment": unisolation_comment, "unlock_code": unlock_code}

        response = self.session.delete(url, params=params)
        self.validate_response(response, f"Unable to Unisolate {connector_guid}")
        return response.json().get("data")

    def get_events(self, start_date, limit, existing_ids):
        """
        Get oldest events from Cisco AMP
        :param: start_date: {str} Date to query events from. Date time in format of ISO860
        :param: limit: {int} Max events to return
        :param: existing_ids: {[str]} List of already seen event ids
        :return: {[Event]} List of events
        """
        request_url = f"{self.server_address}/v1/events"
        page_size = max(DEFAULT_EVENTS_PAGE, min(limit, MAX_EVENTS_PAGE_LIMIT))
        params = {"limit": page_size, "offset": 0, "start_date": start_date}
        response = self.session.get(url=request_url, params=params)
        self.validate_response(response, error_msg="Failed to get events")
        total_events = self.parser.get_total_events(response.json())

        if total_events > page_size:
            filtered_alerts = []
            params.update({"offset": total_events - page_size})
            response = self.session.get(url=request_url, params=params)
            self.validate_response(
                response,
                error_msg=f"Failed to get events from offset: {total_events - page_size}",
            )
            events = self.parser.build_event_obj_list(response.json())
            filtered_alerts.extend(
                list(
                    reversed(
                        filter_old_alerts(
                            siemplify=self.siemplify,
                            alerts=events,
                            existing_ids=existing_ids,
                            id_key=EVENT_ID_FIELD,
                        )
                    )
                )
            )
            prev_link = self.parser.get_prev_events_link(response.json())

            while len(filtered_alerts) <= limit and prev_link:
                response = self.session.get(url=prev_link)
                self.validate_response(response, error_msg="Failed to get events")
                events = self.parser.build_event_obj_list(response.json())
                filtered_alerts.extend(
                    list(
                        reversed(
                            filter_old_alerts(
                                siemplify=self.siemplify,
                                alerts=events,
                                existing_ids=existing_ids,
                                id_key=EVENT_ID_FIELD,
                            )
                        )
                    )
                )
                prev_link = self.parser.get_prev_events_link(response.json())

        else:
            filtered_alerts = list(
                reversed(
                    filter_old_alerts(
                        siemplify=self.siemplify,
                        alerts=self.parser.build_event_obj_list(response.json()),
                        existing_ids=existing_ids,
                        id_key=EVENT_ID_FIELD,
                    )
                )
            )

        return filtered_alerts[:limit] if limit is not None else filtered_alerts
