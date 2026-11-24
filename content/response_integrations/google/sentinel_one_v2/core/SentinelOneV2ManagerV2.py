from __future__ import annotations

import json
from typing import TYPE_CHECKING
from requests import Response

from sentinel_one_v2.core.SentinelOneV2Manager import SentinelOneV2Manager
from sentinel_one_v2.core.SentinelOneV2ParserV2 import SentinelOneV2ParserV2
from sentinel_one_v2.core.datamodelsV2 import Alert
from sentinel_one_v2.core.exceptions import SentinelOneV2NotFoundError

if TYPE_CHECKING:
    from typing import Any, Dict, List

    from TIPCommon.types import SingleJson

    from sentinel_one_v2.core.datamodels import Agent, Threat, ThreatNote


API_ENDPOINTS = {
    "threat_incident": "/web/api/v{api_version}/threats/incident",
    "get_threats_notes": "/web/api/v{api_version}/threats/{threat_id}/notes",
    "add_threats_notes": "/web/api/v{api_version}/threats/notes",
    "analyst_verdict": "/web/api/v{api_version}/threats/analyst-verdict",
    "move_agents": "/web/api/v{api_version}/groups/{group_id}/move-agents",
    "fetch_file": "/web/api/v{api_version}/threats/fetch-file",
    "get_timeline": "/web/api/v{api_version}/threats/{threat_id}/timeline",
    "download_file": "/web/api/v{api_version}{download_url}",
    "get_cloud_detection_alerts": ("/web/api/v{api_version}/cloud-detection/alerts"),
    "update_cloud_detection_alert_incident_status": (
        "/web/api/v{api_version}/cloud-detection/alerts/incident"
    ),
    "update_cloud_detection_alert_verdict": (
        "/web/api/v{api_version}/cloud-detection/alerts/analyst-verdict"
    ),
    "alerts": "/web/api/v2.1/cloud-detection/alerts",
    "get_site_by_name": "/web/api/v2.1/sites",
    "get_agents_by_site": "/web/api/v2.1/agents",
    "create_device_control_rule": "/web/api/v2.1/device-control",
    "update_device_control_rule": "/web/api/v2.1/device-control/{rule_id}",
    "activities": "/web/api/v2.1/activities",
    "get_cloud_detection_alert_notes": (
        "/web/api/v2.1/cloud-detection/alerts/{alert_id}/notes"
    ),
    "add_cloud_detection_alert_note": (
        "/web/api/v2.1/cloud-detection/alerts/{alert_id}/notes"
    ),
}


class SentinelOneV2ManagerV2(SentinelOneV2Manager):
    def __init__(
        self,
        api_root,
        api_token,
        api_version,
        verify_ssl=False,
        force_check_connectivity=False,
        logger=None,
    ):
        """
        :param api_root: API root URL.
        :param api_token: SentinelOne api token
        :param verify_ssl: Enable (True) or disable (False). If enabled, verify the SSL 
            certificate for the 
        :param force_check_connectivity: True or False. If True it will check
            connectivity initially.
        :param logger: Siemplify logger.
        """
        super().__init__(
            api_root,
            api_token,
            api_version,
            verify_ssl,
            force_check_connectivity,
            logger,
        )
        self.api_endpoints.update(API_ENDPOINTS)
        self.parser = SentinelOneV2ParserV2()

    def move_agents(self, group_id, agent_ids=None):
        """
        Move agents to a given group
        :param group_id: {str} The ID of the group
        :param agent_ids: {list} List of ids of agents to move to the group
        :return: {int} Number of agents that were moved
            raise SentinelOneV2ManagerError if failed to validate response status code
        """
        payload = {"filter": {"ids": agent_ids} if agent_ids else {}}
        response = self.session.put(
            self._get_full_url("move_agents", group_id=group_id), json=payload
        )
        self.validate_response(response, "Unable to move agents")

        return self.parser.get_moved_count(response.json())

    def get_threat_notes(self, threat_id):
        """
        Get threats annotation
        :param threat_id {int}
        :return: affected count
        """
        response = self.session.get(
            self._get_full_url("get_threats_notes", threat_id=threat_id)
        )
        self.validate_response(response, "Unable get threat notes")

        return self.parser.build_results(response.json(), "build_threat_notes")

    def resolve_threat(self, threat_ids, annotation=None):
        """
        Resolves threats using the threat ID
        :param threat_ids: {list} List of threat IDs
        :param annotation: {str} Threat annotation
        :return: affected count
        """
        payload = {
            "data": {"incidentStatus": "resolved"},
            "filter": {"ids": threat_ids},
        }

        response = self.session.post(
            self._get_full_url("threat_incident"), json=payload
        )
        self.validate_response(response, "Unable to resolve threat")

        if annotation:
            self.add_notes_to_threat(threat_ids, annotation)

        return self.parser.get_affected(response.json())

    def add_notes_to_threat(self, threat_ids, note):
        """
        Add notes to threats using the threat ID
        :param threat_ids: {list} List of threat IDs
        :param note: {str} Threat note
        :return: {int} affected count
        """
        payload = {"data": {"text": note}, "filter": {"ids": threat_ids}}
        response = self.session.post(
            self._get_full_url("add_threats_notes"), json=payload
        )
        self.validate_response(response, "Unable to add note to threat")

        return self.parser.get_affected(response.json())

    def mark_as_threat(self, threat_ids):
        """
        Marks suspicious threats as a threat
        :param threat_ids: {list} List ot threat IDs
        :return: {int} count of affected threats
        """
        payload = {
            "data": {"analystVerdict": "true_positive"},
            "filter": {"ids": threat_ids},
        }
        response = self.session.post(
            self._get_full_url("analyst_verdict"), json=payload
        )
        self.validate_response(response, "Unable to mark as threat")

        return self.parser.get_affected(response.json())

    def create_fetch_job(self, threat_id, password):
        """
        Create a fetch job
        :param threat_id: {str} The threat id
        :param password: {str} The password for the zip that contains the threat file
        :return: {int} The job affected value
        """
        url = self._get_full_url("fetch_file")
        payload = json.dumps(
            {"data": {"password": password}, "filter": {"ids": [threat_id]}}
        )

        response = self.session.post(url, data=payload)
        self.validate_response(response)

        return self.parser.get_affected(response.json())

    def get_file_from_timeline(self, threat_id):
        """
        Get threat file from timeline
        :param threat_id: {str} The threat id
        :return: {tuple} File name, file content
        """
        url = self._get_full_url("get_timeline", threat_id=threat_id)
        params = {"skip": 0, "limit": 100, "sortOrder": "desc"}

        response = self.session.get(url, params=params)
        self.validate_response(response)
        name, url = self.parser.get_file_data_from_timeline(response.json())

        if name and url:
            return name, self.get_file_by_download_url(url)
        else:
            return None, None

    def get_file_by_download_url(self, download_url):
        """
        Get file by url
        :param download_url: The file download url
        :return: {dict} The raw data of file
        """
        url = self._get_full_url("download_file", download_url=download_url)
        response = self.session.get(url)
        self.validate_response(response)
        return response.content

    def update_analyst_verdict(self, threat_id, analyst_verdict):
        """
        Update analyst ver dict
        :param threat_id: {str} Threat ID
        :param analyst_verdict: analyst Verdict mapped value
        :return: {bool} True if analyst verdict updated False otherwise
        """
        payload = {
            "data": {"analystVerdict": analyst_verdict},
            "filter": {"ids": [threat_id]},
        }

        response = self.session.post(
            self._get_full_url("analyst_verdict"), json=payload
        )
        self.validate_response(response)
        updated_threat = self.get_threats(threat_ids=[threat_id])[0]

        return updated_threat.analyst_verdict == analyst_verdict

    def update_incident_status(self, incident_ids, status):
        """
        Update incident status.
        :param incident_ids: {list} List of ids
        :param status: {str} possible values (value of INCIDENT_STATUS_MAPPING)
        :return: {int} count affected count
        """
        payload = {
            "data": {"incidentStatus": status},
            "filter": {"ids": incident_ids},
        }
        response = self.session.post(
            self._get_full_url("threat_incident"), json=payload
        )
        self.validate_response(response, "Unable to update incident status")
        updated_threat = self.get_threats(threat_ids=incident_ids)[0]

        return updated_threat.incident_status == status

    def get_threat_notes_for_sync(self, threat_id: str) -> list[ThreatNote]:
        """
        Get ALL threat notes by handling pagination automatically.
        """
        all_notes = []
        limit = 100
        cursor = None

        while True:

            params = {"limit": limit}
            if cursor:
                params["cursor"] = cursor


            url = self._get_full_url("get_threats_notes", threat_id=threat_id)
            response = self.session.get(url, params=params)
            self.validate_response(response, "Unable to get threat notes")

            json_response = response.json()
            notes = self.parser.build_results(json_response, "build_threat_notes")
            all_notes.extend(notes)


            pagination = json_response.get("pagination", {})
            cursor = pagination.get("nextCursor")

            if not cursor:
                break

        return all_notes

    def get_threats_by_ids_inclusive(
        self, threat_ids: list[str], **kwargs
    ) -> list[Threat]:
        """
        Fetches threats by IDs, explicitly requesting BOTH Resolved and Unresolved 
        statuses.
        """
        if not threat_ids:
            return []

        url = self._get_full_url("threats")
        params = {
            "ids": ",".join(threat_ids),
            "limit": len(threat_ids)
        }

        if kwargs:
            params.update(kwargs)

        response = self.session.get(url, params=params)
        self.validate_response(response, "Unable to get threats by IDs")

        return self.parser.build_results(
            response.json(),
            method="build_threat_obj",
            pure_data=False
        )

    def update_analyst_verdict_for_sync(
        self, threat_id: str, analyst_verdict: str
    ) -> bool:
        """
        Update analyst verdict for sync purposes.
        :param threat_id: {str} Threat ID.
        :param analyst_verdict: {str} Analyst Verdict mapped value.
        :return: {bool} True if analyst verdict updated, False otherwise.
        """
        payload = {
            "data": {"analystVerdict": analyst_verdict},
            "filter": {"ids": [threat_id]},
        }

        response = self.session.post(
            self._get_full_url("analyst_verdict"), json=payload
        )
        self.validate_response(response, "Unable to update analyst verdict")
        return True

    def update_analyst_verdict_bulk(
        self, threat_ids: list[str], analyst_verdict: str
    ) -> bool:
        """
        Bulk update analyst verdict for multiple threats simultaneously.
        :param threat_ids: {list[str]} List of Threat IDs.
        :param analyst_verdict: {str} Analyst Verdict mapped value.
        :return: {bool} True if successful.
        """
        payload = {
            "data": {"analystVerdict": analyst_verdict},
            "filter": {"ids": threat_ids},
        }

        response = self.session.post(
            self._get_full_url("analyst_verdict"), json=payload
        )
        self.validate_response(response, "Unable to bulk update analyst verdict")
        return True

    def update_incident_status_for_sync(self, threat_id: str, status: str) -> bool:
        """
        Update incident status for sync purposes.
        :param threat_id: {str} Threat ID.
        :param status: {str} Possible values (e.g., "resolved", "active").
        :return: {bool} True if incident status updated, False otherwise.
        """
        payload = {
            "data": {"incidentStatus": status},
            "filter": {"ids": [threat_id]},
        }
        response = self.session.post(
            self._get_full_url("threat_incident"), json=payload
        )
        self.validate_response(response, "Unable to update incident status")
        return True

    def get_cloud_detection_alerts(self, alert_ids: list[str]) -> list[Alert]:
        """
        Get cloud detection alerts.

        Args:
            alert_ids (list[str]): A list of alert IDs to fetch.

        Returns:
            list[Alert]: A list of found Alert objects.
        """
        params: Dict = {"ids": ",".join(alert_ids)}

        response: Response = self.session.get(
            self._get_full_url("get_cloud_detection_alerts"), params=params
        )
        self.validate_response(response, "Unable to get cloud detection alerts")

        return self.parser.build_results(response.json(), "build_alert_obj")

    def get_cloud_detection_alert_or_raise(self, alert_id: str) -> Alert:
        """
        Get cloud detection alert by ID or raise an exception if not found.

        Args:
            alert_id (str): The ID of the alert to fetch.

        Returns:
            Alert: The found Alert object.

        Raises:
            SentinelOneV2NotFoundError: If no alert with the given ID is found.
        """
        alerts: List[Alert] = self.get_cloud_detection_alerts([alert_id])
        if alerts:
            return alerts[0]

        raise SentinelOneV2NotFoundError(
            f"alert with ID {alert_id} wasn’t found in SentinelOne. "
            f"Please check the spelling."
        )

    def update_cloud_detection_alert_verdict(
        self, alert_ids: list[str], analyst_verdict: str
    ) -> None:
        """
        Update cloud detection alert analyst verdict.

        Args:
            alert_ids (list[str]): A list of Alert IDs.
            analyst_verdict (str): The mapped analyst verdict value.
        """
        payload: Dict = {
            "data": {"analystVerdict": analyst_verdict},
            "filter": {"ids": alert_ids},
        }

        response: Response = self.session.post(
            self._get_full_url("update_cloud_detection_alert_verdict"),
            json=payload,
        )
        self.validate_response(response)

    def update_cloud_detection_alert_incident_status(
        self, alert_ids: list[str], status: str
    ) -> None:
        """
        Update cloud detection alert incident status.

        Args:
            alert_ids (list[str]): A list of Alert IDs.
            status (str): The new status for the alert.
        """
        payload: Dict = {
            "data": {"incidentStatus": status},
            "filter": {"ids": alert_ids},
        }

        response: Response = self.session.post(
            self._get_full_url("update_cloud_detection_alert_incident_status"),
            json=payload,
        )
        self.validate_response(response)

    def get_alerts(
        self,
        start_time: str,
        severities: list[str],
        statuses: list[str],
        limit: int,
        cursor: str = None
    ) -> tuple[list, str]:
        """
        Fetches alerts from the SentinelOne API based on specified filters,
        supporting pagination.

        Args:
            start_time (str): The start time to fetch alerts from.
            severities (list): A list of severity levels to filter by.
            statuses (list): A list of statuses to filter by.
            limit (int): The maximum number of alerts to fetch.
            cursor (str, optional): The cursor for pagination. Defaults to None.

        Returns:
            tuple: A tuple containing a list of alert objects
            and the next cursor string.
        """
        params = {
            "createdAt__gte": start_time,
            "sortBy": "alertInfoCreatedAt",
            "sortOrder": "asc",
            "limit": limit,
        }
        if cursor:
            params["cursor"] = cursor
        if severities:
            params["severity"] = ",".join(severities)
        if statuses:
            params["incidentStatus"] = ",".join(statuses)

        response = self.session.get(self._get_full_url("alerts"), params=params)
        self.validate_response(response)

        response_data = response.json()
        alerts = self.parser.build_results(
            response_data, method="build_alert_obj", pure_data=False
        )
        next_cursor = response_data.get("pagination", {}).get("nextCursor")

        return alerts, next_cursor

    def get_site_by_name(self, site_name: str) -> SingleJson:
        """
        Get Site by name in SentinelOneV2.

        Args:
            site_name str: Site name to be fetched.

        Returns:
            SingleJson: JSON object of the sites.
        """

        params: SingleJson = {"name": site_name}

        response = self.session.get(
            self._get_full_url("get_site_by_name"),
            params=params,
        )
        self.validate_response(response)

        return response.json()

    def get_agents_by_site(
        self,
        site_ids: str,
        limit: int,
    ) -> list[Agent]:
        """
        Get Agents by Site rule in SentinelOneV2.

        Args:
            site_ids str : Comma-separated site ids.
            limit int: Limit the no of records to fetch.

        Returns:
            list: A list of agent objects.
        """

        params: SingleJson = {"siteIds": site_ids}
        self.logger.info(f"Params: {params}")

        return self._paginate_results_v2(
            api_endpoint="get_agents_by_site",
            params=params,
            parser_method="build_agent_obj",
            limit=limit,
        )

    def _paginate_results_v2(
        self,
        api_endpoint: str,
        parser_method: str,
        params: SingleJson | None = None,
        limit: int | None = None,
        api_page_size: int = 25,
    ) -> List[Any]:
        """Paginate the results of a job V2.

        Args:
            api_endpoint (str): The API endpoint to call.
            parser_method (str): The parser method to use for building
                results.
            params (SingleJson, optional): The params of the request. Defaults
                to None.
            limit (int, optional): The limit of the results to fetch. Defaults to None.
            api_page_size (int, optional): The number of items to fetch per API call. 
                Defaults to 1000.

        Returns:
            List[Any]: A list of results.
        """
        all_results: List[Any] = []
        current_cursor: str | None = None

        params = params or {}

        while len(all_results) < limit:
            current_limit: int = min(limit - len(all_results), api_page_size)
            current_params: SingleJson = params.copy()
            current_params["limit"] = current_limit
            if current_cursor:
                current_params["cursor"] = current_cursor

            response: Response = self.session.get(
                self._get_full_url(api_endpoint), params=current_params
            )
            self.validate_response(response)
            response_data: SingleJson = response.json()
            results_page: list[Any] = self.parser.build_results(
                response_data,
                method=parser_method,
                pure_data=False,
            )

            if results_page:
                all_results.extend(results_page)

            next_cursor: str | None = response_data.get("pagination", {}).get(
                "nextCursor"
            )
            if not next_cursor:
                break

            current_cursor = next_cursor

        return all_results

    def create_device_control_rule(
        self,
        rule_json: SingleJson,
        scope_json: SingleJson,
    ) -> SingleJson:
        """Create a device control rule in SentinelOne.

        Args:
            rule_json (SingleJson): JSON object of the device control rule.
            scope_json (SingleJson): JSON object defining the scope of the rule.

        Returns:
            SingleJson: JSON object of the created device control rule.
        """
        payload: SingleJson = {"data": rule_json, "filter": scope_json}
        response: Response = self.session.post(
            self._get_full_url("create_device_control_rule"),
            json=payload,
        )
        self.validate_response(response)

        return response.json()

    def update_device_control_rule(
        self,
        rule_id: str,
        rule_json: SingleJson,
    ) -> SingleJson:
        """Update a device control rule in SentinelOne.

        Args:
            rule_id (str): The ID of the device control rule to update.
            rule_json (SingleJson): JSON object of the device control rule.

        Returns:
            SingleJson: JSON object of the created device control rule.
        """
        payload: SingleJson = {"data": rule_json}
        response: Response = self.session.put(
            self._get_full_url("update_device_control_rule", rule_id=rule_id),
            json=payload,
        )
        self.validate_response(response)

        return response.json()

    def get_device_control_rule_name(
        self,
        rule_id: str,
        scope_type: str,
        scope_id: str,
    ) -> SingleJson:
        """Get a device control rule in SentinelOne.

        Args:
            rule_id (str): The ID of the device control rule to get.
            scope_type (str): The type of the scope of the rule.
            scope_id (str): The ID of the scope of the rule.

        Returns:
            SingleJson: JSON object of the device control rule.
        """
        params: SingleJson = {scope_type: scope_id, "ids": rule_id}
        response: Response = self.session.get(
            self._get_full_url("create_device_control_rule"), params=params
        )
        self.validate_response(response)

        return response.json().get("data", [])

    def delete_device_control_rule(
        self,
        rule_id: str,
        rule_name: str,
    ) -> None:
        """Delete a device control rule in SentinelOne.

        Args:
            rule_id (str): The ID of the device control rule to delete.
            rule_name (str): The name of the device control rule to delete.
        """
        payload: SingleJson = {
            "data": {},
            "filter": {"ids": rule_id, "ruleName": rule_name},
        }
        response: Response = self.session.delete(
            self._get_full_url("create_device_control_rule"),
            json=payload,
        )
        self.validate_response(response)

        return response.json()

    def get_activities(
        self,
        limit: int = 1000,
        **kwargs: Any,
    ) -> list[SingleJson]:
        """Get tenant activities from SentinelOne.

        Args:
            limit (int): The limit of the results to fetch.
            **kwargs: Additional query parameters (e.g. createdAt__gte, threatIds).

        Returns:
            list[SingleJson]: List of raw activity JSON objects.
        """
        params: SingleJson = kwargs.copy()

        # Remove limit from params to avoid API validation errors.
        # _paginate_results dynamically handles chunking and limits.
        if "limit" in params:
            del params["limit"]

        response: list[SingleJson] = self._paginate_results(
            method="GET",
            url=self._get_full_url("activities"),
            params=params,
            limit=int(limit),
            err_msg="Unable to get activities",
        )
        return response

    def get_cloud_detection_alert_notes(self, alert_id: str) -> list[str]:
        """
        Get cloud detection alert notes.
        Args:
            alert_id (str): The ID of the alert to fetch notes for.
        Returns:
            list[str]: A list of notes.
        """
        response: Response = self.session.get(
            self._get_full_url(
                "get_cloud_detection_alert_notes",
                alert_id=alert_id,
            )
        )
        self.validate_response(
            response,
            "Unable to get cloud detection alert notes",
        )
        return self.parser.build_results(
            response.json(),
            "build_alert_note_obj",
        )

    def add_cloud_detection_alert_note(
        self,
        alert_id: str,
        note: str,
    ) -> None:
        """
        Add a note to a cloud detection alert.
        Args:
            alert_id (str): The ID of the alert to add a note to.
            note (str): The note to add.
        """
        payload = {"data": {"text": note}}
        response: Response = self.session.post(
            self._get_full_url(
                "add_cloud_detection_alert_note",
                alert_id=alert_id,
            ),
            json=payload,
        )
        self.validate_response(
            response,
            "Unable to add cloud detection alert note",
        )

    def set_alert_verdict(self, alert_id: str, verdict: str) -> SingleJson:
        """
        Set alert verdict.

        Args:
            alert_id (str): The ID of the alert.
            verdict (str): The verdict to set.

        Returns:
            SingleJson: The response from the API.
        """
        payload = {"verdict": verdict}
        url = f"{self.api_root}/web/api/v2.1/cloud-detection/alerts/{alert_id}/verdict"
        response = self.session.put(url, json=payload)
        self.validate_response(response, "Unable to set alert verdict")
        return response.json()

    def set_alert_status(
        self,
        alert_id: str,
        status: str,
        incident_id: str,
    ) -> SingleJson:
        """
        Set alert status.

        Args:
            alert_id (str): The ID of the alert.
            status (str): The status to set.
            incident_id (str): The incident ID.

        Returns:
            SingleJson: The response from the API.
        """
        payload = {"incidentId": incident_id, "status": status}
        url = f"{self.api_root}/web/api/v2.1/cloud-detection/alerts/{alert_id}/incident"
        response = self.session.put(url, json=payload)
        self.validate_response(response, "Unable to set alert status")
        return response.json()

    def get_modified_alerts_by_ids(
        self,
        status: str,
        limit: int,
        alert_ids: list[str],
    ) -> list[Alert]:
        """
        Fetches ALL modified alerts from the SentinelOne API based on alert IDs,
        handling pagination.

        Args:
            status (str): The status of the alerts to fetch.
            limit (int): Max number of alerts to return per API call.
            alert_ids (list[str]): A list of SentinelOne alert IDs.

        Returns:
            list[Alert]: A flattened list of ALL modified alert objects.
        """
        if not alert_ids:
            return []

        all_alerts = []
        ids_string = ",".join(alert_ids)
        next_cursor = None
        has_next = True

        while has_next:
            params = {
                "ids": ids_string,
                "limit": limit,
                "incidentStatus": status,
                "sortOrder": "desc"
            }
            if next_cursor:
                params["cursor"] = next_cursor

            response = self.session.get(self._get_full_url("alerts"), params=params)
            self.validate_response(response)

            response_data = response.json()

            current_alerts = self.parser.build_results(
                response_data, method="build_alert_obj", pure_data=False
            )

            all_alerts.extend(current_alerts)

            next_cursor = response_data.get("pagination", {}).get("nextCursor")
            has_next = bool(next_cursor)

        return all_alerts
