from __future__ import annotations
from .datamodels import UDSOEntry, SecurityAgent, EnabledEndpointSecurityAgent


class TrendMicroApexCentralParser:
    """
    Trend Micro Apex Central Transformation Layer
    """

    @staticmethod
    def extract_api_error_message(raw_response):
        return (
            raw_response.get("result_description")
            or raw_response.get("Meta", {}).get("ErrorMsg")
            or raw_response.get("Response", {}).get("Meta", {}).get("ErrorMsg")
            or raw_response
        )

    @staticmethod
    def build_list_udso_entries(raw_data) -> [UDSOEntry]:
        return [
            TrendMicroApexCentralParser.build_udso_entry(raw_entry)
            for raw_entry in raw_data.get("Data", [])
        ]

    @staticmethod
    def build_udso_entry(raw_data) -> UDSOEntry:
        return UDSOEntry(
            raw_data,
            type=raw_data.get("type"),
            content=raw_data.get("content"),
            notes=raw_data.get("notes"),
            scan_action=raw_data.get("scan_action"),
            expiration_utc_date=raw_data.get("expiration_utc_date"),
        )

    @staticmethod
    def build_list_security_agents(raw_data) -> [SecurityAgent]:
        return [
            TrendMicroApexCentralParser.build_security_agent(raw_agent)
            for raw_agent in raw_data.get("result_content", [])
        ]

    @staticmethod
    def build_security_agent(raw_data) -> SecurityAgent:
        return SecurityAgent(
            raw_data,
            entity_id=raw_data.get("entity_id"),
            product=raw_data.get("product"),
            managing_server_id=raw_data.get("managing_server_id"),
            ad_domain=raw_data.get("ad_domain"),
            folder_path=raw_data.get("folder_path"),
            ip_address_list=raw_data.get("ip_address_list"),
            mac_address_list=raw_data.get("mac_address_list"),
            host_name=raw_data.get("host_name"),
            isolation_status=raw_data.get("isolation_status"),
        )

    @staticmethod
    def extract_if_more_results_available_to_retrieve_all_security_agents_with_enabled_endpoint(
        raw_data,
    ) -> bool:
        return raw_data.get("Data", {}).get("Data", {}).get("hasMore", False)

    @staticmethod
    def build_list_of_security_agents_with_enabled_endpoint(
        raw_data,
    ) -> [EnabledEndpointSecurityAgent]:
        enabled_endpoints = raw_data.get("Data", {}).get("Data", {}).get("content", [])
        security_agents = []
        for enabled_endpoint in enabled_endpoints:
            print(f"Enabled endpoint {enabled_endpoint}")
            security_agents.extend(
                [
                    TrendMicroApexCentralParser.build_enabled_endpoint_security_agent(
                        raw_agent_data
                    )
                    for raw_agent_data in enabled_endpoint.get("content", {}).get(
                        "agentEntity", []
                    )
                ]
            )
        return security_agents

    @staticmethod
    def build_enabled_endpoint_security_agent(
        raw_enabled_endpoint_agent,
    ) -> EnabledEndpointSecurityAgent:
        return EnabledEndpointSecurityAgent(
            raw_data=raw_enabled_endpoint_agent,
            agent_guid=raw_enabled_endpoint_agent.get("agentGuid"),
            server_guid=raw_enabled_endpoint_agent.get("serverGuid"),
            machine_name=raw_enabled_endpoint_agent.get("machineName"),
            is_important=raw_enabled_endpoint_agent.get("isImportant"),
            is_online=raw_enabled_endpoint_agent.get("isOnline"),
            ip=raw_enabled_endpoint_agent.get("ip"),
            machine_guid=raw_enabled_endpoint_agent.get("machineGuid"),
            machine_type=raw_enabled_endpoint_agent.get("machineType"),
            machine_os=raw_enabled_endpoint_agent.get("machineOS"),
            isolation_status=raw_enabled_endpoint_agent.get("isolateStatus"),
            is_enabled=raw_enabled_endpoint_agent.get("isEnable"),
            username=raw_enabled_endpoint_agent.get("userName"),
            user_guid=raw_enabled_endpoint_agent.get("userGuid"),
            product_type=raw_enabled_endpoint_agent.get("productType"),
        )
