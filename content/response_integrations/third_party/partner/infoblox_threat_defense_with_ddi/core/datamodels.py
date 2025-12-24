from __future__ import annotations
import json

from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from TIPCommon import dict_to_flat

from .constants import (
    DEFAULT_DEVICE_VENDOR,
    DEFAULT_DEVICE_PRODUCT,
    RULE_GENERATOR,
)
from .utils import truncate_json_for_display


class BaseModel(object):
    """
    Base model for all Infoblox datamodels.
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def get_severity(self, severity):
        """
        Convert severity text to Siemplify severity value.

        Returns:
            int: Siemplify severity value (40-100)
        """
        severity_map = {
            "LOW": 40,
            "INFO": 40,
            "MEDIUM": 60,
            "HIGH": 80,
            "CRITICAL": 100,
        }

        if not severity:
            return 40

        return severity_map.get(severity.upper(), 40)


class CustomList(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)
        self.id = raw_data.get("id")
        self.name = raw_data.get("name")
        self.description = raw_data.get("description")
        self.confidence_level = raw_data.get("confidence_level")
        self.threat_level = raw_data.get("threat_level")
        self.item_count = raw_data.get("item_count")

    def to_csv(self):
        return {
            "Custom List ID": self.id,
            "Name": self.name,
            "Description": self.description,
            "Confidence Level": self.confidence_level,
            "Threat Level": self.threat_level,
            "Item Count": self.item_count,
        }


class NetworkList(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)
        self.id = raw_data.get("id")
        self.name = raw_data.get("name")
        self.description = raw_data.get("description")
        self.item_approvals = raw_data.get("item_approvals", {})
        self.items = raw_data.get("items", [])
        self.policy_id = raw_data.get("policy_id")

    def to_csv(self):
        return {
            "Network List ID": self.id,
            "Name": self.name,
            "Description": self.description,
            "Security Policy ID": self.policy_id,
        }


class DNSRecord(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)
        self._id = raw_data.get("id")
        self.absolute_name_spec = raw_data.get("absolute_name_spec")
        self.name_in_zone = raw_data.get("name_in_zone")
        self._type = raw_data.get("type")
        self.ttl = raw_data.get("ttl")
        self.updated_at = raw_data.get("updated_at")
        self.disabled = raw_data.get("disabled")
        self.view_name = raw_data.get("view_name")

    def to_csv(self):
        return {
            "DNS ID": self._id,
            "Name In Zone": self.name_in_zone,
            "Absolute Name Spec": self.absolute_name_spec,
            "Type": self._type,
            "TTL": self.ttl,
            "Updated At": self.updated_at,
            "Disabled": self.disabled,
            "View Name": self.view_name,
        }


class IndicatorThreatLookupTideResult(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)
        self._type = raw_data.get("type")
        self.indicator = raw_data.get(self._type.lower())
        self.threat_level = raw_data.get("threat_level")
        self.threat_class = raw_data.get("class")
        self._property = raw_data.get("property")
        self.profile = raw_data.get("profile")
        self.detected = raw_data.get("detected")

    def to_csv(self):
        return {
            "Indicator": self.indicator,
            "Type": self._type,
            "Threat Level": self.threat_level,
            "Class": self.threat_class,
            "Property": self._property,
            "Profile": self.profile,
            "Detected": self.detected,
        }


class IndicatorIntelLookupResult(BaseModel):

    def __init__(self, raw_data):
        super().__init__(raw_data)
        self.source = raw_data.get("params", {}).get("source")
        self.status = raw_data.get("status")
        self.data = truncate_json_for_display(raw_data.get("data"))
        self.time = raw_data.get("time")
        self.version = raw_data.get("v")

    def to_csv(self):
        return {
            "Source": self.source,
            "Status": self.status,
            "Data": json.dumps(self.data) if self.data is not None else None,
            "Time": self.time,
            "Version": self.version,
        }


class IPLookup(BaseModel):

    def __init__(self, raw_data):
        super().__init__(raw_data)
        self._id = raw_data.get("id")
        self.address = raw_data.get("address")
        self.host_name = (
            raw_data.get("names", [{}])[0].get("name")
            if len(raw_data.get("names", [])) > 0
            else None
        )
        self.state = raw_data.get("state")
        self.usage = raw_data.get("usage")
        self.hwaddr = (
            raw_data.get("dhcp_info", {}).get("client_hwaddr")
            if raw_data.get("dhcp_info")
            else None
        )
        self.protocol = raw_data.get("protocol")
        self.updated_at = raw_data.get("updated_at")

    def to_csv(self):
        return {
            "ID": self._id,
            "Address": self.address,
            "Host Name": self.host_name,
            "State": self.state,
            "Usage": self.usage,
            "Hardware Address": self.hwaddr,
            "Protocol": self.protocol,
            "Updated Time": self.updated_at,
        }


class SOCInsightComment(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)
        self.comment_changer = raw_data.get("commentsChanger")
        self.date_changed = raw_data.get("dateChanged")
        self.new_comment = raw_data.get("newComment")
        self.status = raw_data.get("status")

    def to_csv(self):
        return {
            "Comment Changer": self.comment_changer,
            "Date Changed": self.date_changed,
            "New Comment": self.new_comment,
            "Status": self.status,
        }


class SOCInsightIndicator(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)
        self.action = raw_data.get("action")
        self.confidence = raw_data.get("confidence")
        self.count = raw_data.get("count")
        self.feed_name = raw_data.get(
            "feedName",
        )
        self.threat_level_max = raw_data.get("threatLevelMax")
        self.indicator = raw_data.get("indicator")
        self.actor = raw_data.get("actor")

    def to_csv(self):
        return {
            "Action": self.action,
            "Confidence": self.confidence,
            "Count": self.count,
            "Feed Name": self.feed_name,
            "Threat Level Max": self.threat_level_max,
            "Indicator": self.indicator,
            "Actor": self.actor,
        }


class SOCInsightEvent(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)
        self.confidence_level = raw_data.get("confidenceLevel")
        self.device_name = raw_data.get("deviceName")
        self.device_ip = raw_data.get("deviceIp")
        self.action = raw_data.get("action")
        self.policy = raw_data.get("policy")
        self.threat_family = raw_data.get("threatFamily")
        self.threat_level = raw_data.get("threatLevel")

    def to_csv(self):
        return {
            "Confidence Level": self.confidence_level,
            "Device Name": self.device_name,
            "Device IP": self.device_ip,
            "Action": self.action,
            "Policy": self.policy,
            "Threat Family": self.threat_family,
            "Threat Level": self.threat_level,
        }


class DossierWaitResult(IndicatorIntelLookupResult):
    def __init__(self, raw_data):
        super().__init__(raw_data)


class DossierJobResult(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)
        self.job_id = raw_data.get("job_id")
        self.status = raw_data.get("status")

    def to_csv(self):
        return {
            "Job ID": self.job_id,
            "Status": self.status,
        }


class SecurityPolicy(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)
        self.id = raw_data.get("id", "")
        self.name = raw_data.get("name", "")
        self.description = raw_data.get("description", "")
        self.default_action = raw_data.get("default_action", "")

    def to_csv(self):
        return {
            "Security Policy ID": self.id,
            "Policy Name": self.name,
            "Description": self.description,
            "Default Action": self.default_action,
        }


class DHCPLease(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)
        self.address = raw_data.get("address")
        self.hostname = raw_data.get("hostname")
        self.hardware = raw_data.get("hardware")
        self.state = raw_data.get("state")
        self._type = raw_data.get("type")
        self.starts = raw_data.get("starts")
        self.ends = raw_data.get("ends")
        self.fingerprint = raw_data.get("fingerprint")
        self.last_updated = raw_data.get("last_updated")

    def to_csv(self):
        return {
            "Address": self.address,
            "Hostname": self.hostname,
            "Hardware": self.hardware,
            "State": self.state,
            "Type": self._type,
            "Starts": self.starts,
            "Ends": self.ends,
            "Fingerprint": self.fingerprint,
            "Last Updated": self.last_updated,
        }


class SOCInsightAsset(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)
        self.asset_ip = raw_data.get("qip")
        self.mac_address = raw_data.get("cmac")
        self.threat_level = raw_data.get("threatLevelMax")
        self.os_version = raw_data.get("osVersion")
        self.user = raw_data.get("user")

    def to_csv(self):
        return {
            "Asset IP": self.asset_ip,
            "MAC Address": self.mac_address,
            "Threat Level": self.threat_level,
            "OS Version": self.os_version,
            "User": self.user,
        }


class Host(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)
        self._id = raw_data.get("id")
        self.name = raw_data.get("name")
        self.ip_address = (
            raw_data.get("addresses", [{}])[0].get("address")
            if raw_data.get("addresses") and len(raw_data["addresses"]) > 0
            else None
        )
        self.space = (
            raw_data.get("addresses", [{}])[0].get("space")
            if raw_data.get("addresses") and len(raw_data["addresses"]) > 0
            else None
        )
        self.comment = raw_data.get("comment")
        self.created_at = raw_data.get("created_at")
        self.updated_at = raw_data.get("updated_at")
        self.tags = raw_data.get("tags")

    def to_csv(self):
        return {
            "ID": self._id,
            "Name": self.name,
            "IP Address": self.ip_address,
            "Space": self.space,
            "Comment": self.comment,
            "Created At": self.created_at,
            "Updated At": self.updated_at,
            "Tags": self.tags,
        }


class DNSSecurityEvent(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)
        # Extract fields from raw data
        self.event_time = raw_data.get("event_time")
        self.device = raw_data.get("device")
        self.network = raw_data.get("network")
        self.qname = raw_data.get("qname")
        self.qtype = raw_data.get("qtype")
        self.rdata = raw_data.get("rdata")
        self.severity = raw_data.get("severity")
        self.tclass = raw_data.get("tclass")
        self.tfamily = raw_data.get("tfamily")
        self.threat_indicator = raw_data.get("threat_indicator")
        self.feed_name = raw_data.get("feed_name")
        self.feed_type = raw_data.get("feed_type")
        self.policy_action = raw_data.get("policy_action")
        self.policy_name = raw_data.get("policy_name")
        self.qip = raw_data.get("qip")
        self.rip = raw_data.get("rip")
        self.rcode = raw_data.get("rcode")
        self.dns_view = raw_data.get("dns_view")
        self.confidence = raw_data.get("confidence")
        self.user = raw_data.get("user")

        # Generate a deterministic ID for the event
        self.event_id = self._generate_id()

    def _generate_id(self):
        """
        Create a deterministic ID by combining multiple event fields.

        Returns:
            str: Unique identifier generated from event data
        """
        # Truncate qname to 20 characters if needed
        qname_truncated = self.qname[:20] if self.qname else ""

        # Create a composite key with fields separated by '|'
        key_parts = [
            self.event_time,
            qname_truncated,
            self.device,
            self.feed_name,
        ]
        composite_key = "|".join([str(part) for part in key_parts if part])

        return composite_key

    def get_alert_info(
        self, alert_info, environment_common, device_product_field
    ):
        """
        Converts DNSSecurityEvent to AlertInfo object

        Args:
            alert_info (AlertInfo): AlertInfo object to populate
            environment_common (EnvironmentCommon): Environment manager for determining environment
            device_product_field (str): Field name to use for device product

        Returns:
            AlertInfo: Populated AlertInfo object
        """

        alert_info.environment = environment_common.get_environment(
            self.raw_data
        )
        alert_info.display_id = self.event_id
        alert_info.ticket_id = self.event_id
        alert_info.name = (
            f"{self.tclass} - {self.qname}"
            if self.tclass and self.qname
            else "Infoblox DNS Security Event"
        )
        alert_info.description = (
            f"Threat Class: {self.tclass}, Threat Family: {self.tfamily}, "
            f"Feed: {self.feed_name}, Policy: {self.policy_name}"
        )
        alert_info.device_vendor = DEFAULT_DEVICE_VENDOR
        alert_info.device_product = (
            self.raw_data.get(device_product_field) or DEFAULT_DEVICE_PRODUCT
        )
        alert_info.rule_generator = f"{RULE_GENERATOR}: DNS - {alert_info.name}"
        alert_info.source_grouping_identifier = self.event_id
        alert_info.start_time = convert_string_to_unix_time(self.event_time)
        alert_info.end_time = convert_string_to_unix_time(self.event_time)
        alert_info.priority = self.get_severity(self.severity)

        # Add all event data as extensions
        alert_info.extensions = dict_to_flat(self.raw_data)

        # Add events
        alert_info.events = [dict_to_flat(self.raw_data)]

        return alert_info


class SOCInsight(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)
        self.insight_id = raw_data.get("insightId")
        self.t_class = raw_data.get("tClass")
        self.t_family = raw_data.get("tFamily")
        self.feed_source = raw_data.get("feedSource")
        self.started_at = raw_data.get("startedAt")
        self.threat_type = raw_data.get("threatType")
        self.status = raw_data.get("status")
        self.persistent_date = raw_data.get("persistentDate")
        self.spreading_date = raw_data.get("spreadingDate")
        self.num_events = raw_data.get("numEvents")
        self.most_recent_at = raw_data.get("mostRecentAt")
        self.events_blocked_count = raw_data.get("eventsBlockedCount")
        self.date_changed = raw_data.get("dateChanged")
        self.priority_text = raw_data.get("priorityText")
        self.event_id = self.insight_id

    def get_alert_info(
        self, alert_info, environment_common, device_product_field
    ):
        """
        Converts SOCInsight to AlertInfo object

        Args:
            alert_info (AlertInfo): AlertInfo object to populate
            environment_common (EnvironmentCommon): Environment manager for determining environment

        Returns:
            AlertInfo: Populated AlertInfo object
        """

        alert_info.environment = environment_common.get_environment(
            self.raw_data
        )
        alert_info.display_id = self.event_id
        alert_info.ticket_id = self.event_id
        alert_info.name = (
            f"{self.threat_type} - {self.t_family}"
            if self.threat_type and self.t_family
            else "Infoblox SOC Insight"
        )
        alert_info.description = (
            f"Threat Class: {self.t_class}, Family: {self.t_family}, "
            f"Feed Source: {self.feed_source}"
        )
        alert_info.device_vendor = DEFAULT_DEVICE_VENDOR
        alert_info.device_product = (
            self.raw_data.get(device_product_field) or DEFAULT_DEVICE_PRODUCT
        )
        alert_info.rule_generator = (
            f"{RULE_GENERATOR}: Insight - {alert_info.name}"
        )
        alert_info.source_grouping_identifier = self.insight_id
        alert_info.start_time = convert_string_to_unix_time(self.started_at)
        alert_info.end_time = convert_string_to_unix_time(self.most_recent_at)
        alert_info.priority = self.get_severity(self.priority_text)

        # Add all insight data as additional data
        alert_info.extensions = dict_to_flat(self.raw_data)

        # Add events
        alert_info.events = [dict_to_flat(self.raw_data)]

        return alert_info
