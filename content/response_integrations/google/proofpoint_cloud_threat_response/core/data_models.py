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

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from TIPCommon.transformation import dict_to_flat
from ..core import constants

if TYPE_CHECKING:
    from typing import Self

    from EnvironmentCommon import EnvironmentHandle
    from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
    from TIPCommon.types import SingleJson


@dataclass(slots=True)
class IntegrationParameters:
    api_root: str
    client_id: str
    client_secret: str
    verify_ssl: bool


@dataclass(frozen=True, slots=True)
class ProofpointIncident:
    id_: str
    created_at: str
    status: str
    raw_data: SingleJson = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        return "Incident"

    @classmethod
    def from_json(cls, data: SingleJson) -> Self:
        return cls(
            id_=data.get("id", ""),
            created_at=data.get("createdAt", ""),
            status=data.get("state", ""),
            raw_data=data,
        )

    def to_flat_event(self) -> SingleJson:
        flat = dict_to_flat(self.raw_data)
        flat["event_type"] = self.event_type
        return flat

    def created_ts_ms(self) -> int:
        dt_obj = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        return int(dt_obj.timestamp() * 1000)

    def get_priority(self) -> str:
        return constants.AlertSeverityEnum(
            self.raw_data.get("priority", constants.DEFAULT_PRIORITY)
        )


@dataclass(frozen=True, slots=True)
class ProofpointMessage:
    """Minimal + raw_data for everything else."""

    id_: str
    created_at: str
    raw_data: SingleJson = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        return "Message"

    @classmethod
    def from_json(cls, data: SingleJson) -> Self:
        return cls(
            id_=data.get("id", ""),
            created_at=data.get("createdAt", ""),
            raw_data=data,
        )

    def to_flat_event(self) -> SingleJson:
        flat = dict_to_flat(self.raw_data)
        flat["event_type"] = self.event_type
        return flat


class ProofpointIncidentAlertInfo(AlertInfo):
    """Custom AlertInfo for Proofpoint CTR incidents."""

    @classmethod
    def build_alert(
        cls,
        incident: ProofpointIncident,
        messages_raw_list: SingleJson,
        env_common: EnvironmentHandle,
        environment_field_name: str | None = None,
    ) -> Self:
        """ Build soar alert object.

        Args:
            incident(ProofpointIncident): Incidents of proofpoint cloud threat response.
            messages_raw_list(SingleJson): Messages related to incidents.
            env_common(EnvironmentHandle): EnvironmentHandle Object.
            environment_field_name(str): Environment to be used for alert ingestion.

        Returns:
            Self: ProofpointIncidentAlertInfo object.
        """
        alert = cls()
        alert.display_id = f"ProofpointCTR_{incident.id_}"
        alert.alert_id = incident.id_
        alert.ticket_id = incident.id_
        alert.name = incident.raw_data.get("title", incident.id_)
        alert.priority = incident.get_priority().priority
        alert.extensions = {
            "RiskScore": incident.get_priority().risk_score,
            "Severity": incident.get_priority().severity,
        }
        alert.device_vendor = constants.DEFAULT_VENDOR
        alert.device_product = constants.DEFAULT_PRODUCT
        alert.rule_generator = f"Proofpoint CTR Incident: {alert.name}"
        env_data = {}
        if environment_field_name:
            env_value = incident.raw_data.get(environment_field_name)
            if env_value:
                env_data[environment_field_name] = env_value
        alert.environment = env_common.get_environment(env_data)

        ts_ms = incident.created_ts_ms()
        alert.start_time = alert.end_time = ts_ms

        alert.events = [incident.to_flat_event()] + [
            msg.to_flat_event() for msg in messages_raw_list
        ]
        alert.incident_raw_data = incident.raw_data

        return alert

    def pass_filter(
        self,
        soar_connector: SiemplifyConnectorExecution,
        use_dynamic_list_as_blocklist: bool,
    ) -> bool:
        """Checks whether the alert passes the user given filter.

        Args:
            soar_connector (SiemplifyConnectorExecution): Soar connector object.
            use_dynamic_list_as_blocklist (bool): Boolean to use dynamic list.

        Returns:
            bool: True, if passes the filter else False.
        """
        whitelist = soar_connector.whitelist
        if not whitelist:
            return True

        sources: set[str] = set()
        for source_type in self.incident_raw_data.get("sourceTypes", []):
            sources.add(str(source_type))
        if not sources:
            return use_dynamic_list_as_blocklist

        if use_dynamic_list_as_blocklist:
            return not any(src in whitelist for src in sources)

        return any(src in whitelist for src in sources)
