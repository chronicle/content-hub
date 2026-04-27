from __future__ import annotations
from .datamodels import *


class RSAParser:
    def build_event_object(self, raw_json):
        return Event(raw_data=raw_json)

    def get_session_ids_list(self, raw_json):
        return [
            id_dict["value"]
            for id_dict in raw_json.get("results", {}).get("fields", [])
            if id_dict.get("id1") != 0 and id_dict.get("id2") != 0
        ]

    def build_service_object(self, raw_data):
        if raw_data:
            raw_json = raw_data[0]
            return Service(raw_data=raw_json, id=raw_json.get("id"))

    def build_host_object(self, raw_data):
        items = raw_data.get("items", [])
        if items:
            raw_json = items[0]
            return HostEntity(
                raw_data=raw_json,
                agent_id=raw_json.get("agentId"),
                hostname=raw_json.get("hostName"),
                risk_score=raw_json.get("riskScore"),
                network_interfaces=[
                    self.build_network_interface_object(network_interface)
                    for network_interface in raw_json.get("networkInterfaces", [])
                ],
                last_seen_time=raw_json.get("lastSeenTime"),
            )

    def build_network_interface_object(self, raw_json):
        return NetworkInterface(
            raw_data=raw_json,
            name=raw_json.get("name"),
            mac_address=raw_json.get("macAddress"),
            ipv4=" ".join(ip for ip in raw_json.get("ipv4", [])),
            ipv6=" ".join(ip for ip in raw_json.get("ipv6", [])),
            network_idv6=" ".join(ip for ip in raw_json.get("networkIdv6", [])),
            gateway=" ".join(ip for ip in raw_json.get("gateway", [])),
            dns=" ".join(ip for ip in raw_json.get("dns", [])),
            promiscuous=raw_json.get("promiscuous"),
        )

    def build_file_object(self, raw_data):
        items = raw_data.get("items", [])
        if items:
            raw_json = items[0]
            return FileObject(
                raw_data=raw_json,
                filename=raw_json.get("firstFileName"),
                reputation_status=raw_json.get("reputationStatus"),
                global_risk_score=raw_json.get("globalRiskScore"),
                machine_os_type=raw_json.get("machineOsType"),
                size=raw_json.get("size"),
                checksum_md5=raw_json.get("checksumMd5"),
                checksum_sha1=raw_json.get("checksumSha1"),
                checksum_sha256=raw_json.get("checksumSha256"),
                entropy=raw_json.get("entropy"),
                format=raw_json.get("format"),
                file_status=raw_json.get("fileStatus"),
                remediation_action=raw_json.get("remediationAction"),
            )

    def build_incident_object(self, raw_json) -> Incident:
        return Incident(
            raw_data=raw_json,
            id=raw_json.get("id"),
            title=raw_json.get("title"),
            summary=raw_json.get("summary"),
            priority=raw_json.get("priority"),
            risk_score=raw_json.get("riskScore"),
            status=raw_json.get("status"),
            alert_count=raw_json.get("alertCount"),
            average_alert_risk_score=raw_json.get("averageAlertRiskScore"),
            created=raw_json.get("created"),
            last_updated=raw_json.get("lastUpdated"),
            rule_id=raw_json.get("ruleId"),
            first_alert_time=raw_json.get("firstAlertTime"),
            created_by=raw_json.get("createdBy"),
            event_count=raw_json.get("eventCount"),
        )

    def build_incident_object_list(self, raw_json) -> [Incident]:
        return [self.build_incident_object(raw_incident) for raw_incident in raw_json]

    def build_error_object(self, raw_json):
        errors = raw_json.get("errors", [])
        message = errors[0].get("message") if errors else ""
        return ErrorObject(raw_data=raw_json, message=message)

    def build_alert_object_list(self, raw_json) -> [IncidentAlert]:
        return [
            self.build_alert_object(raw_alert)
            for raw_alert in raw_json.get("items", [])
        ]

    def build_alert_object(self, raw_json) -> IncidentAlert:
        return IncidentAlert(
            raw_data=raw_json,
            id=raw_json.get("id"),
            title=raw_json.get("title"),
            detail=raw_json.get("detail"),
            created=raw_json.get("created"),
            source=raw_json.get("source"),
            risk_score=raw_json.get("riskScore"),
            type=raw_json.get("type"),
            events=[
                self.build_alert_event_object(raw_event)
                for raw_event in raw_json.get("events", [])
            ],
        )

    def build_alert_event_object(self, raw_json) -> IncidentAlert.Event:
        return IncidentAlert.Event(
            raw_data=raw_json,
            domain=raw_json.get("domain"),
            event_source=raw_json.get("eventSource"),
            event_source_id=raw_json.get("eventSourceId"),
        )

    def build_event_additional_data_list(self, raw_json) -> [EventAdditionalData]:
        return [
            self.build_event_additional_data_object(raw_object)
            for raw_object in raw_json.get("results", {}).get("fields", [])
        ]

    def build_event_additional_data_object(self, raw_json) -> EventAdditionalData:
        return EventAdditionalData(
            raw_data=raw_json, type=raw_json.get("type"), value=raw_json.get("value")
        )

    def build_event_metadata_object(self, raw_json) -> EventMetadata:
        return EventMetadata(
            raw_data=raw_json,
            field_1=raw_json.get("params", {}).get("field1"),
            field_2=raw_json.get("params", {}).get("field2"),
        )
