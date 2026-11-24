from __future__ import annotations
from sentinel_one_v2.core.datamodels import *
from sentinel_one_v2.core.constants import ACTIVITY_TYPE


class SentinelOneV2Parser:
    def build_results(self, raw_json, method, pure_data=False, limit=None, *kwargs):
        return [
            getattr(self, method)(item_json, *kwargs)
            for item_json in (raw_json if pure_data else raw_json.get("data", []))[
                :limit
            ]
        ]

    def build_result(self, raw_json, method, *kwargs):
        return getattr(self, method)(raw_json.get("data", {}), *kwargs)

    @staticmethod
    def get_next_cursor(raw_json):
        return raw_json.get("pagination", {}).get("nextCursor")

    @staticmethod
    def get_query_id(raw_json):
        return raw_json.get("data", {}).get("queryId")

    @staticmethod
    def get_query_status(raw_json):
        return raw_json.get("data", {}).get("responseState")

    @staticmethod
    def get_paginated_data(raw_json, field_name=None):
        return (
            raw_json.get("data", {}).get(field_name, [])
            if field_name
            else raw_json.get("data", [])
        )

    @staticmethod
    def get_response_state(raw_json):
        return raw_json.get("data", {}).get("responseState")

    @staticmethod
    def get_affected(raw_json):
        return raw_json.get("data", {}).get("affected", 0)

    @staticmethod
    def get_moved_count(raw_json):
        return raw_json.get("data", {}).get("agentsMoved", 0)

    @staticmethod
    def build_siemplify_system_info_obj(raw_json):
        return SystemInfo(raw_json)

    @staticmethod
    def build_siemplify_system_status_obj(system_status_data):
        return SystemStatus(
            raw_data=system_status_data,
            is_ok=system_status_data.get("data", {}).get("health", "").lower() == "ok",
            errors=system_status_data.get("errors", []),
        )

    @staticmethod
    def build_siemplify_agent_obj(agent_data):
        interfaces = [
            SentinelOneV2Parser.build_siemplify_agent_inteface_obj(interface)
            for interface in agent_data.get("networkInterfaces", [])
        ]
        return Agent(raw_data=agent_data, interfaces=interfaces, **agent_data)

    @staticmethod
    def build_siemplify_agent_inteface_obj(interface_data):
        return AgentInterface(raw_data=interface_data, **interface_data)

    @staticmethod
    def build_siemplify_event_obj(event_data):
        return Event(raw_data=event_data, **event_data)

    @staticmethod
    def build_siemplify_process_event_obj(event_data):
        return ProcessEvent(raw_data=event_data, **event_data)

    @staticmethod
    def build_siemplify_file_event_obj(event_data):
        return FileEvent(raw_data=event_data, **event_data)

    @staticmethod
    def build_siemplify_indicator_event_obj(event_data):
        return IndicatorEvent(raw_data=event_data, **event_data)

    @staticmethod
    def build_siemplify_dns_event_obj(event_data):
        return DNSEvent(raw_data=event_data, **event_data)

    @staticmethod
    def build_siemplify_network_actions_event_obj(event_data):
        return NetworkActionsEvent(raw_data=event_data, **event_data)

    @staticmethod
    def build_siemplify_url_event_obj(event_data):
        return URLEvent(raw_data=event_data, **event_data)

    @staticmethod
    def build_siemplify_registry_event_obj(event_data):
        return RegistryEvent(raw_data=event_data, **event_data)

    @staticmethod
    def build_siemplify_scheduled_task_event_obj(event_data):
        return ScheduledTaskEvent(raw_data=event_data, **event_data)

    @staticmethod
    def build_hash_obj(hash_data):
        rank = hash_data.get("data", {}).get("rank")
        if not rank:
            return None
        return Hash(raw_data=hash_data, rank=rank)

    @staticmethod
    def build_path_obj(path_data):
        return PathObject(
            raw_data=path_data,
            value=path_data.get("value", ""),
            created_at=path_data.get("createdAt", ""),
            path_id=path_data.get("id", ""),
            scope_name=path_data.get("scopeName", ""),
        )

    @staticmethod
    def build_threat_event_obj(event_data):
        return ThreatEvent(raw_data=event_data)

    @staticmethod
    def build_threat_obj(threat_data):
        return Threat(
            raw_data=threat_data,
            threat_id=threat_data.get("id"),
            threat_name=threat_data.get("threatName"),
            agent_id=threat_data.get("agentId"),
            created_at=threat_data.get("createdAt"),
            classification=threat_data.get("classification"),
            description=threat_data.get("description"),
            mitigation_status=threat_data.get("mitigationStatus"),
            site_id=threat_data.get("siteId"),
            site_name=threat_data.get("siteName"),
            rank=threat_data.get("rank"),
            marked_as_benign=threat_data.get("markedAsBenign"),
            in_quarantine=threat_data.get("inQuarantine"),
            hash_value=threat_data.get("fileContentHash"),
            resolved=threat_data.get("resolved"),
        )

    @staticmethod
    def build_blacklisted_threat_obj(threat_data):
        return BlacklistedThreat(
            raw_data=threat_data,
            hash_value=threat_data.get("value"),
            scope_name=threat_data.get("scopeName", ""),
            os_type=threat_data.get("osType", ""),
            description=threat_data.get("description", ""),
            username=threat_data.get("userName", ""),
            hash_id=threat_data.get("id", ""),
        )

    @staticmethod
    def build_group_obj(group_data):
        return Group(raw_data=group_data, **group_data)

    @staticmethod
    def build_deep_visibility_query_event(event_data):
        return QueryEvent(raw_data=event_data, **event_data)

    @staticmethod
    def build_application_object(raw_data):
        return Application(
            raw_data=raw_data,
            installed_date=raw_data.get("installedDate", ""),
            name=raw_data.get("name", ""),
            publisher=raw_data.get("publisher", ""),
            size=raw_data.get("size", ""),
            version=raw_data.get("version", ""),
        )

    @staticmethod
    def get_fetch_job_affected(raw_data):
        return raw_data.get("data", {}).get("affected")

    @staticmethod
    def get_file_data_from_timeline(raw_data):
        data = raw_data.get("data", [])
        current_file = next(
            (item for item in data if item.get("activityType") == ACTIVITY_TYPE), {}
        )
        return current_file.get("data", {}).get("fileDisplayName"), current_file.get(
            "data", {}
        ).get("downloadUrl")

    @staticmethod
    def build_site_object(raw_data):
        return Site(
            raw_data=raw_data,
            name=raw_data.get("name"),
            id=raw_data.get("id"),
            creator=raw_data.get("creator"),
            expiration=raw_data.get("expiration"),
            site_type=raw_data.get("siteType"),
            state=raw_data.get("state"),
        )
