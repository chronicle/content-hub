from __future__ import annotations
import json

from TIPCommon.adapters.pubsub import data_models
from TIPCommon.types import SingleJson

from scc_enterprise.core.GoogleSecurityCommandCenterConstants import (
    EXTERNAL_SYSTEMS_KEY,
    URGENT_POSTURE_DEFAULT_CASE_ID,
)
from scc_enterprise.core.GoogleSecurityCommandCenterDatamodels import *
from scc_enterprise.core.SCCEnterpriseUtils import get_finding_value_by_key


class GoogleSecurityCommandCenterParser:

    def build_finding_details_list(self, raw_data):
        return [
            self.build_finding_details_object(item)
            for item in raw_data.get("listFindingsResults", [])
        ]

    def build_urgent_posture_findings_list(self, received_pubsub_messages):
        return [
            self.build_urgent_posture_finding_object(msg)
            for msg in received_pubsub_messages
        ]

    def build_finding_details_object(self, raw_data):
        finding_data = (
            raw_data.get("finding") if raw_data.get("finding", {}) else raw_data
        )

        attack_exposure = finding_data.get("attackExposure", {})
        aps_score = attack_exposure.get("score")
        aps_state = attack_exposure.get("state", "")
        if aps_score is None and aps_state.upper() == "CALCULATED":
            aps_score = 0

        chronicle_soar_external_systems = finding_data.get("externalSystems", {}).get(
            EXTERNAL_SYSTEMS_KEY, {}
        )

        return FindingDetails(
            raw_data=raw_data,
            name=finding_data.get("name"),
            category=finding_data.get("category"),
            state=finding_data.get("state"),
            mute=finding_data.get("mute"),
            severity=finding_data.get("severity"),
            finding_class=finding_data.get("findingClass"),
            description=finding_data.get("description"),
            event_time=finding_data.get("eventTime"),
            cve_id=finding_data.get("vulnerability", {}).get("cve", {}).get("id"),
            recommendation=finding_data.get("sourceProperties", {}).get(
                "Recommendation"
            ),
            resource_name=finding_data.get("resourceName"),
            resource_data=raw_data.get("resource"),
            external_systems=self.build_chronicle_soar_external_systems(
                chronicle_soar_external_systems
            ),
            aps_score=aps_score,
        )

    @staticmethod
    def build_notifications_config_object(raw_data):
        return NotificationsConfig(
            raw_data=raw_data,
            name=raw_data.get("name", "").split("/")[-1],
            config_id=raw_data.get("name", ""),
            pubsub_topic=raw_data.get("pubsubTopic"),
            service_account=raw_data.get("serviceAccount"),
            streaming_config=raw_data.get("streamingConfig"),
        )

    def build_urgent_posture_finding_object(
        self, received_pubsub_message: data_models.ReceivedMessage
    ):
        # received_pubsub_message.message.data <- finding + resource + tags
        message_data = json.loads(received_pubsub_message.message.data)

        finding_data = message_data.get("finding")
        resource_data = message_data.get("resource", {})
        effective_tags = message_data.get("effectiveTags", [])

        attack_exposure = finding_data.get("attackExposure", {})
        aps_score = attack_exposure.get("score")
        aps_state = attack_exposure.get("state", "")
        if aps_score is None and aps_state.upper() == "CALCULATED":
            aps_score = 0

        chronicle_soar_external_systems = finding_data.get("externalSystems", {}).get(
            EXTERNAL_SYSTEMS_KEY, {}
        )
        organization_id = get_finding_value_by_key(
            finding_data["parent"], key="organizations"
        )

        return PostureFindingAlert(
            ack_id=received_pubsub_message.ack_id,
            event_time=finding_data.get("eventTime"),
            raw_data=finding_data,
            resource=self.build_resource_object(
                resource_data, organization_id=organization_id
            ),
            external_systems=self.build_chronicle_soar_external_systems(
                chronicle_soar_external_systems
            ),
            organization_id=organization_id,
            cve_id=(finding_data.get("vulnerability", {}).get("cve", {}).get("id")),
            contacts=finding_data.get("contacts", {}),
            state=finding_data.get("state"),
            mute=finding_data.get("mute"),
            mute_update_time=finding_data.get("muteUpdateTime"),
            effective_tags=effective_tags,
            group_memberships=finding_data.get("groupMemberships", []),
            tc_related_findings=(
                finding_data.get("toxicCombination", {}).get("relatedFindings")
            ),
            aps_score=aps_score,
            toxic_aps_score=(
                finding_data.get("toxicCombination", {}).get("attackExposureScore")
            ),
            finding_class=finding_data.get("findingClass"),
            notification_config_name=message_data.get("notificationConfigName"),
        )

    def build_resource_object(
        self, raw_data: SingleJson, organization_id: str
    ) -> Resource:
        return Resource(
            raw_data,
            cloud_provider=raw_data.get("cloudProvider"),
            type_=raw_data.get("type"),
            display_name=raw_data.get("displayName"),
            project_display_name=raw_data.get("projectDisplayName"),
            cloud_metadata=(
                raw_data.get("awsMetadata", {})
                or raw_data.get("gcpMetadata", {})
                or raw_data.get("azureMetadata", {})
            ),
            organization_id=organization_id,
        )

    def build_external_systems_ticket(self, raw_data: dict):
        return ExternalSystemsTicket(
            raw_data=raw_data,
            id_=raw_data.get("id"),
            assignee=raw_data.get("assignee"),
            description=raw_data.get("description"),
            uri=raw_data.get("uri"),
            status=raw_data.get("status"),
            update_time=raw_data.get("updateTime"),
        )

    def build_sources_list(self, raw_data):
        return [self.build_source_object(item) for item in raw_data.get("sources", [])]

    def build_source_object(self, raw_data: dict):
        return Source(
            raw_data=raw_data,
            name=raw_data.get("name"),
            description=raw_data.get("description"),
            display_name=raw_data.get("displayName"),
        )

    def build_chronicle_soar_external_systems(
        self, chronicle_soar_external_systems: dict
    ):
        return ChronicleSoarExternalSystems(
            raw_data=chronicle_soar_external_systems,
            name=chronicle_soar_external_systems.get("name"),
            assignees=chronicle_soar_external_systems.get("assignees"),
            case_id=chronicle_soar_external_systems.get(
                "externalUid", URGENT_POSTURE_DEFAULT_CASE_ID
            ),
            status=chronicle_soar_external_systems.get("status"),
            external_system_update_time=(
                chronicle_soar_external_systems.get("externalSystemUpdateTime")
            ),
            case_uri=chronicle_soar_external_systems.get("caseUri"),
            case_priority=chronicle_soar_external_systems.get("casePriority"),
            case_sla=chronicle_soar_external_systems.get("caseSla"),
            ticket_info=(
                self.build_external_systems_ticket(
                    chronicle_soar_external_systems.get("ticketInfo")
                )
                if chronicle_soar_external_systems.get("ticketInfo")
                else None
            ),
        )
