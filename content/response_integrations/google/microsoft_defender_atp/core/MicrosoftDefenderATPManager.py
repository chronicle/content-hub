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

import ast
from datetime import datetime, timedelta
import requests

# FIXME: Import urllib while using python 3
import urllib.parse


from soar_sdk.SiemplifyLogger import SiemplifyLogger
from TIPCommon.filters import filter_old_alerts
from TIPCommon.types import SingleJson

from .constants import (
    API_LIMIT_STATUS_CODE,
    CUSTOM_ACCESS_TOKEN_URL,
    DEFAULT_ALERTS_LIMIT,
    GRAPH_CLASSIFICATIONS_MAPPING,
    GRAPH_DETERMINATIONS_MAPPING,
    GRAPH_SEVERITY_MAPPING,
    GRAPH_STATUS_MAPPING,
    GRAPH_VALID_PAIRS,
    POSSIBLE_SORT_ORDER,
    POSSIBLE_THREATS,
    POSSIBLE_SORT_BY,
    SORT_KEY_MAPPING,
    THREAT_ATTRIBUTE_MAPPING,
    THREAT_QUERY_MAPPING,
)
from .datamodels import Alert, Recommendation, Vulnerability
from .MicrosoftDefenderATPTransformationLayer import (
    MicrosoftDefenderATPTransformationLayer,
)


class MicrosoftDefenderATPError(Exception):
    """
    General Exception for MicrosoftDefenderATP Manager
    """

    pass


class MicrosoftDefenderATPValidationError(Exception):
    """
    General Exception for MicrosoftDefenderATP Validation
    """

    pass


class MicrosoftDefenderATPForbiddenError(Exception):
    pass


class MicrosoftDefenderATPManager:
    """
    MicrosoftDefenderATP Manager
    """

    TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
    DEFENDER_API_ACCESS_TOKEN_URL = (
        "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    )
    SIEM_DETECTIONS_URL = "https://wdatp-alertexporter-us.securitycenter.windows.com"

    TOKEN_PAYLOAD = {
        "client_id": None,
        "client_secret": None,
        "resource": None,
        "grant_type": "client_credentials",
    }

    DEFENDER_API_TOKEN_PAYLOAD = {
        "client_id": None,
        "client_secret": None,
        "scope": "https://api.security.microsoft.com/.default",
        "grant_type": "client_credentials",
    }

    URLS = {
        "test_connectivity": "/api/alerts",
        "v2_graph": "/v1.0/security/alerts_v2",
        "get_alerts": "/api/alerts",
        "update_alert": "/api/alerts/{alert_id}",
        "update_alert_graph": "/v1.0/security/alerts_v2/{alert_id}",
        "get_machines": "/api/machines",
        "get_machine_logon_users": "/api/machines/{machine_id}/logonusers",
        "get_machine_related_alerts": "/api/machines/{machine_id}/alerts",
        "isolate_machine": "/api/machines/{machine_id}/isolate",
        "unisolate_machine": "/api/machines/{machine_id}/unisolate",
        "run_antivirus_scan": "/api/machines/{machine_id}/runAntiVirusScan",
        "stop_and_quarantine_machine_file": "/api/machines/{machine_id}/StopAndQuarantineFile",
        "get_machine_task_status": "/api/machineactions",
        "wait_machine_task_status": "/api/machineactions",
        "get_file_related_alerts": "/api/files/{file_hash}/alerts",
        "get_file_related_machines": "/api/files/{file_hash}/machines",
        "run_advanced_hunting_query": "/api/advancedqueries/run",
        "run_advanced_hunting_graph": "/v1.0/security/runHuntingQuery",
        "get_file_info": "/api/files/{file_hash}",
        "get_file_stats": "/api/files/{file_hash}/stats",
        "get_detections_siem": "/api/alerts",
        "get_incident": "/api/incidents/{}",
        "entities": "/api/indicators",
        "delete_indicator": "/api/indicators/{indicator_id}",
        "run_live_response": "/api/machines/{machine_id}/runliveresponse",
        "get_live_response_status": "/api/machineactions/{action_id}",
        "get_live_response_result_download_link": (
            "/api/machineactions/{action_id}/GetLiveResponseResultDownloadLink(index=0)"
        ),
        "get_machine_vulnerabilities": "/api/machines/{machine_id}/vulnerabilities",
        "get_machine_recommendations": "/api/machines/{machine_id}/recommendations",
        "get_user_related_alerts": "/api/users/{user_id}/alerts",
    }

    DEFAULT_TIME_FRAME = 3

    DEFAULT_STATUSES = ["Unknown", "New", "InProgress", "Resolved"]

    DEFAULT_SEVERITIES = [
        "UnSpecified",
        "Informational",
        "Low",
        "Medium",
        "High",
        "Critical",
    ]

    DEFAULT_CATEGORIES = [
        "Collection",
        "CommandAndControl",
        "CredentialAccess",
        "DefenseEvasion",
        "Discovery",
        "Execution",
        "Exfiltration",
        "Exploit",
        "InitialAccess",
        "LateralMovement",
        "Malware",
        "Persistence",
        "PrivilegeEscalation",
        "Ransomware",
        "SuspiciousActivity",
        "UnwantedSoftware",
    ]

    DEFAULT_CLASSIFICATIONS = ["Unknown", "FalsePositive", "TruePositive"]

    DEFAULT_DETERMINATIONS = [
        "NotAvailable",
        "MultiStagedAttack",
        "MaliciousUserActivity",
        "Malware",
        "CompromisedAccount",
        "Phishing",
        "UnwantedSoftware",
        "SecurityTesting",
        "LineOfBusinessApplication",
        "ConfirmedActivity",
        "NotMalicious",
        "Other",
    ]

    DEFAULT_HEALTH_STATUSES = [
        "Active",
        "Inactive",
        "ImpairedCommunication",
        "NoSensorData",
        "NoSensorDataImpairedCommunication",
    ]

    DEFAULT_RISK_SCORES = ["None", "Low", "Medium", "High"]

    TASK_SUCCEEDED_STATUS = "Succeeded"
    TASK_PENDING_STATUS = "Pending"
    TASK_FAILED_STATUS = "Failed"
    TASK_TIMEOUT_STATUS = "TimeOut"
    TASK_CANCELLED_STATUS = "Cancelled"

    POSSIBLE_SCAN_TYPES = ["Full", "Quick"]

    POSSIBLE_ISOLATION_TYPES = ["Full", "Selective"]

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        resource: str,
        login_api_root: str = None,
        defender_api_resource: str = None,
        verify_ssl: bool = True,
        siemplify: SiemplifyLogger | None = None,
        entities_scope: bool = False,
    ) -> None:
        """
        Init function for MS Defender ATP Manager

        Args:
            client_id(str): Client ID for authentication
            client_secret(str): Client secret for authentication
            tenant_id(str): Tenant ID for authentication
            resource(str): Resource name for authentication
            login_api_root(str, optional): Login API root URL for authentication
            defender_api_resource(str, optional): API resource name for authentication
            verify_ssl(bool, optional): Verify SSL certificate for authentication
            siemplify(SiemplifyLogger, optional): Siemplify logger for authentication
            entities_scope(bool, optional): Enable entities scope for authentication

        Returns:
            None
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.resource = resource
        self.login_api_root = login_api_root
        self.defender_api_resource = defender_api_resource
        self.verify_ssl = verify_ssl
        self.siemplify = siemplify
        self.session = requests.Session()
        self.session.verify = verify_ssl
        if self.defender_api_resource:
            self.access_token = self._generate_defender_api_token(
                entities_scope=entities_scope
            )
        else:
            self.access_token = self._generate_token(
                client_id=self.client_id,
                client_secret=self.client_secret,
                tenant_id=self.tenant_id,
                resource=self.resource,
                login_api_root=self.login_api_root,
            )

        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
        )

    def _generate_token(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        resource: str,
        login_api_root: str = None,
    ) -> str:
        """
        Request access token (Valid for 60 min)

        Args:
            client_id(str): The Application ID that the registration portal
            client_secret(str): The application secret that you created in the app
                                registration portal for your app.
            tenant_id(str): Azure Active Directory Tenant ID
            resource(str): Api root url to use with integration.
            login_api_root(str, optional): Url to login API resource.

        Returns:
            Access token(str): Access token.
        """
        self.TOKEN_PAYLOAD["client_id"] = client_id
        self.TOKEN_PAYLOAD["client_secret"] = client_secret
        self.TOKEN_PAYLOAD["resource"] = resource
        auth_url = CUSTOM_ACCESS_TOKEN_URL.format(
            login_api_root=login_api_root,
            tenant_id=tenant_id,
        )
        response = requests.post(
            auth_url,
            data=self.TOKEN_PAYLOAD,
            verify=self.verify_ssl,
        )
        self._validate_response(
            response, "Unable to generate access token for Microsoft Defender ATP"
        )

        return response.json().get("access_token")

    def _generate_defender_api_token(
        self,
        entities_scope: bool = False,
        use_graph: bool = False
    ) -> str:
        """Request Defender API access token.

        Args:
            entities_scope(bool): Enable entities scope for authentication
            use_graph(bool): Enable graph API for authentication

        Returns:
            str: Access token
        """
        payload = self.DEFENDER_API_TOKEN_PAYLOAD.copy()
        payload["client_id"] = self.client_id
        payload["client_secret"] = self.client_secret

        if use_graph:
            payload["scope"] = "https://graph.microsoft.com/.default"
        elif entities_scope:
            payload["scope"] = "https://api.securitycenter.microsoft.com/.default"

        request_url = self.DEFENDER_API_ACCESS_TOKEN_URL.format(
            tenant_id=self.tenant_id
        )
        response = requests.post(request_url, data=payload, verify=self.verify_ssl)
        self._validate_response(
            response, "Unable to generate access token for Microsoft 365 Defender"
        )
        return response.json().get("access_token")

    def get_full_url(self, url_id: str, **kwargs) -> str:
        """
        Get a full URL from a URL ID and format it with parameters.
        Args:
            url_id: The ID of the URL to retrieve from the URLS dictionary.
            **kwargs: Keyword arguments to format the URL path.

        Returns:
            The full, formatted URL.
        """
        return urllib.parse.urljoin(self.resource, self.URLS[url_id].format(**kwargs))

    def test_connectivity(self):
        # type: () -> None or Exception
        """
        Function that checks the connection to the Microsoft Defender ATP
        """
        url = urllib.parse.urljoin(self.resource, self.URLS["test_connectivity"])
        params = self._build_api_params(limit=1)

        response = self.session.get(url, params=params)
        self._validate_response(response, "Unable to connect to Microsoft Defender ATP")

    def get_alerts(
        self,
        alert_time_frame=None,
        start_timestamp=None,
        statuses=None,
        severities=None,
        categories=None,
        incident_id=None,
        limit=None,
    ):
        # type: (int, list, list, list, int, int) -> [Alert] or Exception
        """
        Get Alerts with filtration
        @param alert_time_frame: Time frame in hours for which to fetch alerts
        @param start_timestamp: Start timestamp from when to fetch alerts
        @param statuses: Statuses of alerts to look for
        @param severities: Severities of alerts to look for
        @param categories: Categories of alerts to look for
        @param incident_id: Microsoft Defender Incident ID for which you want to find related alerts
        @param limit: How much alerts should be fetched
        @return: Alerts list
        """
        url = urllib.parse.urljoin(self.resource, self.URLS["get_alerts"])
        params = self._build_api_params(
            alert_time_frame=alert_time_frame,
            start_timestamp=start_timestamp,
            statuses=statuses,
            severities=severities,
            categories=categories,
            incident_id=incident_id,
            limit=limit,
        )

        response = self.session.get(url, params=params)
        self._validate_response(response, "Failed to fetch alerts")

        alerts_data = response.json().get("value", [])

        return [
            MicrosoftDefenderATPTransformationLayer.build_alert(alert_data)
            for alert_data in alerts_data
        ]

    def get_filtered_alerts(
        self, existing_ids, start_timestamp, statuses=None, severities=None, limit=None
    ):
        """
        Get filtered alerts
        @param existing_ids: {list} The list of existing ids
        @param start_timestamp: {int} Start timestamp from when to fetch alerts
        @param statuses: {list} Statuses of alerts to look for
        @param severities: {list} Severities of alerts to look for
        @param limit: {int} Limit for results
        :return: {list} List of filtered Alert objects
        """
        alerts = self.get_alerts(
            start_timestamp=start_timestamp,
            statuses=statuses,
            severities=severities,
            limit=max(limit, DEFAULT_ALERTS_LIMIT),
        )

        filtered_alerts = filter_old_alerts(self.siemplify, alerts, existing_ids, "id")
        return sorted(filtered_alerts, key=lambda alert: alert.alert_creation_time)

    def update_alert(
        self,
        alert_id,
        status=None,
        assigned_to=None,
        classification=None,
        determination=None,
    ):
        # type: (unicode, unicode, unicode, unicode, unicode) -> Alert or Exception
        """
        Update alert
        @param alert_id: Alert ID to update
        @param status: Status to update
        @param assigned_to: Assigned To to update
        @param classification: Classification to update
        @param determination: Determination to update
        @return: Updated Alert
        """
        url = urllib.parse.urljoin(
            self.resource, self.URLS["update_alert"].format(alert_id=alert_id)
        )
        params = self._build_api_params()

        data = {
            "status": status,
            "assignedTo": assigned_to,
            "classification": classification,
            "determination": determination,
        }

        response = self.session.patch(url, params=params, json=data)
        self._validate_response(response, f"Failed to update alert with id {alert_id}")

        alert_data = response.json()

        return MicrosoftDefenderATPTransformationLayer.build_alert(alert_data)

    def match_machine_dns_name(self, machine, starts_with_name):
        """
        Filter machines by dns name
        allow combinations domain, domain.*
        @param machine: {Machine} instance
        @param starts_with_name: {str} machine dns name
        @return: {bool} is match
        """
        dns_name = machine.computer_dns_name.lower()
        starts_with = dns_name.startswith(starts_with_name.lower())

        if starts_with and len(dns_name) == len(starts_with_name):
            return True

        return starts_with and dns_name[len(starts_with_name)] == "."

    def get_machines_by_name(self, starts_with_name):
        machines = self.get_machines(starts_with_name=starts_with_name)

        filtered_machines = [
            machine
            for machine in machines
            if self.match_machine_dns_name(machine, starts_with_name)
        ]

        return (
            sorted(filtered_machines, key=lambda machine: machine.last_seen_unix)
            if filtered_machines
            else None
        )

    def get_machines(
        self,
        last_seen_time_frame=None,
        name=None,
        starts_with_name=None,
        ip=None,
        risk_scores=None,
        health_statuses=None,
        os_platform=None,
        rbac_group_id=None,
    ):
        # type: (int, unicode, unicode, list, list, unicode, int) -> [Machine] or Exception
        """
        Get Machines list
        @param last_seen_time_frame: Last seen time frame to look for in hours
        @param name: A part of the name to look for
        @param starts_with_name: The starts with name to look for
        @param ip: Machine IP address to look for.
        @param risk_scores: Risk scores to look for
        @param health_statuses: Health status to look for
        @param os_platform: OS platform to look for
        @param rbac_group_id: RBAC Group ID to look for
        @return: Machines List
        """
        url = urllib.parse.urljoin(self.resource, self.URLS["get_machines"])
        params = self._build_api_params(
            last_seen_time_frame=last_seen_time_frame,
            computer_dns_name=name,
            starts_with_computer_dns_name=starts_with_name,
            ip=ip,
            risk_scores=risk_scores,
            health_statuses=health_statuses,
            os_platform=os_platform,
            rbac_group_id=rbac_group_id,
        )

        response = self.session.get(url, params=params)
        self._validate_response(response, "Failed to fetch machines")

        machines_data = response.json().get("value", [])

        return [
            MicrosoftDefenderATPTransformationLayer.build_machine(machine_data)
            for machine_data in machines_data
        ]

    def get_machine_logon_users(self, machine_id):
        # type: (unicode) -> [User] or Exception
        """
        Get Logon Users related to machine with given ID
        @param machine_id: Machine ID
        @return: Users list
        """
        url = urllib.parse.urljoin(
            self.resource,
            self.URLS["get_machine_logon_users"].format(machine_id=machine_id),
        )
        params = self._build_api_params()

        response = self.session.get(url, params=params)
        self._validate_response(
            response,
            f"Failed to fetch log on users of the machine with id: {machine_id}",
        )

        logon_users_data = response.json().get("value", [])

        return [
            MicrosoftDefenderATPTransformationLayer.build_user(user_data)
            for user_data in logon_users_data
        ]

    def get_machine_related_alerts(
        self,
        machine_id,
        statuses=None,
        severities=None,
        categories=None,
        incident_id=None,
    ):
        # type: (unicode, list, list, list, int) -> [Alert] or Exception
        """
        Get Alerts related to machine with given ID
        @param machine_id: Machine ID
        @param statuses: Statuses of alerts to look for
        @param severities: Severities of the incidents to look for
        @param categories: Categories of the incidents to look for
        @param incident_id: Microsoft Defender Incident ID for which you want to find related alerts
        @return: Related Alerts list
        """
        url = urllib.parse.urljoin(
            self.resource,
            self.URLS["get_machine_related_alerts"].format(machine_id=machine_id),
        )
        params = self._build_api_params(
            statuses=statuses,
            severities=severities,
            categories=categories,
            incident_id=incident_id,
        )

        response = self.session.get(url, params=params)
        self._validate_response(
            response,
            f"Failed to fetch related alerts of the machine with id: {machine_id}",
        )

        machine_alerts_data = response.json().get("value", [])

        return [
            MicrosoftDefenderATPTransformationLayer.build_alert(alert_data)
            for alert_data in machine_alerts_data
        ]

    def isolate_machine(self, machine_id, isolation_type, comment):
        # type: (unicode, unicode, unicode) -> MachineTask or Exception
        """
        Create Isolate Machine Task
        @param machine_id: Machine ID
        @param isolation_type: Isolation type
        @param comment: Comment as to why the machine needs to be isolated
        @return: Machine Task
        """
        url = urllib.parse.urljoin(
            self.resource, self.URLS["isolate_machine"].format(machine_id=machine_id)
        )
        params = self._build_api_params()

        data = {"Comment": comment, "IsolationType": isolation_type}

        response = self.session.post(url, params=params, json=data)
        self._validate_response(
            response, f"Failed isolate machine with ID: {machine_id}"
        )

        machine_task_data = response.json()

        return MicrosoftDefenderATPTransformationLayer.build_machine_task(
            machine_task_data
        )

    def unisolate_machine(self, machine_id, comment):
        # type: (unicode, unicode) -> MachineTask or Exception
        """
        Create Unisolate Machine Task
        @param machine_id: Machine ID
        @param comment: Comment as to why the machine needs to be unisolated
        @return: Machine Task
        """
        url = urllib.parse.urljoin(
            self.resource, self.URLS["unisolate_machine"].format(machine_id=machine_id)
        )
        params = self._build_api_params()

        data = {"Comment": comment}

        response = self.session.post(url, params=params, json=data)
        self._validate_response(
            response, f"Failed unisolate machine with ID: {machine_id}"
        )

        machine_task_data = response.json()

        return MicrosoftDefenderATPTransformationLayer.build_machine_task(
            machine_task_data
        )

    def run_antivirus_scan(self, machine_id, av_scan_type, comment):
        # type: (unicode, unicode, unicode) -> MachineTask or Exception
        """
        Create Run AV Scan Machine Task
        @param machine_id: Machine ID
        @param av_scan_type: To start Full or Quick antivirus scan on machine
        @param comment: Comment as to why an antivirus scan needs to be executed on the machine
        @return: Machine Task
        """
        url = urllib.parse.urljoin(
            self.resource, self.URLS["run_antivirus_scan"].format(machine_id=machine_id)
        )
        params = self._build_api_params()

        data = {"Comment": comment, "ScanType": av_scan_type}

        response = self.session.post(url, params=params, json=data)
        self._validate_response(
            response, f"Failed run AV on machine with ID: {machine_id}"
        )

        machine_task_data = response.json()

        return MicrosoftDefenderATPTransformationLayer.build_machine_task(
            machine_task_data
        )

    def stop_and_quarantine_machine_file(self, machine_id, file_hash, comment):
        # type: (unicode, unicode, unicode) -> MachineTask or Exception
        """
        Create Stop And Quarantine Machine file Task
        @param machine_id: Machine ID
        @param file_hash: SHA1 file hash of the file to stop and quarantine
        @param comment: Comment to associate with the action
        @return: Machine Task
        """
        url = urllib.parse.urljoin(
            self.resource,
            self.URLS["stop_and_quarantine_machine_file"].format(machine_id=machine_id),
        )
        params = self._build_api_params()

        data = {"Comment": comment, "Sha1": file_hash}

        response = self.session.post(url, params=params, json=data)
        self._validate_response(
            response,
            f"Failed stop AV and quarantine file with file hash {file_hash} on machine with ID: {machine_id}",
        )

        machine_task_data = response.json()

        return MicrosoftDefenderATPTransformationLayer.build_machine_task(
            machine_task_data
        )

    def get_machine_task_status(self, id):
        # type: (unicode) -> MachineTask or Exception
        """
        Get Machine Task with given ID
        @param id: Machine Task ID
        @return: Machine Task
        """
        url = urllib.parse.urljoin(self.resource, self.URLS["get_machine_task_status"])
        params = self._build_api_params(id=id)

        response = self.session.get(url, params=params)
        self._validate_response(
            response, f"Failed to get machine task status with id: {id}"
        )

        machine_task_data = response.json().get("value", [])

        if not machine_task_data:
            raise MicrosoftDefenderATPError(f"There is no task with id {id}")

        return MicrosoftDefenderATPTransformationLayer.build_machine_task(
            machine_task_data[0]
        )

    def get_file_related_alerts(
        self,
        file_hash,
        statuses=None,
        severities=None,
        categories=None,
        incident_id=None,
    ):
        # type: (unicode, list, list, list, int) -> [Alert] or Exception
        """
        Get Alerts related to file
        @param file_hash: File hash
        @param statuses: Statuses to look for
        @param severities: Severities to look for
        @param categories: Categories to look for
        @param incident_id: Microsoft Defender Incident ID for which you want to find related alerts
        @return: Alerts List
        """
        url = urllib.parse.urljoin(
            self.resource,
            self.URLS["get_file_related_alerts"].format(file_hash=file_hash),
        )
        params = self._build_api_params()

        response = self.session.get(url, params=params)
        self._validate_response(
            response, f"Failed to get related alerts of file with hash {file_hash}"
        )

        alerts_data = response.json().get("value", [])
        alerts = [
            MicrosoftDefenderATPTransformationLayer.build_alert(alert_data)
            for alert_data in alerts_data
        ]

        return self._filter_alerts(
            alerts=alerts,
            statuses=statuses,
            severities=severities,
            categories=categories,
            incident_id=incident_id,
        )

    @staticmethod
    def _filter_alerts(
        alerts, statuses=None, severities=None, categories=None, incident_id=None
    ):
        # type: ([Alert], [unicode], [unicode], [unicode], int) -> object
        """
        Client side filtering alerts (because server side does not work)
        @param alerts: Alerts to filter
        @param statuses: Statuses to look for
        @param severities: Severities to look for
        @param categories: Categories to look for
        @param incident_id: Microsoft Defender Incident ID for which you want to find related alerts
        @return: Filtered Alerts List
        """
        filtered_alerts = []

        for alert in alerts:
            conditions = []

            if statuses:
                conditions.append(alert.status in statuses)

            if severities:
                conditions.append(alert.severity in severities)

            if categories:
                conditions.append(alert.category in categories)

            if incident_id:
                conditions.append(alert.incident_id == incident_id)

            if all(conditions):
                filtered_alerts.append(alert)

        return filtered_alerts

    def get_file_related_machines(
        self,
        file_hash,
        name=None,
        ip=None,
        risk_scores=None,
        health_statuses=None,
        os_platform=None,
        rbac_group_id=None,
    ):
        # type: (unicode, unicode, unicode, list, list, unicode, int) -> [Machine] or Exception
        """
        Get Machines related to file
        @param file_hash: File Hash
        @param name: A part of the name to look for
        @param ip: Machine IP address to look for.
        @param risk_scores: Risk scores to look for
        @param health_statuses: Health status to look for
        @param os_platform: OS platform to look for
        @param rbac_group_id: RBAC Group ID to look for
        @return: Machines List
        """
        url = urllib.parse.urljoin(
            self.resource,
            self.URLS["get_file_related_machines"].format(file_hash=file_hash),
        )
        params = self._build_api_params()

        response = self.session.get(url, params=params)
        self._validate_response(
            response, f"Failed to get related machines of file with hash {file_hash}"
        )

        machines_data = response.json().get("value", [])
        machines = [
            MicrosoftDefenderATPTransformationLayer.build_machine(machine_data)
            for machine_data in machines_data
        ]

        return self._filter_machines(
            machines=machines,
            computer_dns_name=name,
            ip=ip,
            risk_scores=risk_scores,
            health_statuses=health_statuses,
            os_platform=os_platform,
            rbac_group_id=rbac_group_id,
        )

    @staticmethod
    def _filter_machines(
        machines,
        computer_dns_name=None,
        ip=None,
        risk_scores=None,
        health_statuses=None,
        os_platform=None,
        rbac_group_id=None,
    ):
        # type: ([Machine], unicode, unicode, [unicode], [unicode], unicode, int) -> [Machine]
        """
        Client side filtering machines (because server side does not work)
        @param machines: Machines to filter
        @param computer_dns_name: A part of the name to look for
        @param ip: Machine IP address to look for.
        @param risk_scores: Risk scores to look for
        @param health_statuses: Health status to look for
        @param os_platform: OS platform to look for
        @param rbac_group_id: RBAC Group ID to look for
        @return: Filtered Machines List
        """

        filtered_machines = []

        for machine in machines:
            conditions = []

            if computer_dns_name:
                conditions.append(computer_dns_name in machine.computer_dns_name)

            if ip:
                conditions.append(machine.last_ip_address == ip)

            if risk_scores:
                conditions.append(machine.risk_score in risk_scores)

            if health_statuses:
                conditions.append(machine.health_status in health_statuses)

            if os_platform:
                conditions.append(machine.os_platform == os_platform)

            if rbac_group_id:
                conditions.append(machine.rbac_group_id == rbac_group_id)

            if all(conditions):
                filtered_machines.append(machine)

        return filtered_machines

    def run_advanced_hunting_query(self, query):
        # type: (unicode) -> QueryResult or Exception
        """
        Run given query
        @param query: Query to run
        @return: Query Result
        """
        url = urllib.parse.urljoin(
            self.resource, self.URLS["run_advanced_hunting_query"]
        )
        params = self._build_api_params()

        data = {"Query": query}

        response = self.session.post(url, params=params, json=data)
        self._validate_response(response, "Failed to run query")

        query_result_data = response.json()

        return MicrosoftDefenderATPTransformationLayer.build_query_result(
            query_result_data
        )

    def get_file_info(self, file_hash):
        # type: (unicode) -> dict or Exception
        """
        Get Info about file
        @param file_hash: File Hash
        @return: Info dict
        """
        url = urllib.parse.urljoin(
            self.resource, self.URLS["get_file_info"].format(file_hash=file_hash)
        )
        params = self._build_api_params()

        response = self.session.get(url, params=params)
        self._validate_response(response, f"Failed to fetch file with hash {file_hash}")

        return response.json()

    def get_file_stats(self, file_hash):
        # type: (unicode) -> dict or Exception
        """
        Get file stats
        @param file_hash: File Hash
        @return: Stats dict
        """
        url = urllib.parse.urljoin(
            self.resource, self.URLS["get_file_stats"].format(file_hash=file_hash)
        )
        params = self._build_api_params()

        response = self.session.get(url, params=params)
        self._validate_response(response, f"Failed to fetch file with hash {file_hash}")

        return response.json()

    def get_file(self, file_hash):
        # type: (unicode) -> File or Exception
        """
        Get file
        @param file_hash: File Hash
        @return: File
        """
        file_hash = file_hash.lower()
        file_data = {}
        file_info = self.get_file_info(file_hash)
        file_stats = self.get_file_stats(file_hash)

        file_data.update(file_info)
        file_data.update(file_stats)

        return MicrosoftDefenderATPTransformationLayer.build_file(file_data)

    def get_detections_siem(self, since_time_frame):
        # type: (unicode) -> [Detection] or Exception
        """
        Get Detections
        @param since_time_frame: Since what time get detections
        @return: Detections list
        """
        url = urllib.parse.urljoin(
            self.SIEM_DETECTIONS_URL, self.URLS["get_detections_siem"]
        )
        params = self._build_api_params(since_time_frame=since_time_frame)

        response = self.session.get(url, params=params)
        self._validate_response(response, "Failed to fetch siem detections")

        detections_data = response.json()

        return [
            MicrosoftDefenderATPTransformationLayer.build_detection(detection_data)
            for detection_data in detections_data
        ]

    def get_alert_data(self, alert_id, incident_id):
        """
        Get alert data from the incident
        @param alert_id: {str} alert id
        @param incident_id: {int} incident id
        @return: {dict} raw dict of alert data
        """
        url = urllib.parse.urljoin(
            self.defender_api_resource, self.URLS["get_incident"].format(incident_id)
        )
        response = self.session.get(url)
        self._validate_response(
            response, f"Failed to fetch incident by ID {incident_id}"
        )
        return MicrosoftDefenderATPTransformationLayer.get_alert_data(
            response.json(), alert_id
        )

    def delete_indicator(self, indicator_id):
        """
        Delete entity indicator
        :param indicator_id: {str} Indicator ID
        :return:
        """
        url = urllib.parse.urljoin(
            self.resource,
            self.URLS["delete_indicator"].format(indicator_id=indicator_id),
        )
        response = self.session.delete(url)
        self._validate_response(
            response, f"Failed to delete indicator with ID {indicator_id}"
        )

    def get_entities(self, entities, types=None, actions=None, severities=None):
        """
        Get entities by value
        @param entities: List of entity identifiers
        @param types: Indicator types
        @param actions: Indicator actions
        @param severities: Indicator severities
        @return: Indicators
        """
        url = urllib.parse.urljoin(self.resource, self.URLS["entities"])
        params = self._build_api_params(
            entities=entities,
            types=types,
            actions=actions,
            severities=severities,
            for_entities=True,
        )

        response = self.session.get(url, params=params)
        self._validate_response(response, "Failed to fetch indicators")

        return MicrosoftDefenderATPTransformationLayer.build_indicators_list(
            response.json()
        )

    def submit_entity(
        self,
        entity_identifier,
        entity_type,
        title,
        action,
        application,
        severity,
        description,
        recommended_action,
    ):
        """
        Submit entity as indicator
        :param entity_identifier: The entity identifier
        :param entity_type: Type of the entity
        :param title: Title for the indicator
        :param action: Action to apply
        :param application: Application related to entity
        :param severity: Severity level to apply
        :param description: Description for entity
        :param recommended_action: Recommended actions for handling the entity
        :return:
        """
        url = urllib.parse.urljoin(self.resource, self.URLS["entities"])
        payload = {
            "indicatorValue": entity_identifier,
            "indicatorType": entity_type,
            "title": title,
            "application": application,
            "action": action,
            "severity": severity,
            "description": description,
            "recommendedActions": recommended_action,
        }

        if action in ["Audit"]:
            payload["generateAlert"] = True

        response = self.session.post(url, json=payload)
        if response.status_code == 403:
            raise MicrosoftDefenderATPForbiddenError()
        self._validate_response(response, "Failed to submit entity")

    def _build_api_params(
        self,
        incident_id=None,
        statuses=None,
        severities=None,
        categories=None,
        ip=None,
        risk_scores=None,
        health_statuses=None,
        computer_dns_name=None,
        starts_with_computer_dns_name=None,
        os_platform=None,
        rbac_group_id=None,
        last_seen_time_frame=None,
        alert_time_frame=None,
        start_timestamp=None,
        since_time_frame=None,
        expand=None,
        limit=None,
        id=None,
        entities=None,
        types=None,
        actions=None,
        for_entities=False,
        threats: list[str] = None,
        sort_by: str = None,
        sort_order: str = None,
    ):
        """
        Create filtration dict
        @param incident_id: Microsoft Defender Incident ID for which you want to find related alerts
        @param statuses: Statuses to look for
        @param severities: Severities to look for
        @param categories: Categories to look for
        @param ip: IP to look for
        @param risk_scores: Risk Scores to look for
        @param health_statuses: Health Statuses to look for
        @param computer_dns_name: A part of name to look for
        @param starts_with_computer_dns_name: Starts with name to look for
        @param os_platform: OS Platform to look for
        @param rbac_group_id: RBAC Group ID to look for
        @param last_seen_time_frame: Last seen time frame
        @param alert_time_frame: Alert time frame
        @param start_timestamp: Start timestamp
        @param since_time_frame: Since time frame
        @param expand: Expand to look for
        @param limit: How much should be fetched
        @param id: ID to look for
        @param threats: Threats to look for
        @param sort_by: Sort by field
        @param sort_order: Sort order
        @return: Dict of filters
        """
        filter_params = []

        if incident_id:
            filter_params.append(f"incidentId eq {incident_id}")

        if statuses and set(statuses) ^ set(self.DEFAULT_STATUSES):
            filter_params.append(self._get_multiple_value_filter("status", statuses))

        if severities and set(severities) ^ set(self.DEFAULT_SEVERITIES):
            filter_params.append(
                self._get_multiple_value_filter("severity", severities)
            )

        if categories and set(categories) ^ set(self.DEFAULT_CATEGORIES):
            filter_params.append(
                self._get_multiple_value_filter("category", categories)
            )

        threat_filter: str = self._build_threat_filter(threats)
        if threat_filter:
            filter_params.append(threat_filter)

        if ip:
            filter_params.append(f"lastIpAddress eq '{ip}'")

        if risk_scores and set(risk_scores) ^ set(self.DEFAULT_RISK_SCORES):
            filter_params.append(
                self._get_multiple_value_filter("RiskScore", risk_scores)
            )

        if health_statuses and set(health_statuses) ^ set(self.DEFAULT_HEALTH_STATUSES):
            filter_params.append(
                self._get_multiple_value_filter("healthStatus", health_statuses)
            )

        if computer_dns_name:
            filter_params.append(f"contains(computerDnsName, '{computer_dns_name}')")

        if starts_with_computer_dns_name:
            filter_params.append(
                f"startswith(computerDnsName, '{starts_with_computer_dns_name}')"
            )

        if os_platform:
            filter_params.append(f"osPlatform eq '{os_platform}'")

        if rbac_group_id:
            filter_params.append(f"rbacGroupId eq {rbac_group_id}")

        if last_seen_time_frame:
            time = datetime.utcnow() - timedelta(hours=last_seen_time_frame)
            filter_params.append(f"lastSeen ge {time.strftime(self.TIME_FORMAT)}")

        if alert_time_frame:
            time = datetime.utcnow() - timedelta(hours=alert_time_frame)
            filter_params.append(
                f"alertCreationTime ge {time.strftime(self.TIME_FORMAT)}"
            )

        if start_timestamp:
            time = datetime.fromtimestamp(start_timestamp / 1000)
            filter_params.append(
                f"alertCreationTime ge {time.strftime(self.TIME_FORMAT)}"
            )

        if id:
            filter_params.append(f"id eq {id}")

        if entities:
            filter_params.append(
                self._get_multiple_value_filter("indicatorValue", entities)
            )

        if types:
            filter_params.append(
                self._get_multiple_value_filter("indicatorType", types)
            )

        if actions:
            filter_params.append(self._get_multiple_value_filter("action", actions))

        params = {"$filter": " and ".join(filter_params) if filter_params else None}

        if sort_by:
            sort_by_mapping: SingleJson = {
                "First Detection Time": "publishedOn",
                "Severity": "severity",
                "Update Time": "updatedOn",
            }
            order_by_field: str = sort_by_mapping.get(sort_by, sort_by)
            order_direction: str = sort_order.lower() if sort_order else "asc"
            params["$orderby"] = f"{order_by_field} {order_direction}"

        if not for_entities:
            params["$top"] = limit
            params["$expand"] = expand

        if since_time_frame:
            time = datetime.utcnow() - timedelta(hours=since_time_frame)
            params["sinceTimeUtc"] = time.strftime(self.TIME_FORMAT)

        return params

    @staticmethod
    def _build_threat_filter(threats) -> str:
        """Builds an OData filter string based on selected threats.

        Args:
            threats (list): List of threat strings to filter by.

        Returns:
            (str): The OData filter string.
        """
        if not threats:
            return ""

        threat_queries: list[str] = [
            f"ThreatInfo/{THREAT_QUERY_MAPPING[t]} eq true"
            for t in threats if t in THREAT_QUERY_MAPPING
        ]

        return f"({' or '.join(threat_queries)})" if threat_queries else ""

    @staticmethod
    def _get_multiple_value_filter(value_name, value_list):
        # type: (unicode, list) -> unicode
        """
        Join filters
        @param value_name: Name to filter
        @param value_list: List of values to filter
        @return: String filter
        """
        filter_group = " or ".join([f"{value_name} eq '{x}'" for x in value_list])
        return f"({filter_group})"

    @staticmethod
    def _validate_response(response, error_msg="An error occurred"):
        # type: (requests.Response, unicode) -> None or Exception
        """
        Validate Response
        @param response: Response
        @param error_msg: Message to raise with
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            if response.status_code == API_LIMIT_STATUS_CODE:
                raise MicrosoftDefenderATPError(
                    "Action ran into rate limiting. Please try again in a few minutes."
                ) from error

            try:
                response = response.json()
                error_info = response.get("error", {})
                raise MicrosoftDefenderATPError(
                    f'{error_msg}. {error_info.get("message", "") if isinstance(error_info, dict) else error_info}'
                )
            except ValueError:
                raise MicrosoftDefenderATPError(
                    f"{error_msg}: {error} - {response.content}"
                )

    @staticmethod
    def validate_statuses(*statuses):
        # type: (list) -> None or Exception
        """
        Validate Statuses
        @param statuses: Statuses
        """
        statuses = set(statuses)
        default_statuses = set(MicrosoftDefenderATPManager.DEFAULT_STATUSES)
        wrong_statuses = statuses ^ default_statuses & statuses
        if wrong_statuses:
            raise MicrosoftDefenderATPValidationError(
                f"Wrong statuses {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(wrong_statuses)}.\nPossible values are {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(default_statuses)}"
            )

    @staticmethod
    def validate_severities(*severities):
        # type: (list) -> None or Exception
        """
        Validate Severities
        @param severities: Severities
        """
        severities = set(severities)
        default_severities = set(MicrosoftDefenderATPManager.DEFAULT_SEVERITIES)
        wrong_severities = severities ^ default_severities & severities
        if wrong_severities:
            raise MicrosoftDefenderATPValidationError(
                f"Wrong severities {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(wrong_severities)}.\nPossible values are {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(default_severities)}"
            )

    @staticmethod
    def validate_categories(*categories):
        # type: (list) -> None or Exception
        """
        Validate Categories
        @param categories: Categories
        """
        categories = set(categories)
        default_categories = set(MicrosoftDefenderATPManager.DEFAULT_CATEGORIES)
        wrong_categories = categories ^ default_categories & categories
        if wrong_categories:
            raise MicrosoftDefenderATPValidationError(
                f"Wrong categories {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(wrong_categories)}.\nPossible values are {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(default_categories)}"
            )

    @staticmethod
    def validate_classifications(*classifications):
        # type: (list) -> None or Exception
        """
        Validate Classifications
        @param classifications: Classifications
        """
        classifications = set(classifications)
        default_classifications = set(
            MicrosoftDefenderATPManager.DEFAULT_CLASSIFICATIONS
        )
        wrong_classifications = (
            classifications ^ default_classifications & classifications
        )
        if wrong_classifications:
            raise MicrosoftDefenderATPValidationError(
                f"Wrong classifications {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(wrong_classifications)}.\nPossible values are {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(default_classifications)}"
            )

    @staticmethod
    def validate_determinations(*determinations):
        # type: (list) -> None or Exception
        """
        Validate Determinations
        @param determinations: Determinations
        """
        determinations = set(determinations)
        default_determinations = set(MicrosoftDefenderATPManager.DEFAULT_DETERMINATIONS)
        wrong_determinations = determinations ^ default_determinations & determinations
        if wrong_determinations:
            raise MicrosoftDefenderATPValidationError(
                f"Wrong determinations {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(wrong_determinations)}.\nPossible values are {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(default_determinations)}"
            )

    @staticmethod
    def validate_risk_scores(*risk_scores):
        # type: (list) -> None or Exception
        """
        Validate Risk Scores
        @param risk_scores: Risk Scores
        """
        risk_scores = set(risk_scores)
        default_risk_scores = set(MicrosoftDefenderATPManager.DEFAULT_RISK_SCORES)
        wrong_risk_scores = risk_scores ^ default_risk_scores & risk_scores
        if wrong_risk_scores:
            raise MicrosoftDefenderATPValidationError(
                f"Wrong risk scores {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(wrong_risk_scores)}.\nPossible values are {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(default_risk_scores)}"
            )

    @staticmethod
    def validate_health_statuses(*health_statuses):
        # type: (list) -> None or Exception
        """
        Validate Health Statuses
        @param health_statuses: Health Statuses
        """
        health_statuses = set(health_statuses)
        default_health_statuses = set(
            MicrosoftDefenderATPManager.DEFAULT_HEALTH_STATUSES
        )
        wrong_health_statuses = (
            health_statuses ^ default_health_statuses & health_statuses
        )
        if wrong_health_statuses:
            raise MicrosoftDefenderATPValidationError(
                f"Wrong health statuses {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(wrong_health_statuses)}.\nPossible values are {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(default_health_statuses)}"
            )

    @staticmethod
    def validate_isolation_type(isolation_type):
        # type: (unicode) -> None or Exception
        """
        Validate Isolation Type
        @param isolation_type: Isolation Type
        """
        if isolation_type not in MicrosoftDefenderATPManager.POSSIBLE_ISOLATION_TYPES:
            raise MicrosoftDefenderATPValidationError(
                f"Wrong isolation type {isolation_type}.\nPossible values are {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string( MicrosoftDefenderATPManager.POSSIBLE_ISOLATION_TYPES )}"
            )

    @staticmethod
    def validate_av_scan_type(av_scan_type):
        # type: (unicode) -> None or Exception
        """
        Validate Antivirus Scan Type
        @param av_scan_type: Antivirus Scan Type
        """
        if av_scan_type not in MicrosoftDefenderATPManager.POSSIBLE_SCAN_TYPES:
            raise MicrosoftDefenderATPValidationError(
                f"Wrong AV scan type {av_scan_type}.\nPossible values are {MicrosoftDefenderATPManager.convert_list_to_comma_separated_string( MicrosoftDefenderATPManager.POSSIBLE_SCAN_TYPES )}"
            )

    @staticmethod
    def convert_comma_separated_to_list(comma_separated: str) -> list:
        """Convert comma-separated string to list

        Args:
            comma_separated (str): String with comma-separated values

        Returns:
            list: List of values
        """
        if not comma_separated:
            return []

        if isinstance(comma_separated, list):
            return comma_separated

        if (
            isinstance(comma_separated, str)
            and comma_separated.startswith("[")
            and comma_separated.endswith("]")
        ):
            try:
                evaluated = ast.literal_eval(comma_separated)
                if isinstance(evaluated, list):
                    return evaluated
            except (ValueError, SyntaxError):
                pass

        return [item.strip() for item in comma_separated.split(",")]

    @staticmethod
    def validate_sort_order(sort_order: str) -> None:
        """Validate Sort Order

        Args:
            sort_order (str): The sort order to validate.
        """
        if sort_order.lower() not in POSSIBLE_SORT_ORDER:
            utils = MicrosoftDefenderATPManager
            possible_values: str = utils.convert_list_to_comma_separated_string(
                POSSIBLE_SORT_ORDER
            )
            raise MicrosoftDefenderATPValidationError(
                f"Wrong Sort Order {sort_order}. "
                f"Possible values are: {possible_values}"
            )

    @staticmethod
    def validate_threats(*threats: str) -> None:
        """Validate Threats

        Args:
           *threats (str): Variable length threat list.
        """
        threats_set: set = set(threats)
        default_threats: set = set(POSSIBLE_THREATS)
        wrong_threats: set = threats_set - default_threats

        if wrong_threats:
            utils = MicrosoftDefenderATPManager
            wrong_str: str = utils.convert_list_to_comma_separated_string(wrong_threats)
            possible_str: str = utils.convert_list_to_comma_separated_string(
                default_threats
            )

            raise MicrosoftDefenderATPValidationError(
                f"Wrong threats {wrong_str}. "
                f"Possible values are {possible_str}"
            )

    @staticmethod
    def validate_sort_by(sort_by: str) -> None:
        """Validate Sort By

        Args:
            sort_by (str): The Sort By
        """
        if sort_by not in POSSIBLE_SORT_BY:
            possible_values: str = (
                MicrosoftDefenderATPManager.convert_list_to_comma_separated_string(
                    POSSIBLE_SORT_BY
                )
            )
            raise MicrosoftDefenderATPValidationError(
                f"Wrong Sort By {sort_by}.\n"
                f"Possible values are {possible_values}"
            )

    @staticmethod
    def join_validation_errors(validation_errors):
        # type: (list) -> unicode
        """
        Join validation errors list to one string
        @param validation_errors: Validation error messages list
        """
        return "\n".join(validation_errors)

    @staticmethod
    def convert_list_to_comma_separated_string(iterable):
        # type: (list or set) -> unicode
        """
        Convert list to comma separated string
        @param iterable: List or Set to covert
        """
        return ", ".join(iterable)

    def run_live_response_command(self, machine_id: str, commands: list, comment: str):
        """
        Run a live response command on a specific machine.

        Args:
            machine_id: The ID of the machine to run the command on.
            commands: A list of commands to execute.
            comment: A comment for the action.

        Returns:
            The response JSON from the API.
        """
        url = self.get_full_url("run_live_response", machine_id=machine_id)
        payload = {"Commands": commands, "Comment": ""}

        if comment:
            payload["Comment"] = comment

        response = self.session.post(url, json=payload)
        self._validate_response(response, f"Failed to run live response - {machine_id}")
        return response.json()

    def get_live_response_status(self, action_id: str):
        """
        Get the status of a live response action.
        @param action_id: The ID of the action.
        @return: The response JSON from the API.
        """
        url = self.get_full_url("get_live_response_status", action_id=action_id)
        response = self.session.get(url)
        self._validate_response(response, f"Failed to get live response {action_id}")
        return response.json()

    def get_active_machine_actions(self, machine_id: str) -> list[SingleJson]:
        """
        Get active machine actions for a given machine ID.
        @param machine_id: The ID of the machine.
        @return: List of active machine actions.
        """
        url = urllib.parse.urljoin(self.resource, "/api/machineactions")
        filter_str = (
            f"machineId eq '{machine_id}' and (status eq 'Pending' or status eq 'InProgress')"
        )
        params = {"$filter": filter_str}
        response = self.session.get(url, params=params)
        self._validate_response(
            response,
            f"Failed to get active machine actions for {machine_id}",
        )
        return response.json().get("value", [])

    def get_live_response_result_download_link(self, action_id: str):
        """
        Get the download link for the result of a live response action.
        @param action_id: The ID of the action.
        @return: The response JSON from the API.
        """
        url = self.get_full_url(
            "get_live_response_result_download_link", action_id=action_id
        )
        response = self.session.get(url)
        self._validate_response(response, f"Failed to get download link {action_id}")
        return response.json()

    def get_live_response_result(self, download_url: str):
        """
        Download the result of a live response action.
        @param download_url: The URL to download the result from.
        @return: The content of the result file.
        """

        headers = {
            "Authorization": None,
            "Content-Type": None,
        }
        response = self.session.get(download_url, headers=headers)
        self._validate_response(response, f"Failed to download {download_url}")
        return response.content

    def get_machine_vulnerabilities(
        self,
        machine_id: str,
        severities: list[str] | None = None,
        threats: list[str] | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
        limit: int | None = None,
    ) -> list[Vulnerability]:
        """Get vulnerabilities for a machine.

        Args:
            machine_id (str): The unique identifier of the machine.
            severities (list[str] | None): List of severity
            threats (list[str] | None): List of threat types to filter by.
            sort_by (str | None): The field name to sort the results by.
            sort_order (str | None): The order of sorting ('asc' or 'desc').
            limit (int | None): The maximum number of vulnerabilities to return.

        Returns:
            list[Vulnerability]: A list of Vulnerability data model objects.
        """
        url: str = self.get_full_url(
            "get_machine_vulnerabilities",
            machine_id=machine_id,
        )
        params: SingleJson = self._build_api_params(
            severities=severities,
            threats=threats,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        response: requests.Response = self.session.get(url, params=params)
        self._validate_response(
            response,
            f"Failed to fetch vulnerabilities of the machine with id: {machine_id}",
        )

        v_data_list: list = response.json().get("value")
        if v_data_list is None:
            v_data_list: list = response.json().get("vulnerabilities", [])

        vulnerabilities: list[Vulnerability] = [
            MicrosoftDefenderATPTransformationLayer.build_vulnerability(v_data)
            for v_data in v_data_list
        ]

        if threats:
            vulnerabilities: list[Vulnerability] = [
                v for v in vulnerabilities
                if any(
                    getattr(v, THREAT_ATTRIBUTE_MAPPING[t], False)
                    for t in threats if t in THREAT_ATTRIBUTE_MAPPING
                )
            ]

        if sort_by in SORT_KEY_MAPPING:
            reverse: bool = (sort_order or "ASC").upper() == "DESC"
            vulnerabilities.sort(key=SORT_KEY_MAPPING[sort_by], reverse=reverse)

        return vulnerabilities[:limit] if limit else vulnerabilities

    def get_machine_recommendations(
        self,
        machine_id: str,
        limit: int | None = None,
    ) -> list[Recommendation]:
        """Get security recommendations for a specific machine.

        Args:
            machine_id (str): The ID of the machine.
            limit (int | None): The maximum number of recommendations to return.

        Returns:
            list[Recommendation]: A list of recommendation objects.
        """
        url: str = self.get_full_url(
            "get_machine_recommendations",
            machine_id=machine_id,
        )
        params: dict = self._build_api_params(limit=limit)

        response: requests.Response = self.session.get(url, params=params)
        self._validate_response(
            response,
            f"Failed to get recommendations for machine {machine_id}",
        )

        recommendations_data: list[dict] = response.json().get("value", [])

        return [
            MicrosoftDefenderATPTransformationLayer.build_recommendation(
                recommendation_data
            )
            for recommendation_data in recommendations_data
        ]

    def get_user_related_alerts(
        self,
        user_id: str,
        limit: int | None = None,
    ) -> list[Alert]:
        """Get Alerts related to user with given ID

        Args:
            user_id (str): User ID
            limit (int | None): How much alerts should be fetched

        Return:
            Alerts (list[Alert]) : List of alerts
        """
        url: str = self.get_full_url("get_user_related_alerts", user_id=user_id)
        params: SingleJson = self._build_api_params(limit=limit)

        response: requests.Response = self.session.get(url, params=params)
        self._validate_response(
            response,
            f"Failed to fetch related alerts of the user with id: {user_id}",
        )

        user_alerts_data: list[dict] = response.json().get("value", [])

        return [
            MicrosoftDefenderATPTransformationLayer.build_alert(alert_data)
            for alert_data in user_alerts_data
        ]

    def get_all_alerts(
        self,
        limit: int | None,
    ) -> list[Alert]:
        """Retrieves alerts from the Microsoft Defender ATP API.

        Args:
            limit (int | None): How much alerts should be fetched

        Return:
            Alerts (list[Alert]) : List of alerts
        """
        url: str = self.get_full_url("get_alerts")
        params: dict = {}
        if limit:
            params["$top"] = limit

        response: requests.Response = self.session.get(url, params=params)
        self._validate_response(
            response,
            "Failed to fetch alerts",
        )

        alerts_data: list[dict] = response.json().get("value", [])

        return [
            MicrosoftDefenderATPTransformationLayer.build_alert(alert_data)
            for alert_data in alerts_data
        ]


class MicrosoftDefenderATPManagerV2(MicrosoftDefenderATPManager):

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        resource: str,
        microsoft_graph_url: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(client_id, client_secret, tenant_id, resource, **kwargs)
        self.microsoft_graph_url = microsoft_graph_url

        self.graph_token = self._generate_defender_api_token(
            entities_scope=kwargs.get("entities_scope", False), use_graph=True
        )

        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.graph_token}",
                "Content-Type": "application/json",
            }
        )

    def test_connectivity(self) -> None:
        """Function that checks the connection to the Microsoft Defender ATP.

        Raises:
            Exception: If connection fails.
        """
        url = urllib.parse.urljoin(self.microsoft_graph_url, self.URLS["v2_graph"])
        params = self._build_api_params_v2(limit=1)
        response = self.session.get(url, params=params)
        self._validate_response(response, "Unable to connect to Microsoft Defender ATP")

    def get_alerts(
        self,
        alert_time_frame: int | None = None,
        start_timestamp: str | None = None,
        statuses: list[str] | None = None,
        severities: list[str] | None = None,
        categories: list[str] | None = None,
        incident_id: str | None = None,
        limit: int | None = None,
    ) -> list[Alert]:
        """Get Alerts with filtration.

        Args:
            alert_time_frame (int, None): Time frame in hours for which to fetch alerts.
            start_timestamp (str, None): Start timestamp from when to fetch alerts.
            statuses (list[str], None): Statuses of alerts to look for.
            severities (list[str], None): Severities of alerts to look for.
            categories (list[str], None): Categories of alerts to look for.
            incident_id (str, None): Microsoft Defender Incident ID for which you want
            to find related alerts.
            limit (int, None): How much alerts should be fetched.

        Returns:
            list[Alert]: Alerts list.
        """
        url = urllib.parse.urljoin(self.microsoft_graph_url, self.URLS["v2_graph"])
        params = self._build_api_params_v2(
            alert_time_frame=alert_time_frame,
            start_timestamp=start_timestamp,
            statuses=statuses,
            severities=severities,
            categories=categories,
            incident_id=incident_id,
            limit=limit,
        )
        response = self.session.get(url, params=params)
        self._validate_response(response, "Failed to fetch alerts")

        alerts_data = response.json().get("value", [])

        return [
            MicrosoftDefenderATPTransformationLayer.build_alert(alert_data)
            for alert_data in alerts_data
        ]

    def update_alert(
        self,
        alert_id: str,
        status: str | None = None,
        assigned_to: str | None = None,
        classification: str | None = None,
        determination: str | None = None,
    ) -> Alert:
        """Update alert.

        Args:
            alert_id (str): Alert ID to update.
            status (str, None): Status to update.
            assigned_to (str, None): Assigned To to update.
            classification (str, None): Classification to update.
            determination (str, None): Determination to update.

        Returns:
            Alert: Updated Alert.
        """
        url = urllib.parse.urljoin(
            self.microsoft_graph_url,
            self.URLS["update_alert_graph"].format(alert_id=alert_id),
        )

        updated_status = None
        if status:
            updated_status = GRAPH_STATUS_MAPPING.get(status)
            if not updated_status:
                self.siemplify.LOGGER.info(
                    f"Status '{status}' is not supported in Graph API. Ignoring it."
                )

        updated_classification = GRAPH_CLASSIFICATIONS_MAPPING.get(
            classification,
            classification
        )
        updated_determination = GRAPH_DETERMINATIONS_MAPPING.get(
            determination,
            determination
        )

        if updated_classification == "unknown":
            updated_determination = None
        elif updated_classification and updated_determination:
            valid_pairs = GRAPH_VALID_PAIRS.get(updated_classification, [])
            if updated_determination not in valid_pairs:
                self.siemplify.LOGGER.info(
                    f"Determination '{determination}' is not valid for "
                    f"classification '{classification}' in Graph API. "
                    f"Overriding to 'other'."
                )
                updated_determination = "other"

        payload = {}
        if updated_status:
            payload["status"] = updated_status
        if assigned_to:
            payload["assignedTo"] = assigned_to
        if updated_classification:
            payload["classification"] = updated_classification
        if updated_determination:
            payload["determination"] = updated_determination

        response = self.session.patch(url, json=payload)
        self._validate_response(response, f"Failed to update alert with id {alert_id}")

        alert_data = response.json()

        return MicrosoftDefenderATPTransformationLayer.build_alert(alert_data)

    def get_user_related_alerts(
        self,
        user_id: str,
        limit: int,
    ) -> list[Alert]:
        """Get Alerts related to user with given ID

        Args:
            user_id (str): User ID
            limit (int): How much alerts should be fetched

        Returns:
            list[Alert]: List of alerts
        """
        url = urllib.parse.urljoin(
            self.microsoft_graph_url, self.URLS["run_advanced_hunting_graph"]
        )

        kql_query = f"""
        AlertEvidence
        | where AccountName =~ '{user_id}'
        | summarize by AlertId
        | join kind=inner AlertInfo on AlertId
        | project AlertId, Title, Severity, Category, ServiceSource, Timestamp
        | sort by Timestamp desc
        """

        kql_query += f"\n| take {limit}"

        response = self.session.post(url, json={"query": kql_query})
        self._validate_response(
            response, f"Failed Advanced Hunting for user: {user_id}"
        )
        results = response.json().get("results", [])

        return [
            MicrosoftDefenderATPTransformationLayer.build_alert(alert_data)
            for alert_data in results
        ]

    def _build_incident_filter(self, incident_id: str | int | None) -> str | None:
        """Build filter for incident ID."""
        if incident_id:
            return f"incidentId eq '{incident_id}'"
        return None

    def _build_status_filter(self, statuses: list[str] | None) -> str | None:
        """Build filter for statuses."""
        if statuses and set(statuses) ^ set(self.DEFAULT_STATUSES):
            status_values = []
            for s in statuses:
                mapped_status = GRAPH_STATUS_MAPPING.get(s)
                if mapped_status:
                    status_values.append(mapped_status)
                else:
                    self.siemplify.LOGGER.info(
                        f"Status '{s}' is not supported in Graph API. Ignoring it."
                    )

            if status_values:
                return self._get_multiple_value_filter("status", status_values)
        return None

    def _build_severity_filter(self, severities: list[str] | None) -> str | None:
        """Build filter for severities."""
        if severities and set(severities) ^ set(self.DEFAULT_SEVERITIES):
            severity_values = []
            for s in severities:
                mapped_severity = GRAPH_SEVERITY_MAPPING.get(s)
                if mapped_severity:
                    severity_values.append(mapped_severity)
                else:
                    self.siemplify.LOGGER.info(
                        f"Severity '{s}' is not supported in Graph API. Ignoring it."
                    )

            if severity_values:
                return self._get_multiple_value_filter("severity", severity_values)
        return None

    def _build_category_filter(self, categories: list[str] | None) -> str | None:
        """Build filter for categories."""
        if categories and set(categories) ^ set(self.DEFAULT_CATEGORIES):
            return self._get_multiple_value_filter("category", categories)
        return None

    def _build_time_filter(
        self, alert_time_frame: int | None, start_timestamp: int | float | None
    ) -> list[str]:
        """Build filters for time frame."""
        filter_params = []
        creation_time = "createdDateTime"

        if alert_time_frame:
            time = datetime.utcnow() - timedelta(hours=alert_time_frame)
            filter_params.append(
                f"{creation_time} ge {time.strftime(self.TIME_FORMAT)}"
            )

        if start_timestamp:
            time = datetime.fromtimestamp(start_timestamp / 1000)
            filter_params.append(
                f"{creation_time} ge {time.strftime(self.TIME_FORMAT)}"
            )
        return filter_params

    def _build_api_params_v2(
        self,
        incident_id: str | int | None = None,
        statuses: list[str] | None = None,
        severities: list[str] | None = None,
        categories: list[str] | None = None,
        alert_time_frame: int | None = None,
        start_timestamp: int | float | None = None,
        limit: int | None = None,
    ) -> SingleJson:
        """Create filtration dict.

        Args:
            incident_id (str | int, None): Microsoft Defender Incident ID for which you
            want to find related alerts.
            statuses (list[str], None): Statuses to look for.
            severities (list[str], None): Severities to look for.
            categories (list[str], None): Categories to look for.
            alert_time_frame (int, None): Alert time frame in hours.
            start_timestamp (int | float, None): Start timestamp from when to fetch
            alerts.
            limit (int, None): Maximum number of items to return.

        Returns:
            SingleJson: Dict of filters.
        """
        filter_params = []

        incident_filter = self._build_incident_filter(incident_id)
        if incident_filter:
            filter_params.append(incident_filter)

        status_filter = self._build_status_filter(statuses)
        if status_filter:
            filter_params.append(status_filter)

        severity_filter = self._build_severity_filter(severities)
        if severity_filter:
            filter_params.append(severity_filter)

        category_filter = self._build_category_filter(categories)
        if category_filter:
            filter_params.append(category_filter)

        filter_params.extend(self._build_time_filter(alert_time_frame, start_timestamp))

        params = {"$filter": " and ".join(filter_params) if filter_params else None}

        if limit:
            params["$top"] = limit

        return params
