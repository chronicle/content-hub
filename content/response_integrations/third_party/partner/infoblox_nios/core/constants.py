from __future__ import annotations

INTEGRATION_NAME = "Infoblox NIOS"

RESULT_VALUE_TRUE = True
RESULT_VALUE_FALSE = False
DEFAULT_DEVICE_VENDOR = "Infoblox"
DEFAULT_DEVICE_PRODUCT = INTEGRATION_NAME
RULE_GENERATOR = DEFAULT_DEVICE_VENDOR
COMMON_ACTION_ERROR_MESSAGE = "Error while executing action {}. Reason: {}"
DEFAULT_PAGE_SIZE = 1000
RETRY_COUNT = 3
WAIT_TIME_FOR_RETRY = 5
DEFAULT_RESULTS_LIMIT = 10000000
RATE_LIMIT_EXCEEDED_STATUS_CODE = 429
DEFAULT_REQUEST_TIMEOUT = 60
DEFAULT_OFFSET = "0"
DEFAULT_LIMIT = "100"
MAX_TABLE_RECORDS = 20
MAX_JSON_CHARS = 300
MAX_INT_VALUE = 65535

# Time formats
UNIX_FORMAT = "unix"
ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

# Scripts Name
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
DELETE_RESPONSE_POLICY_ZONE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Delete Response Policy Zone"
GET_RESPONSE_POLICY_ZONE_DETAILS_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Get Response Policy Zone Details"
)
CREATE_RESPONSE_POLICY_ZONE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create Response Policy Zone"
DELETE_RPZ_RULE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Delete RPZ Rule"
SEARCH_RPZ_RULE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Search RPZ Rule"
IP_LOOKUP_SCRIPT_NAME = f"{INTEGRATION_NAME} - IP Lookup"
LIST_NETWORK_INFO_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Network Info"
CREATE_RPZ_TXT_RULE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create RPZ TXT Rule"
DHCP_LEASE_LOOKUP_SCRIPT_NAME = f"{INTEGRATION_NAME} - DHCP Lease Lookup"
CREATE_RPZ_A_RULE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create RPZ A Rule"
CREATE_RPZ_AAAA_RULE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create RPZ AAAA Rule"
CREATE_RPZ_MX_RULE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create RPZ MX Rule"
CREATE_RPZ_PTR_RULE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create RPZ PTR Rule"
LIST_HOST_INFO_SCRIPT_NAME = f"{INTEGRATION_NAME} - List Host Info"
CREATE_RPZ_NAPTR_RULE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create RPZ NAPTR Rule"
CREATE_RPZ_SRV_RULE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create RPZ SRV Rule"
CREATE_RPZ_CNAME_RULE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create RPZ CNAME Rule"
UPDATE_RPZ_CNAME_RULE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Update RPZ CNAME Rule"
CREATE_HOST_RECORD_SCRIPT_NAME = f"{INTEGRATION_NAME} - Create Host Record"


# Action Identifiers
PING_ACTION_IDENTIFIER = "ping"
DELETE_RESPONSE_POLICY_ZONE_ACTION_IDENTIFIER = "delete_response_policy_zone"
GET_RESPONSE_POLICY_ZONE_DETAILS_ACTION_IDENTIFIER = "get_response_policy_zone_details"
CREATE_RESPONSE_POLICY_ZONE_ACTION_IDENTIFIER = "create_response_policy_zone"
DELETE_RPZ_RULE_ACTION_IDENTIFIER = "delete_rpz_rule"
SEARCH_RPZ_RULE_ACTION_IDENTIFIER = "search_rpz_rule"
IP_LOOKUP_ACTION_IDENTIFIER_V4 = "ip_lookup_v4"
IP_LOOKUP_ACTION_IDENTIFIER_V6 = "ip_lookup_v6"
LIST_NETWORK_INFO_ACTION_IDENTIFIER = "list_network_info"
CREATE_RPZ_TXT_RULE_ACTION_IDENTIFIER = "create_rpz_txt_rule"
DHCP_LEASE_LOOKUP_ACTION_IDENTIFIER = "dhcp_lease_lookup"
CREATE_RPZ_A_RULE_ACTION_IDENTIFIER_DOMAIN = "create_rpz_a_rule_domain"
CREATE_RPZ_A_RULE_ACTION_IDENTIFIER_IP = "create_rpz_a_rule_ip"
CREATE_RPZ_AAAA_RULE_ACTION_IDENTIFIER_DOMAIN = "create_rpz_aaaa_rule_domain"
CREATE_RPZ_AAAA_RULE_ACTION_IDENTIFIER_IP = "create_rpz_aaaa_rule_ip"
CREATE_RPZ_MX_RULE_ACTION_IDENTIFIER = "create_rpz_mx_rule"
CREATE_RPZ_PTR_RULE_ACTION_IDENTIFIER = "create_rpz_ptr_rule"
LIST_HOST_INFO_ACTION_IDENTIFIER = "list_host_info"
CREATE_RPZ_NAPTR_RULE_ACTION_IDENTIFIER = "create_rpz_naptr_rule"
CREATE_RPZ_SRV_RULE_ACTION_IDENTIFIER = "create_rpz_srv_rule"
CREATE_RPZ_CNAME_ACTION_IDENTIFIER = "create_rpz_cname_rule"
CREATE_RPZ_CNAME_ACTION_IDENTIFIER_IP = "create_rpz_cname_rule_ip"
CREATE_RPZ_CNAME_ACTION_IDENTIFIER_CLIENT_IP = "create_rpz_cname_rule_client_ip"
UPDATE_RPZ_CNAME_ACTION_IDENTIFIER = "update_rpz_cname_rule"
CREATE_HOST_RECORD_ACTION_IDENTIFIER = "create_host_record"

# API Services and Versions
API_VERSION_V2_13_1 = "/wapi/v2.13.1"
RECORD_RPZ = "/record:rpz:"

# API Endpoints
ENDPOINTS = {
    PING_ACTION_IDENTIFIER: f"{API_VERSION_V2_13_1}/?_schema",
    DELETE_RESPONSE_POLICY_ZONE_ACTION_IDENTIFIER: API_VERSION_V2_13_1 + "/{reference_id}",
    GET_RESPONSE_POLICY_ZONE_DETAILS_ACTION_IDENTIFIER: API_VERSION_V2_13_1 + "/zone_rp",
    CREATE_RESPONSE_POLICY_ZONE_ACTION_IDENTIFIER: API_VERSION_V2_13_1 + "/zone_rp",
    DELETE_RPZ_RULE_ACTION_IDENTIFIER: API_VERSION_V2_13_1 + "/{reference_id}",
    SEARCH_RPZ_RULE_ACTION_IDENTIFIER: API_VERSION_V2_13_1 + "/{object_type}",
    IP_LOOKUP_ACTION_IDENTIFIER_V4: API_VERSION_V2_13_1 + "/ipv4address",
    IP_LOOKUP_ACTION_IDENTIFIER_V6: API_VERSION_V2_13_1 + "/ipv6address",
    LIST_NETWORK_INFO_ACTION_IDENTIFIER: API_VERSION_V2_13_1 + "/network",
    CREATE_RPZ_TXT_RULE_ACTION_IDENTIFIER: API_VERSION_V2_13_1 + RECORD_RPZ + "txt",
    DHCP_LEASE_LOOKUP_ACTION_IDENTIFIER: API_VERSION_V2_13_1 + "/lease",
    CREATE_RPZ_A_RULE_ACTION_IDENTIFIER_DOMAIN: API_VERSION_V2_13_1 + RECORD_RPZ + "a",
    CREATE_RPZ_A_RULE_ACTION_IDENTIFIER_IP: API_VERSION_V2_13_1 + RECORD_RPZ + "a:ipaddress",
    CREATE_RPZ_AAAA_RULE_ACTION_IDENTIFIER_DOMAIN: API_VERSION_V2_13_1 + RECORD_RPZ + "aaaa",
    CREATE_RPZ_AAAA_RULE_ACTION_IDENTIFIER_IP: API_VERSION_V2_13_1 + RECORD_RPZ + "aaaa:ipaddress",
    CREATE_RPZ_MX_RULE_ACTION_IDENTIFIER: API_VERSION_V2_13_1 + RECORD_RPZ + "mx",
    CREATE_RPZ_PTR_RULE_ACTION_IDENTIFIER: API_VERSION_V2_13_1 + RECORD_RPZ + "ptr",
    LIST_HOST_INFO_ACTION_IDENTIFIER: API_VERSION_V2_13_1 + "/record:host",
    CREATE_RPZ_NAPTR_RULE_ACTION_IDENTIFIER: API_VERSION_V2_13_1 + RECORD_RPZ + "naptr",
    CREATE_RPZ_SRV_RULE_ACTION_IDENTIFIER: API_VERSION_V2_13_1 + RECORD_RPZ + "srv",
    CREATE_RPZ_CNAME_ACTION_IDENTIFIER: API_VERSION_V2_13_1 + "/record:rpz:cname",
    CREATE_RPZ_CNAME_ACTION_IDENTIFIER_IP: API_VERSION_V2_13_1 + "/record:rpz:cname:ipaddress",
    CREATE_RPZ_CNAME_ACTION_IDENTIFIER_CLIENT_IP: API_VERSION_V2_13_1
    + "/record:rpz:cname:clientipaddress",
    UPDATE_RPZ_CNAME_ACTION_IDENTIFIER: API_VERSION_V2_13_1 + "/{reference_id}",
    CREATE_HOST_RECORD_ACTION_IDENTIFIER: API_VERSION_V2_13_1 + "/record:host",
}

# Return Fields
DEFAULT_RPZ_RETURN_FIELDS = ["name", "view"]
IP_LOOKUP_COMMON_RETURN_FIELDS = [
    "objects",
    "conflict_types",
    "names",
    "ms_ad_user_data",
    "fingerprint",
    "network",
    "extattrs",
    "types",
    "reserved_port",
    "ip_address",
    "comment",
    "status",
    "usage",
    "discovered_data",
    "lease_state",
    "network_view",
    "discover_now_status",
    "is_conflict",
]
CREATE_RPZ_CNAME_RULE_RETURN_FIELDS = [
    "canonical",
    "comment",
    "disable",
    "extattrs",
    "name",
    "rp_zone",
    "ttl",
    "use_ttl",
    "view",
    "zone",
]
RESPONSE_POLICY_ZONE_RETURN_FIELDS = [
    "address",
    "comment",
    "disable",
    "display_domain",
    "dns_soa_email",
    "extattrs",
    "external_primaries",
    "external_secondaries",
    "fireeye_rule_mapping",
    "fqdn",
    "grid_primary",
    "grid_secondaries",
    "locked",
    "locked_by",
    "log_rpz",
    "mask_prefix",
    "member_soa_mnames",
    "member_soa_serials",
    "network_view",
    "ns_group",
    "parent",
    "prefix",
    "primary_type",
    "record_name_policy",
    "rpz_drop_ip_rule_enabled",
    "rpz_drop_ip_rule_min_prefix_length_ipv4",
    "rpz_drop_ip_rule_min_prefix_length_ipv6",
    "rpz_last_updated_time",
    "rpz_policy",
    "rpz_priority",
    "rpz_priority_end",
    "rpz_severity",
    "rpz_type",
    "soa_default_ttl",
    "soa_email",
    "soa_expire",
    "soa_negative_ttl",
    "soa_refresh",
    "soa_retry",
    "soa_serial_number",
    "substitute_name",
    "use_external_primary",
    "use_grid_zone_timer",
    "use_log_rpz",
    "use_record_name_policy",
    "use_rpz_drop_ip_rule",
]
CREATE_RPZ_RULE_COMMON_FIELDS = [
    "comment",
    "disable",
    "extattrs",
    "name",
    "rp_zone",
    "ttl",
    "use_ttl",
    "view",
    "zone",
]
CREATE_HOST_RECORD_RETURN_FIELDS = [
    "aliases",
    "allow_telnet",
    "cli_credentials",
    "cloud_info",
    "comment",
    "configure_for_dns",
    "creation_time",
    "ddns_protected",
    "device_description",
    "device_location",
    "device_type",
    "device_vendor",
    "disable",
    "disable_discovery",
    "dns_aliases",
    "dns_name",
    "extattrs",
    "ipv4addrs",
    "ipv6addrs",
    "last_queried",
    "ms_ad_user_data",
    "name",
    "network_view",
    "rrset_order",
    "snmp3_credential",
    "snmp_credential",
    "ttl",
    "use_cli_credentials",
    "use_dns_ea_inheritance",
    "use_snmp3_credential",
    "use_snmp_credential",
    "use_ttl",
    "view",
    "zone",
]
RETURN_FIELDS = {
    PING_ACTION_IDENTIFIER: [],
    IP_LOOKUP_ACTION_IDENTIFIER_V4: IP_LOOKUP_COMMON_RETURN_FIELDS
    + ["mac_address", "username", "dhcp_client_identifier", "is_invalid_mac"],
    IP_LOOKUP_ACTION_IDENTIFIER_V6: IP_LOOKUP_COMMON_RETURN_FIELDS + ["duid"],
    GET_RESPONSE_POLICY_ZONE_DETAILS_ACTION_IDENTIFIER: RESPONSE_POLICY_ZONE_RETURN_FIELDS,
    CREATE_RESPONSE_POLICY_ZONE_ACTION_IDENTIFIER: RESPONSE_POLICY_ZONE_RETURN_FIELDS,
    LIST_NETWORK_INFO_ACTION_IDENTIFIER: [
        "authority",
        "bootfile",
        "bootserver",
        "cloud_info",
        "comment",
        "conflict_count",
        "ddns_domainname",
        "ddns_generate_hostname",
        "ddns_server_always_updates",
        "ddns_ttl",
        "ddns_update_fixed_addresses",
        "ddns_use_option81",
        "deny_bootp",
        "dhcp_utilization",
        "dhcp_utilization_status",
        "disable",
        "discover_now_status",
        "discovered_bgp_as",
        "discovered_bridge_domain",
        "discovered_tenant",
        "discovered_vlan_id",
        "discovered_vlan_name",
        "discovered_vrf_description",
        "discovered_vrf_name",
        "discovered_vrf_rd",
        "discovery_basic_poll_settings",
        "discovery_blackout_setting",
        "discovery_engine_type",
        "discovery_member",
        "dynamic_hosts",
        "email_list",
        "enable_ddns",
        "enable_dhcp_thresholds",
        "enable_discovery",
        "enable_email_warnings",
        "enable_ifmap_publishing",
        "enable_pxe_lease_time",
        "enable_snmp_warnings",
        "endpoint_sources",
        "extattrs",
        "high_water_mark",
        "high_water_mark_reset",
        "ignore_dhcp_option_list_request",
        "ignore_id",
        "ignore_mac_addresses",
        "ipam_email_addresses",
        "ipam_threshold_settings",
        "ipam_trap_settings",
        "ipv4addr",
        "last_rir_registration_update_sent",
        "last_rir_registration_update_status",
        "lease_scavenge_time",
        "logic_filter_rules",
        "low_water_mark",
        "low_water_mark_reset",
        "members",
        "mgm_private",
        "mgm_private_overridable",
        "ms_ad_user_data",
        "netmask",
        "network",
        "network_container",
        "network_view",
        "nextserver",
        "options",
        "port_control_blackout_setting",
        "pxe_lease_time",
        "recycle_leases",
        "rir",
        "rir_organization",
        "rir_registration_status",
        "same_port_control_discovery_blackout",
        "static_hosts",
        "subscribe_settings",
        "total_hosts",
        "unmanaged",
        "unmanaged_count",
        "update_dns_on_lease_renewal",
        "use_authority",
        "use_blackout_setting",
        "use_bootfile",
        "use_bootserver",
        "use_ddns_domainname",
        "use_ddns_generate_hostname",
        "use_ddns_ttl",
        "use_ddns_update_fixed_addresses",
        "use_ddns_use_option81",
        "use_deny_bootp",
        "use_discovery_basic_polling_settings",
        "use_email_list",
        "use_enable_ddns",
        "use_enable_dhcp_thresholds",
        "use_enable_discovery",
        "use_enable_ifmap_publishing",
        "use_ignore_dhcp_option_list_request",
        "use_ignore_id",
        "use_ipam_email_addresses",
        "use_ipam_threshold_settings",
        "use_ipam_trap_settings",
        "use_lease_scavenge_time",
        "use_logic_filter_rules",
        "use_mgm_private",
        "use_nextserver",
        "use_options",
        "use_pxe_lease_time",
        "use_recycle_leases",
        "use_subscribe_settings",
        "use_update_dns_on_lease_renewal",
        "use_zone_associations",
        "utilization",
        "utilization_update",
        "zone_associations",
    ],
    CREATE_RPZ_TXT_RULE_ACTION_IDENTIFIER: CREATE_RPZ_RULE_COMMON_FIELDS + ["text"],
    DHCP_LEASE_LOOKUP_ACTION_IDENTIFIER: [
        "address",
        "billing_class",
        "binding_state",
        "client_hostname",
        "cltt",
        "discovered_data",
        "ends",
        "fingerprint",
        "hardware",
        "ipv6_duid",
        "ipv6_iaid",
        "ipv6_preferred_lifetime",
        "ipv6_prefix_bits",
        "is_invalid_mac",
        "ms_ad_user_data",
        "network",
        "network_view",
        "never_ends",
        "never_starts",
        "next_binding_state",
        "on_commit",
        "on_expiry",
        "on_release",
        "option",
        "protocol",
        "remote_id",
        "served_by",
        "server_host_name",
        "starts",
        "tsfp",
        "tstp",
        "uid",
        "username",
        "variable",
    ],
    CREATE_RPZ_A_RULE_ACTION_IDENTIFIER_DOMAIN: CREATE_RPZ_RULE_COMMON_FIELDS + ["ipv4addr"],
    CREATE_RPZ_A_RULE_ACTION_IDENTIFIER_IP: CREATE_RPZ_RULE_COMMON_FIELDS + ["ipv4addr"],
    CREATE_RPZ_AAAA_RULE_ACTION_IDENTIFIER_DOMAIN: CREATE_RPZ_RULE_COMMON_FIELDS + ["ipv6addr"],
    CREATE_RPZ_AAAA_RULE_ACTION_IDENTIFIER_IP: CREATE_RPZ_RULE_COMMON_FIELDS + ["ipv6addr"],
    CREATE_RPZ_MX_RULE_ACTION_IDENTIFIER: CREATE_RPZ_RULE_COMMON_FIELDS
    + ["mail_exchanger", "preference"],
    CREATE_RPZ_PTR_RULE_ACTION_IDENTIFIER: CREATE_RPZ_RULE_COMMON_FIELDS
    + ["ipv4addr", "ipv6addr", "ptrdname"],
    LIST_HOST_INFO_ACTION_IDENTIFIER: CREATE_HOST_RECORD_RETURN_FIELDS,
    CREATE_RPZ_NAPTR_RULE_ACTION_IDENTIFIER: [
        "comment",
        "disable",
        "extattrs",
        "flags",
        "last_queried",
        "name",
        "order",
        "preference",
        "regexp",
        "replacement",
        "rp_zone",
        "services",
        "ttl",
        "use_ttl",
        "view",
        "zone",
    ],
    CREATE_RPZ_SRV_RULE_ACTION_IDENTIFIER: [
        "comment",
        "disable",
        "extattrs",
        "name",
        "port",
        "priority",
        "rp_zone",
        "target",
        "ttl",
        "use_ttl",
        "view",
        "weight",
        "zone",
    ],
    CREATE_RPZ_CNAME_ACTION_IDENTIFIER: CREATE_RPZ_CNAME_RULE_RETURN_FIELDS,
    CREATE_RPZ_CNAME_ACTION_IDENTIFIER_IP: CREATE_RPZ_CNAME_RULE_RETURN_FIELDS + ["is_ipv4"],
    CREATE_RPZ_CNAME_ACTION_IDENTIFIER_CLIENT_IP: CREATE_RPZ_CNAME_RULE_RETURN_FIELDS + ["is_ipv4"],
    UPDATE_RPZ_CNAME_ACTION_IDENTIFIER: CREATE_RPZ_CNAME_RULE_RETURN_FIELDS,
    CREATE_HOST_RECORD_ACTION_IDENTIFIER: CREATE_HOST_RECORD_RETURN_FIELDS,
}
