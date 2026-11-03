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
# ============================= IMPORTS ===================================== #

from typing import TYPE_CHECKING

from .constants import GRAPH_SEVERITY_MAPPING
from .datamodels import (
    Alert,
    Machine,
    User,
    File,
    Detection,
    QueryResult,
    MachineTask,
    SiemplifyPriorityEnum,
    DefenderPriorityEnum,
    Indicator,
    Vulnerability,
    Recommendation,
)

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


# ============================= CLASSES ===================================== #


class MicrosoftDefenderATPTransformationLayerError(Exception):
    """
    General Exception for AzureAD DataModel TransformationLayer
    """

    pass


class MicrosoftDefenderATPTransformationLayer:

    @staticmethod
    def _apply_mappings(alert_data: SingleJson) -> None:
        """Apply basic mappings to alert data."""
        mappings = {
            "AlertId": "id",
            "Title": "title",
            "Category": "category",
            "Status": "status",
            "Severity": "severity",
            "Timestamp": "alertCreationTime",
        }
        for k, v in mappings.items():
            if k in alert_data and v not in alert_data:
                alert_data[v] = alert_data[k]

        if "createdDateTime" in alert_data:
            alert_data["alertCreationTime"] = alert_data.get("createdDateTime")

    @staticmethod
    def _normalize_user(alert_data: SingleJson) -> None:
        """Normalize user field in alert data."""
        if "AccountName" in alert_data and not alert_data.get("user"):
            alert_data["user"] = {
                "accountName": alert_data.get("AccountName"),
                "domainName": alert_data.get("DeviceDomain"),
            }

    @staticmethod
    def _normalize_files(alert_data: SingleJson) -> None:
        """Normalize files field in alert data."""
        if ("SHA1" in alert_data or "SHA256" in alert_data) and not alert_data.get(
            "files"
        ):
            alert_data["files"] = [
                {
                    "sha1": alert_data.get("SHA1"),
                    "sha256": alert_data.get("SHA256"),
                    "fileName": alert_data.get("FileName"),
                    "filePath": alert_data.get("FilePath"),
                }
            ]

    @staticmethod
    def _process_evidence(alert_data: SingleJson) -> None:
        """Process evidence field in alert data."""
        evidence = alert_data.get("evidence", [])
        if evidence:
            if not alert_data.get("machineId"):
                alert_data["machineId"] = next(
                    (
                        e.get("mdeDeviceId")
                        for e in evidence
                        if "deviceEvidence" in e.get("@odata.type", "")
                    ),
                    None,
                )

            if not alert_data.get("user"):
                alert_data["user"] = next(
                    (
                        e.get("userAccount")
                        for e in evidence
                        if "userEvidence" in e.get("@odata.type", "")
                    ),
                    None,
                )

            if not alert_data.get("files"):
                file_evidences = [
                    e.get("fileDetails", {})
                    for e in evidence
                    if "fileEvidence" in e.get("@odata.type", "")
                ]
                if file_evidences:
                    alert_data["files"] = [
                        {
                            "sha1": f.get("sha1"),
                            "sha256": f.get("sha256"),
                            "fileName": f.get("fileName"),
                            "filePath": f.get("filePath"),
                        }
                        for f in file_evidences
                    ]

    @staticmethod
    def build_alert(alert_data: SingleJson) -> Alert:
        """Build Alert object from raw data."""
        MicrosoftDefenderATPTransformationLayer._apply_mappings(alert_data)
        MicrosoftDefenderATPTransformationLayer._normalize_user(alert_data)
        MicrosoftDefenderATPTransformationLayer._normalize_files(alert_data)
        MicrosoftDefenderATPTransformationLayer._process_evidence(alert_data)

        return Alert(raw_data=alert_data, **alert_data)

    @staticmethod
    def build_machine(machine_data):
        return Machine(raw_data=machine_data, **machine_data)

    @staticmethod
    def build_user(user_data):
        return User(raw_data=user_data, **user_data)

    @staticmethod
    def build_file(file_data):
        return File(raw_data=file_data, **file_data)

    @staticmethod
    def build_detection(detection_data):
        return Detection(raw_data=detection_data, **detection_data)

    @staticmethod
    def build_query_result(query_result_data):
        return QueryResult(raw_data=query_result_data, **query_result_data)

    @staticmethod
    def build_machine_task(machine_task_data):
        return MachineTask(raw_data=machine_task_data, **machine_task_data)

    @staticmethod
    def build_vulnerability(vulnerability_data):
        return Vulnerability(raw_data=vulnerability_data, **vulnerability_data)

    @staticmethod
    def calculate_priority(alert_severity: str, use_v2_api: bool = False) -> int:
        """Calculates case priority by the Priority Map.

        Args:
            alert_severity (str): Severity value as it came from Sentinel.
            use_v2_api (bool): True if Graph API is used.

        Returns:
            int: Calculated Siemplify alarm priority.
        """
        if not isinstance(alert_severity, str):
            return SiemplifyPriorityEnum.INFO.value

        severity_lower: str = alert_severity.lower()

        if use_v2_api:
            reverse_mapping: dict[str, str] = {
                v.lower(): k
                for k, v in GRAPH_SEVERITY_MAPPING.items()
            }
            mapped_severity: str = reverse_mapping.get(severity_lower, alert_severity)
            severity_lower = mapped_severity.lower()

        dpe = DefenderPriorityEnum
        spe = SiemplifyPriorityEnum

        mapping: dict[str, int] = {
            dpe.UNSPECIFIED.value.lower(): spe.UNSPECIFIED.value,
            dpe.INFO.value.lower(): spe.INFO.value,
            dpe.LOW.value.lower(): spe.LOW.value,
            dpe.MEDIUM.value.lower(): spe.MEDIUM.value,
            dpe.HIGH.value.lower(): spe.HIGH.value,
        }

        return mapping.get(severity_lower, SiemplifyPriorityEnum.INFO.value)

    @staticmethod
    def get_alert_data(incident, alert_id):
        return next(
            (
                alert
                for alert in incident.get("alerts", [])
                if alert.get("alertId") == alert_id
            ),
            {},
        )

    @staticmethod
    def build_indicators_list(raw_data):
        return [
            MicrosoftDefenderATPTransformationLayer.build_indicator(indicator_data)
            for indicator_data in raw_data.get("value", [])
        ]

    @staticmethod
    def build_indicator(indicator_data):
        return Indicator(
            raw_data=indicator_data,
            identifier=indicator_data.get("id"),
            indicator_value=indicator_data.get("indicatorValue"),
            indicator_type=indicator_data.get("indicatorType"),
            action=indicator_data.get("action"),
            severity=indicator_data.get("severity"),
            description=indicator_data.get("description"),
            title=indicator_data.get("title"),
            recommended_actions=indicator_data.get("recommendedActions"),
        )

    @staticmethod
    def build_recommendation(recommendation_data):
        return Recommendation(raw_data=recommendation_data, **recommendation_data)
