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
import datetime
import time
from typing import Optional
from urllib.parse import urljoin
import requests
from .CBCloudParser import CBCloudParser
from soar_sdk.SiemplifyDataModel import EntityTypes
from .utils import LOGGER, remove_none_values
from .exceptions import (
    CBCloudException,
    CBCloudUnauthorizedError,
    CBCloudTimeoutException,
)
from .constants import (
    HTTP_STATUS_CODE_BAD_REQUEST,
    HTTP_STATUS_CODE_UNAUTHORIZED,
    SEVERITY_FILTER_MAPPING,
)


SLEEP_TIME = 1
DEFAULT_PAGE_SIZE = 100
MIN_LIMIT = 100
MAX_ENRICHED_EVENTS_PER_REQUEST = 10
NOT_FOUND_CODE = "NOT_FOUND"
BYPASS = "BYPASS"
DISMISSED_STATE = "CLOSED"
QUARANTINE = "QUARANTINE"
UPDATE_POLICY = "UPDATE_POLICY"
BACKGROUND_SCAN = "BACKGROUND_SCAN"

API_ENDPOINTS = {
    "ping": "/api/alerts/v7/orgs/{org_key}/alerts/_search",
    "alerts_search": "/api/alerts/v7/orgs/{org_key}/alerts/_search",
    "dismiss_alert": "/api/alerts/v7/orgs/{org_key}/alerts/workflow",
    "get_specific_alert": "/api/alerts/v7/orgs/{org_key}/alerts/{alert_id}",
    "get_updated_alerts": "/api/alerts/v7/orgs/{org_key}/alerts/_search",
    "create-job-to-search-events": "/api/investigate/v2/orgs/{org_key}/observations"
                                   "/search_jobs",
    "get-job-search-results-events": "/api/investigate/v2/orgs/{org_key}/observations"
                                     "/search_jobs/{job_id}/results",
    "is-job-search-events-completed": "/api/investigate/v1/orgs/{org_key}/enriched_events/search_jobs/{job_id}",
    "is-job-search-detailed-events-completed": "/api/investigate/v2/orgs/{org_key}/enriched_events/detail_jobs/{job_id}",
    "create-job-for-detailed-events": "/api/investigate/v2/orgs/{org_key}/observations"
                                      "/detail_jobs",
    "get-detailed-events-results": "/api/investigate/v2/orgs/{org_key}/observations"
                                   "/detail_jobs/{job_id}/results",
    "search-devices": "appservices/v6/orgs/{org_key}/devices/_search",
    "app-service-device-action": "appservices/v6/orgs/{org_key}/device_actions",
    "create_job_to_search_processes": "/api/investigate/v2/orgs/{org_key}/processes/search_jobs",
    "get_results_of_search_of_events": "/api/investigate/v2/orgs/{org_key}/processes/search_jobs/{job_id}/results",
    "get_detailed_events_information": "/api/investigate/v2/orgs/{org_key}/processes/detail_jobs",
    "get_status_of_search_process": "/api/investigate/v1/orgs/{org_key}/processes/search_jobs/{job_id}",
    "create_reputation_override": "/appservices/v6/orgs/{org_key}/reputations/overrides",
    "search_reputation_overrides": "/appservices/v6/orgs/{org_key}/reputations/overrides/_search",
    "delete_reputation_override": "/appservices/v6/orgs/{org_key}/reputations/overrides/{rep_override_id}",
    "get_vulnerability_details": "/vulnerability/assessment/api/v1/orgs/{org_key}/devices/{device_id}/vulnerabilities/_search",
}


class CBCloudManager:
    def __init__(
        self,
        api_root,
        org_key,
        api_id,
        api_secret_key,
        verify_ssl=False,
        logger=None,
        force_check_connectivity=False,
    ):
        self.session = requests.session()
        self.api_root = self._get_adjusted_root_url(api_root)
        self.org_key = org_key
        self.session.headers["X-Auth-Token"] = f"{api_secret_key}/{api_id}"
        self.session.verify = verify_ssl
        self.parser = CBCloudParser()
        self.logger = LOGGER(logger)

        if force_check_connectivity:
            self.test_connectivity()

    @classmethod
    def validate_organization_error(cls, response):
        try:
            response_json = response.json()
        except:
            # Unable to parse out the JSON - let the error be raised as any regular error
            return

        not_found = response.status_code == 404
        not_found_code = response_json.get("error_code") == NOT_FOUND_CODE
        invalid_org = response_json.get("resource_type") == "org"

        if not_found and invalid_org and not_found_code:
            raise CBCloudUnauthorizedError(
                "Invalid organization ID. Please check given credentials."
            )

    @classmethod
    def validate_response(cls, response, error_msg="An error occurred"):
        """
        Validate response
        :param response: {requests.Response} The response to validate
        :param error_msg: {str} Default message to display on error
        """
        try:
            if response.status_code == HTTP_STATUS_CODE_UNAUTHORIZED:
                raise CBCloudUnauthorizedError(
                    "Unauthorized. Please check given credentials."
                )

            if (
                response.status_code == HTTP_STATUS_CODE_BAD_REQUEST
                and "message" in response.json()
            ):
                error = response.json().get("message")
                raise CBCloudException(f"{error_msg}: {error}")

            cls.validate_organization_error(response)

            response.raise_for_status()

        except requests.HTTPError as error:
            raise CBCloudException(f"{error_msg}: {error} {response.content}")

    @staticmethod
    def _get_adjusted_root_url(api_root):
        return api_root[:-1] if api_root.endswith("/") else api_root

    def test_connectivity(self):
        """
        Test connectivity to CB Cloud
        :return: {bool} True if successful, exception otherwise
        """
        data = {"rows": 1, "start": 1}
        response = self.session.post(self._get_full_url("ping"), json=data)
        self.validate_response(response, "Unable to connect to CB Cloud")

        return True

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier
        :param url_id: {str} the id of url
        :param kwargs: {dict} variables passed for string formatting
        :return: {str} the full url
        """
        if "org_key" not in kwargs:
            kwargs["org_key"] = self.org_key

        return urljoin(self.api_root, API_ENDPOINTS[url_id].format(**kwargs))

    def dismiss_alert(
        self,
        alert_id: str,
        remediation_state: str,
        determination: str,
        comment: str = "Closed programmatically from Siemplify Server.",
    ) -> None:
        """Dismiss an alert by its ID

        Args:
            alert_id (str): The ID of the alert.
            remediation_state (str): Description or justification for the change.
            determination (str): Determination for the alert.
            comment: (str) Comment to include with operation
        """
        data = {
            "criteria": {"id": [alert_id]},
            "determination": determination,
            "closure_reason": remediation_state,
            "status": DISMISSED_STATE,
            "note": comment,
        }
        results = self.session.post(self._get_full_url("dismiss_alert"), json=data)
        self.validate_response(results)

        return True

    def validate_alert(self, alert_id: str) -> None:
        """Validate details of a alert by its ID.

        Args:
            alert_id (str): The unique identifier of the alert to validate.
        """
        url = self._get_full_url("get_specific_alert", alert_id=alert_id)
        results = self.session.get(url)
        self.validate_response(results)

    def match_device_host_name(self, device, starts_with_name):
        """
        Check if hostname matches with device name
        :param device: {Device} instance
        :param starts_with_name: {string} The starting string of device name
        :return: [{Device}] if match results None otherwise
        """
        name = device.name.lower()
        starts_with = name.startswith(starts_with_name.lower())

        if not starts_with:
            return False

        if starts_with and len(name) == len(starts_with_name):
            return True

        return starts_with and name[len(starts_with_name)] == "."

    def search_devices(self, **kwargs):
        """
        Search for hosts in your environment by platform, hostname, IP, and other criteria.
        :return: {list} of device details {dict}
        """
        starts_with_name = kwargs.get("starts_with_name")
        query = kwargs.get("query", "")
        if starts_with_name:
            query = kwargs.pop("starts_with_name")

        devices = self.get_devices(query=query, limit=kwargs.get("limit"))

        if starts_with_name:
            filtered_devices = [
                device
                for device in devices
                if self.match_device_host_name(device, starts_with_name)
            ]
            return (
                sorted(filtered_devices, key=lambda machine: machine.last_contact_time)
                if filtered_devices
                else None
            )

        return sorted(devices, key=lambda machine: machine.last_contact_time)

    def get_devices_by_name(self, starts_with_name, limit=None):
        """
        Search for hosts in your environment by platform, hostname with entity identifier
        :param starts_with_name: {string} The starting string of device name
        :param limit: {string} Limit of returning items
        :return: [{Device}] if match results None otherwise
        """
        devices = self.get_devices(query=starts_with_name, limit=limit)

        filtered_devices = [
            device
            for device in devices
            if self.match_device_host_name(device, starts_with_name)
        ]

        return filtered_devices if filtered_devices else None

    def get_devices(
        self, query=None, sort_by="last_contact_time", sort_order="DESC", limit=None
    ):
        """
        Get an device by query
        :param query: {str} The query to use for
        :param sort_by: {str} The sorting key
        :param sort_order: {str} The sorting logic asc or desc
        :param limit: {int} Limit param
        :return: {[Device]} The matching endpoints
        """
        payload = {"query": query, "sort": [{"field": sort_by, "order": sort_order}]}

        devices = self._paginate_results(
            method="POST",
            url=self._get_full_url("search-devices", org_key=self.org_key),
            err_msg="Unable to get devices",
            limit=limit,
            body=payload,
        )

        return self.parser.build_results(
            devices, "build_siemplify_device_obj", pure_data=True
        )

    def create_policy_update_task(self, policy_id, device_id):
        """
        Create a policy update task for a device
        :param policy_id: {str} The ID of the policy to update to
        :param device_id: {str} The ID of the device to update
        :return: {bool} True if successful, exception otherwise
        """
        json_payload = {
            "action_type": UPDATE_POLICY,
            "device_id": [device_id],
            "options": {"policy_id": policy_id},
        }
        response = self.session.post(
            self._get_full_url("app-service-device-action"), json=json_payload
        )
        self.validate_response(
            response, f"Unable to create policy update task for device {device_id}"
        )

        return True

    def create_quarantine_task(self, device_id):
        """
        Create a quarantine task for a device
        :param device_id: {str} The ID of the device to update
        :return: {bool} True if successful, exception otherwise
        """
        json_payload = {
            "action_type": QUARANTINE,
            "device_id": [device_id],
            "options": {"toggle": "ON"},
        }
        response = self.session.post(
            self._get_full_url("app-service-device-action"), json=json_payload
        )
        self.validate_response(
            response, f"Unable to create quarantine task for device {device_id}"
        )

        return True

    def create_unquarantine_task(self, device_id):
        """
        Create a unquarantine task for a device
        :param device_id: {str} The ID of the device to update
        :return: {bool} True if successful, exception otherwise
        """
        json_payload = {
            "action_type": QUARANTINE,
            "device_id": [device_id],
            "options": {"toggle": "OFF"},
        }
        response = self.session.post(
            self._get_full_url("app-service-device-action"), json=json_payload
        )
        self.validate_response(
            response, f"Unable to create unquarantine task for device {device_id}"
        )

        return True

    def create_enable_bypass_mode_task(self, device_id):
        """
        Create a enable bypass mode task for a device
        :param device_id: {str} The ID of the device to update
        :return: {bool} True if successful, exception otherwise
        """
        json_payload = {
            "action_type": BYPASS,
            "device_id": [device_id],
            "options": {"toggle": "ON"},
        }
        response = self.session.post(
            self._get_full_url("app-service-device-action"), json=json_payload
        )
        self.validate_response(
            response, f"Unable to create enable bypass mode task for device {device_id}"
        )

        return True

    def create_disable_bypass_mode_task(self, device_id):
        """
        Create a disable bypass mode task for a device
        :param device_id: {str} The ID of the device to update
        :return: {bool} True if successful, exception otherwise
        """
        json_payload = {
            "action_type": BYPASS,
            "device_id": [device_id],
            "options": {"toggle": "OFF"},
        }
        response = self.session.post(
            self._get_full_url("app-service-device-action"), json=json_payload
        )
        self.validate_response(
            response,
            f"Unable to create disable bypass mode task for device {device_id}",
        )

        return True

    def create_background_scan_task(self, device_id):
        """
        Create a background scan task for a device
        :param device_id: {str} The ID of the device to update
        :return: {bool} True if successful, exception otherwise
        """
        json_payload = {
            "action_type": BACKGROUND_SCAN,
            "device_id": [device_id],
            "options": {"toggle": "ON"},
        }
        response = self.session.post(
            self._get_full_url("app-service-device-action"), json=json_payload
        )
        self.validate_response(
            response, f"Unable to create background scan task for device {device_id}"
        )

        return True

    def _paginate_results(
        self,
        method,
        url,
        params=None,
        body=None,
        limit=None,
        err_msg="Unable to get results",
    ):
        """
        Paginate the results of a job
        :param method: {str} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} The url to send request to
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param limit: {int} The limit of the results to fetch
        :param err_msg: {str} The message to display on error
        :return: {list} List of results
        """
        if body is None:
            body = {}

        body.update(
            {
                "start": 1,
                "rows": min(DEFAULT_PAGE_SIZE, limit) if limit else DEFAULT_PAGE_SIZE,
            }
        )

        response = self.session.request(method, url, params=params, json=body)
        self.validate_response(response, err_msg)
        results = self.parser.get_results(response.json())

        while True:
            if limit and len(results) >= limit:
                break

            if not self.parser.get_results(response.json()):
                break

            body.update({"start": len(results) + 1})

            response = self.session.request(method, url, params=params, json=body)
            self.validate_response(response, err_msg)
            results.extend(self.parser.get_results(response.json()))

        return results[:limit] if limit else results

    def get_alerts(
        self,
        start_time=None,
        end_time=None,
        min_severity=None,
        sort_by="first_event_timestamp",
        sort_order="ASC",
        workflows=None,
        limit=None,
    ):
        """
        Get alerts
        :param start_time: {str} Get only alerts that were created after the passed time. I,e: 2020-04-01T05:32:53.214Z
        :param end_time: {str} Get only alerts that were created before the passed time. I,e: 2020-04-01T05:32:53.214Z
        :param min_severity: {int} The minimum severity of the alerts
        :param sort_by: {str} The field to sort by
        :param sort_order: {str} The order of the sorting (ASC/DESC)
        :param workflows: {list} List of workflow statuses to filter by
        :param limit: {int} Max amount of alerts to fetch
        :return: {[Alert]} The matching alerts
        """
        criteria_payload = {
            "workflow_status": workflows,
            "minimum_severity": min_severity,
        }

        criteria_payload = {
            key: value for key, value in criteria_payload.items() if value is not None
        }
        if start_time or end_time:
            time_range = {}
            if start_time:
                time_range["start"] = start_time
            if end_time:
                time_range["end"] = end_time

        payload = {
            "sort": [{"field": sort_by, "order": sort_order}],
            "criteria": criteria_payload,
            "time_range": time_range,
        }

        alerts = self._paginate_results(
            "POST",
            url=self._get_full_url("alerts_search"),
            err_msg="Unable to get alerts",
            limit=max(limit, MIN_LIMIT),
            body=payload,
        )
        if self.logger:
            self.logger.info(f"Total loaded alerts: {len(alerts)}")

        return self.parser.build_results(
            alerts, method="build_siemplify_alert_obj", pure_data=True
        )

    def get_alerts_by_id(self, ids, limit):
        """
        Get updated alerts
        :param ids: {list} List of alert ids to fetch
        :param limit: {int} The maximum number of alerts to fetch
        :return: {[datamodels.Alert]} The matching alerts
        """
        payloads_for_ids = {"criteria": {"id": ids}, "rows": limit, "start": 1}
        response = self.session.post(
            url=self._get_full_url("alerts_search"), json=payloads_for_ids
        )
        alerts = self.parser.get_results(response.json())
        return [self.parser.build_siemplify_alert_obj(alert) for alert in alerts]

    def get_updated_alerts(
        self,
        start_time=None,
        end_time=None,
        min_severity=None,
        sort_by="first_event_timestamp",
        sort_order="ASC",
        workflows=None,
        limit=None,
    ):
        """
        Get updated alerts
        :param start_time: {str} Get only alerts that were updated after the passed time. I,e: 2020-04-01T05:32:53.214Z
        :param end_time: {str} Get only alerts that were updated before the passed time. I,e: 2020-04-01T05:32:53.214Z
        :param min_severity: {int} The minimum severity of the alerts
        :param sort_by: {str} The field to sort by
        :param sort_order: {str} The order of the sorting (ASC/DESC)
        :param workflows: {list} List of workflow statuses to filter by
        :param limit: {int} Max amount of alerts to fetch
        :return: {[datamodels.Alert]} The matching alerts
        """
        workflows = workflows or []
        payload = {"sort": [{"field": sort_by, "order": sort_order}], "criteria": {}}

        if workflows:
            payload["criteria"]["workflow_status"] = workflows

        if min_severity:
            payload["criteria"]["minimum_severity"] = min_severity

        if start_time or end_time:
            time_range = {}
            if start_time:
                time_range["start"] = start_time
            if end_time:
                time_range["end"] = end_time

            payload["time_range"] = time_range

        url = self._get_full_url(
            "get_updated_alerts", api_root=self.api_root, org_key=self.org_key
        )
        alerts = self._paginate_results(
            method="POST",
            url=url,
            err_msg="Unable to get alerts",
            limit=max(limit, MIN_LIMIT),
            body=payload,
        )

        return [self.parser.build_siemplify_alert_obj(alert) for alert in alerts]

    def is_search_process_completed(self, job_id):
        """
        Check if a search job for events has completed
        :param job_id: {str} job id
        :return: {bool} True if job completed, otherwise false
        """
        response = self.session.get(
            url=self._get_full_url("get_status_of_search_process", job_id=job_id)
        )
        self.validate_response(
            response, error_msg=f"Unable to get search job status for job id {job_id}"
        )
        completed, contacted = self.parser.get_job_statuses(response.json())

        return completed == contacted

    def get_events_by_job_id(self, job_id, time_out_in_seconds=None):
        """
        Get events of search job with id <job_id>
        :param job_id: {str} the job id of the search
        :param time_out_in_seconds: {str} timeout seconds
        :return: {Event}
        """
        while not self.is_search_process_completed(job_id):
            self.pause_execution(job_id, time_out_in_seconds)

        response = self.session.get(
            url=self._get_full_url("get_results_of_search_of_events", job_id=job_id)
        )
        self.validate_response(
            response, f"Unable to job search processes results for job id {job_id}"
        )

        return self.parser.build_siemplify_event_obj(response.json())

    def get_detailed_events_by_job_id(self, job_id, time_out_in_seconds=None):
        """
        Get events of search job with id <job_id>
        :param job_id: {str} the job id of the search
        :param time_out_in_seconds: {str} timeout seconds
        :return: {DetailedEvent}
        """
        while not self.is_search_process_completed(job_id):
            self.pause_execution(job_id, time_out_in_seconds)

        response = self.session.get(
            url=self._get_full_url("get_results_of_search_of_events", job_id=job_id)
        )
        self.validate_response(
            response, f"Unable to job search events results for job id {job_id}"
        )

        return self.parser.build_siemplify_detailed_event_obj(response.json())

    def pause_execution(self, job_id, time_out_in_seconds=None):
        """
        Pause execution
        :param job_id: {str} the job id of the search
        :param time_out_in_seconds: {str} process name
        """
        time.sleep(SLEEP_TIME)
        if time_out_in_seconds:
            timeout_time = datetime.datetime.now() + datetime.timedelta(
                seconds=time_out_in_seconds
            )
            if datetime.datetime.now() >= timeout_time:
                raise CBCloudTimeoutException(
                    f"Timeout fetching job search status for job id: {job_id}"
                )

    def get_events_by_process_name(
        self, process_name, entity_type, start=None, rows=None
    ):
        """
        Get events for alert for time
        :param process_name: {str} process name
        :param entity_type: {str} entity type
        :param start: {int} start offset of the events
        :param rows: {int} number of events to return from the offset
        :return: {Event}
        """
        job_id = self.create_job_to_search_processes(
            process_name=process_name,
            entity_type=entity_type,
            start=start if start is not None else 0,
            rows=min(DEFAULT_PAGE_SIZE, rows) if rows else DEFAULT_PAGE_SIZE,
        )

        return self.get_events_by_job_id(job_id)

    def get_detailed_events_information(self, process_guids):
        """
        Create a job for detailed events information
        :param process_guids: {list} list of process guids
        :return: {DetailedEvent}
        """
        payload = {"process_guids": process_guids}
        response = self.session.post(
            url=self._get_full_url("get_detailed_events_information"), json=payload
        )
        self.validate_response(
            response,
            f"Unable to create job to get detailed information for events for "
            f"process_guids {process_guids}",
        )
        job_id = self.parser.get_job_id(response.json())

        return self.get_detailed_events_by_job_id(job_id)

    def create_job_to_search_processes(
        self,
        process_name,
        entity_type,
        start=None,
        rows=None,
        sort_field="device_timestamp",
        sort_order="asc",
    ):
        """
        Create a job to search for events for the given legacy alert ids
        :param process_name: {list} list of entity identifier
        :param entity_type: {str} entity type
        :param start: {int} start offset of the events
        :param rows: {int} number of events to return from the offset
        :param sort_field: {str} sort filter field
        :param sort_order: {str} sort by asc or desc
        :return: {str} job id if job created successfully, otherwise return None
            or raise CBCloudException / CBCloudUnauthorizedError exceptions
        """
        query_payload = {
            EntityTypes.ADDRESS: f"device_external_ip:{process_name} || device_internal_ip:{process_name} || "
            f"event_network_local_ipv4:{process_name} || event_network_remote_ipv4:{process_name}",
            EntityTypes.FILEHASH: f"process_hash:{process_name}",
            EntityTypes.HOSTNAME: f"device_name:{process_name}",
            EntityTypes.USER: f"process_username:{process_name}",
            EntityTypes.PROCESS: "",
        }
        payload = {
            "criteria": (
                {"process_name": [process_name]}
                if entity_type == EntityTypes.PROCESS
                else {}
            ),
            "query": query_payload[entity_type] if query_payload[entity_type] else "",
            "sort": [{"field": sort_field, "order": sort_order}],
            "start": start,
            "rows": rows,
        }

        payload = self.validate_dict(payload)

        response = self.session.post(
            url=self._get_full_url("create_job_to_search_processes"), json=payload
        )
        self.validate_response(
            response,
            f"Unable to create job to search processes for entity {process_name}",
        )

        return self.parser.get_job_id(response.json())

    @staticmethod
    def validate_dict(dictionary):
        """
        Validate dictionary by value
        :param dictionary: {dict} dict to be validated
        :return: {str} validated dict
        """
        return {key: value for key, value in dictionary.items() if value}

    def create_job_to_search_events(
        self, alert_ids, start_time, end_time, sort_order="asc", start=None, rows=None
    ):
        """
        Create a job to search for events for the given legacy alert ids
        :param alert_ids: {list} list of legacy alert ids. Each alert id represented as unicode
        :param start_time: {str} Get only alerts that were created after the passed time. I,e: 2020-04-01T05:32:53.214Z
        :param end_time: {str} Get only alerts that were created before the passed time. I,e: 2020-04-01T05:32:53.214Z
        :param sort_order: {str} Sort order by ascending or descending order "asc" or "desc" respectively
        :param start: {int} start offset of the events
        :param rows: {int} number of events to return from the offset
        :return: {str} job id if job created successfully, otherwise return None
            or raise CBCloudException / CBCloudUnauthorizedError exceptions
        """
        payload = {
            "fields": ["*"],
            "sort": [{"field": "device_timestamp", "order": sort_order}],
            "criteria": {"alert_id": alert_ids if alert_ids else []},
        }

        if start_time or end_time:
            payload["time_range"] = {}

        if start_time:
            payload["time_range"]["start"] = start_time

        if end_time:
            payload["time_range"]["end"] = end_time

        if start:
            payload["start"] = start

        if rows:
            payload["rows"] = rows

        response = self.session.post(
            url=self._get_full_url(
                "create-job-to-search-events",
                api_root=self.api_root,
                org_key=self.org_key,
            ),
            json=payload,
        )
        self.validate_response(
            response,
            f"Unable to create job to search events for alert ids {', '.join(alert_ids)}",
        )

        return response.json().get("job_id")

    def get_job_search_results_events(self, job_id):
        """
        Get events results of search job with id <job_id>
        :param job_id: {str} job id of the search
        :return: {[datamodels.EnrichedEvent]} List of result enriched events.
             or raise CBCloudException / CBCloudUnauthorizedError exceptions
        """
        response = self.session.get(
            url=self._get_full_url(
                "get-job-search-results-events",
                api_root=self.api_root,
                org_key=self.org_key,
                job_id=job_id,
            )
        )
        self.validate_response(
            response,
            error_msg=f"Unable to job search events results for job id {job_id}",
        )
        return self.parser.build_results(
            response.json(), "build_siemplify_enriched_event_obj", data_key="results"
        )

    def get_events_by_alert_id(
        self,
        alert_id,
        start_time=None,
        end_time=None,
        max_events_to_return=None,
        existing_events=None,
    ):
        """
        Get events for alert for time
        :param alert_id: {str} alert id
        :param start_time: {str} Get only alerts that were created after the passed time. I,e: 2020-04-01T05:32:53.214Z
        :param end_time: {str} Get only alerts that were created before the passed time. I,e: 2020-04-01T05:32:53.214Z
        :param max_events_to_return: {int} max amount of events to return
        :param existing_events: {list} list of existing events ids to filter out of the fetched events
        :return: {[datamodels.EnrichedEvent]} list of EnrichedEvent datamodels for an alert
        """
        existing_events = existing_events or []
        job_id = self.create_job_to_search_events(
            alert_ids=[alert_id],
            start_time=start_time,
            end_time=end_time,
            start=0,
            rows=(
                min(DEFAULT_PAGE_SIZE, max_events_to_return)
                if max_events_to_return
                else DEFAULT_PAGE_SIZE
            ),
        )

        if self.logger:
            self.logger.info(f"Successfully created job {job_id} to search for events")

        return self.get_events_search_results(
            alert_id,
            job_id,
            start_time,
            end_time,
            max_events_to_return,
            existing_events,
        )

    def check_search_status_and_get_results(self, job_id):
        """
        Check if a search job for events has completed and return search results
        :param job_id: {str} job id
        :return: {([datamodels.EnrichedEvent], int)} List of enriched events and number of found results if job completed, otherwise None
        """
        response = self.session.get(
            url=self._get_full_url(
                "get-job-search-results-events",
                api_root=self.api_root,
                org_key=self.org_key,
                job_id=job_id,
            )
        )
        self.validate_response(
            response, error_msg=f"Unable to get search job status for job id {job_id}"
        )
        json_response = response.json()

        if self.parser.get_completed_status(
            json_response
        ) == self.parser.get_contacted_status(json_response):
            return self.parser.build_results(
                response.json(),
                "build_siemplify_enriched_event_obj",
                data_key="results",
            ), self.parser.get_found_number(response.json())

        return None, None

    def check_detailed_search_status_and_get_results(self, job_id):
        """
        Check if a search for detailed events information has completed and return search results
        :param job_id: {str} job id
        :return: {[datamodels.EnrichedEvent]} List of enriched events if job completed, otherwise None
        """
        response = self.session.get(
            url=self._get_full_url(
                "get-detailed-events-results",
                api_root=self.api_root,
                org_key=self.org_key,
                job_id=job_id,
            )
        )
        self.validate_response(
            response, error_msg=f"Unable to get search job status for job id {job_id}"
        )
        response_json = response.json()

        if response_json.get("completed", 1) == response_json.get("contacted", 0):
            # We sort the resulting array to ensure that if there is a duplicate events with same ids
            # the most recent one would be first in this list when iterating through
            enriched_events = sorted(
                self.parser.build_results(
                    response_json,
                    "build_siemplify_enriched_event_obj",
                    data_key="results",
                ),
                key=lambda x: x.backend_timestamp,
                reverse=True,
            )
            # Once we convert resulting list into set all duplicates would be removed as both
            # __hash__ and __eq__ function of resulting event object are caluclated based on it's ID
            return list(set(enriched_events))

    def get_events_search_results(
        self,
        alert_id,
        job_id,
        start_time,
        end_time,
        limit=None,
        existing_events=None,
        time_out_in_seconds=None,
    ):
        """
        Retrieves events from a created job search with job id <job_id>
        :param alert_id: {str} the alert id to retrieve events from
        :param job_id: {str} job id to retrieve events from
        :param start_time: {str} Get only alerts that were created after the passed time. I,e: 2020-04-01T05:32:53.214Z
        :param end_time: {str} Get only alerts that were created before the passed time. I,e: 2020-04-01T05:32:53.214Z
        :param limit: {int} the limit number of events to return
        :param existing_events: {[unicode]} list of event ids
        :param time_out_in_seconds: {int} Timeout for the search of the events
        :return: {[datamodels.EnrichedEvent]} list of enriched events
        """
        existing_events = existing_events or []
        alert_events = None
        total_events_count = 0

        while alert_events is None:
            alert_events, total_events_count = self.check_search_status_and_get_results(
                job_id
            )
            time.sleep(SLEEP_TIME)
            if time_out_in_seconds:
                timeout_time = datetime.datetime.now() + datetime.timedelta(
                    seconds=time_out_in_seconds
                )
                if datetime.datetime.now() >= timeout_time:
                    raise CBCloudTimeoutException(
                        f"Timeout fetching job search status for job id: {job_id}"
                    )

        if self.logger:
            self.logger.info(f"Total events results: {total_events_count}")

        filtered_events = set(
            [event for event in alert_events if event.id not in existing_events]
        )

        while len(alert_events) < total_events_count:  # fetch more available events
            if len(filtered_events) >= limit:
                break

            start = len(alert_events)  # advance offset
            rows = (
                min(MAX_ENRICHED_EVENTS_PER_REQUEST, limit - len(filtered_events))
                if filtered_events
                else MAX_ENRICHED_EVENTS_PER_REQUEST
            )

            if self.logger:
                self.logger.info(
                    f"Fetching more events results. Fetched {len(alert_events)}/{total_events_count}"
                )

            more_events = self.get_events_by_range(
                alert_id, start_time, end_time, start, rows
            )

            if not more_events:
                break

            alert_events.extend(more_events)
            filtered_events.update(
                [event for event in more_events if event.id not in existing_events]
            )

        filtered_events_sliced = sorted(
            filtered_events, key=lambda event: event.backend_timestamp, reverse=True
        )[:limit]
        if self.logger:
            self.logger.info(f"Total new events found: {len(filtered_events_sliced)}")

        return filtered_events_sliced

    def get_events_by_range(
        self, alert_id, start_time, end_time, start, rows, time_out_in_seconds=None
    ):
        """
        Get events by range
        :param alert_id: {str} alert id
        :param start_time: {str} Get only alerts that were created after the passed time. I,e: 2020-04-01T05:32:53.214Z
        :param end_time: {str} Get only alerts that were created before the passed time. I,e: 2020-04-01T05:32:53.214Z
        :param start: {int} the start offset of the events
        :param rows: {int} the number of events to return from the offset
        :param time_out_in_seconds: {int} Timeout for the search of the events
        :return: {[datamodels.EnrichedEvent]} list of enriched events
            raise CBCloudTimeoutException if the job to created to get events timed out (exceeds the time_out_in_seconds param)
        """
        job_id = self.create_job_to_search_events(
            alert_ids=[alert_id],
            start_time=start_time,
            end_time=end_time,
            start=start,
            rows=rows,
        )

        alert_events = None
        # Wait for the job to complete
        while alert_events is None:
            alert_events, total_events_count = self.check_search_status_and_get_results(
                job_id
            )
            time.sleep(SLEEP_TIME)
            if time_out_in_seconds:
                timeout_time = datetime.datetime.now() + datetime.timedelta(
                    seconds=time_out_in_seconds
                )
                if datetime.datetime.now() >= timeout_time:
                    raise CBCloudTimeoutException(
                        f"Timeout fetching job search status for job id: {job_id}"
                    )

        return alert_events

    def create_job_for_detailed_events(self, events_ids):
        """
        Create a job for detailed events information
        :param events_ids: {[unicode]} list of event ids. Each event id represented as unicode
        :return: {str} job id of the created search job
            or raise CBCloudException / CBCloudUnauthorizedError exceptions
        """
        payload = {"observation_ids": events_ids if events_ids else []}
        response = self.session.post(
            url=self._get_full_url(
                "create-job-for-detailed-events",
                api_root=self.api_root,
                org_key=self.org_key,
            ),
            json=payload,
        )
        self.validate_response(
            response,
            f"Unable to create job to get detailed information for events for ids {', '.join(events_ids)}",
        )

        return response.json().get("job_id")

    def get_events_detailed_information(self, event_ids=None, time_out_in_seconds=None):
        """
        Get enriched events information for event ids
        :param event_ids: {list} list of event ids
        :param time_out_in_seconds: {int} time out in seconds for the job to get detailed events information
        :return: {list} List of EnrichedEvent model instance or raise CBCloudTimeoutException if the job timed out
        """
        if not event_ids:
            return []

        job_id = self.create_job_for_detailed_events(events_ids=event_ids)

        if self.logger:
            self.logger.info(f"Created job {job_id} for detailed events.")

        detailed_events = None
        while detailed_events is None:
            detailed_events = self.check_detailed_search_status_and_get_results(job_id)
            time.sleep(SLEEP_TIME)
            if time_out_in_seconds:
                timeout_time = datetime.datetime.now() + datetime.timedelta(
                    seconds=time_out_in_seconds
                )
                if datetime.datetime.now() >= timeout_time:
                    raise CBCloudTimeoutException(
                        f"Timeout fetching job search status for job id: {job_id}"
                    )

        return detailed_events

    def create_it_tool_reputation_override(
        self,
        override_list,
        path,
        description=None,
        include_child_processes: Optional[bool] = False,
    ):
        """
        Create a new reputation override for IT Tool
        :param override_list: {str} The override list to add a new reputation
        :param description: {str} Justification for override
        :param path: {str} Path to the file or directory where the IT tool(s) exist on disk.
        :param include_child_processes: {bool} True if to Include tool's child processes on approved list, otherwise False
        :return: {OverriddenITToolReputation} OverriddenITToolReputation datamodel object
        """
        response = self.session.post(
            url=self._get_full_url(
                "create_reputation_override",
                api_root=self.api_root,
                org_key=self.org_key,
            ),
            json=remove_none_values(
                {
                    "description": description,
                    "override_list": override_list,
                    "override_type": "IT_TOOL",
                    "path": path,
                    "include_child_processes": include_child_processes,
                }
            ),
        )
        self.validate_response(
            response,
            f"Unable to create IT Tool reputation override for path {path} in list {override_list}",
        )
        return self.parser.build_it_tool_reputation_override_obj(response.json())

    def create_certificate_reputation_override(
        self, override_list, signed_by, certificate_authority=None, description=None
    ):
        """
        Create a new reputation override for a Certificate
        :param override_list: {str} The override list to add a new reputation
        :param description: {str} Justification for override
        :param signed_by: {str} Name of the signer for the application
        :param certificate_authority: {str} Certificate authority that authorizes the validity of the certificate
        :return: {OverriddenCertificateReputation} OverriddenCertificateReputation datamodel object
        """
        response = self.session.post(
            url=self._get_full_url(
                "create_reputation_override",
                api_root=self.api_root,
                org_key=self.org_key,
            ),
            json=remove_none_values(
                {
                    "description": description,
                    "override_list": override_list,
                    "override_type": "CERT",
                    "signed_by": signed_by,
                    "certificate_authority": certificate_authority,
                }
            ),
        )
        self.validate_response(
            response,
            f"Unable to create reputation override in {override_list} for a certificate which is signed by {signed_by}"
            f"{'' if not certificate_authority else f' and issued by CA {certificate_authority}'}",
        )
        return self.parser.build_certificate_reputation_override_obj(response.json())

    def create_sha256_reputation_override(
        self, override_list, sha256_hash, filename=None, description=None
    ):
        """
        Create a new reputation override for a SHA-256 hash
        :param override_list: {str} The override list to add a new reputation
        :param description: {str} Justification for override
        :param sha256_hash: {str} A hexadecimal string of length 64 characters representing the SHA-256 hash of the application
        :param filename: {str} An application name for the hash
        :return: {OverriddenSHA256Reputation} OverriddenSHA256Reputation datamodel object
        """
        response = self.session.post(
            url=self._get_full_url(
                "create_reputation_override",
                api_root=self.api_root,
                org_key=self.org_key,
            ),
            json=remove_none_values(
                {
                    "description": description,
                    "override_list": override_list,
                    "override_type": "SHA256",
                    "sha256_hash": sha256_hash,
                    "filename": filename,
                }
            ),
        )
        self.validate_response(
            response,
            f"Unable to create reputation override in {override_list} for file hash {sha256_hash}",
        )
        return self.parser.build_sha265_reputation_override_obj(response.json())

    def list_reputation_overrides(
        self,
        override_list,
        start_row,
        max_rows,
        sort_order,
        sort_field,
        override_type=None,
    ):
        """
        Search existing reputation overrides by a search criteria.
        :param override_list: {str} The override list to add a new reputation
        :param override_type: {str} Process property match when applying override. Possible values: SHA256, CERT, IT_TOOL
        :param start_row: {int} For pagination, where to start retrieving results from
        :param max_rows: {int} For pagination, how many results to return
        :param sort_order: {str} The direction to sort by
        :param sort_field: {str} The field to sort on
        :return: {[OverriddenReputation]} List of OverriddenReputation datamodel objects
        """
        response = self.session.post(
            url=self._get_full_url(
                "search_reputation_overrides",
                api_root=self.api_root,
                org_key=self.org_key,
            ),
            json=remove_none_values(
                {
                    "criteria": (
                        None
                        if not (override_list or override_type)
                        else remove_none_values(
                            {
                                "override_list": override_list,
                                "override_type": override_type,
                            }
                        )
                    ),
                    "start": start_row,
                    "rows": max_rows,
                    "sort_field": sort_field,
                    "sort_order": sort_order,
                }
            ),
        )
        self.validate_response(
            response,
            f"Unable to list reputation overrides{f' of type {override_type}' if override_type else ''} in {override_list}",
        )
        return self.parser.build_reputation_override_obj_list(response.json())

    def delete_reputation_override(self, reputation_override_id):
        """
        Delete a reputation override by id
        :param reputation_override_id: {str} Reputation override ID
        """
        response = self.session.delete(
            url=self._get_full_url(
                "delete_reputation_override",
                api_root=self.api_root,
                org_key=self.org_key,
                rep_override_id=reputation_override_id,
            )
        )
        self.validate_response(
            response,
            f"Unable to delete reputation override with id {reputation_override_id}",
        )

    def get_vulnerability_details(self, device_id, severities=None, limit=None):
        """
        Get device vulnerability details
        :param device_id: {str} device id
        :param severities: {[str]} list of severities for filtering
        :param limit: {int} limit for results
        :return: {[VulnerabilityDetail]} list of VulnerabilityDetail objects
        """
        payload = {
            "query": "",
            "sort": [{"field": "risk_meter_score", "order": "DESC"}],
            "criteria": {
                "severity": {
                    "operator": "IN",
                    "value": (
                        [
                            SEVERITY_FILTER_MAPPING.get(severity)
                            for severity in severities
                        ]
                        if severities
                        else list(SEVERITY_FILTER_MAPPING.values())
                    ),
                }
            },
        }

        devices = self._paginate_results(
            method="POST",
            url=self._get_full_url(
                "get_vulnerability_details", org_key=self.org_key, device_id=device_id
            ),
            err_msg="Unable to get vulnerability details",
            limit=limit,
            body=payload,
        )

        return self.parser.build_results(
            devices, "build_vulnerability_detail", pure_data=True
        )
