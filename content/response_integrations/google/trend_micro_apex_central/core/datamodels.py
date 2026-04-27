from __future__ import annotations
import copy

from TIPCommon import dict_to_flat, add_prefix_to_dict

from .consts import (
    ENRICHMENT_PREFIX,
    NOT_ASSIGNED,
    ENDPOINTS_INSIGHT_TEMPLATE,
    UDSO_INSIGHT_TEMPLATE,
)


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class UDSOEntry(BaseModel):
    """
    User Defined Suspicious object entry data model
    """

    def __init__(
        self,
        raw_data,
        type=None,
        content=None,
        notes=None,
        scan_action=None,
        expiration_utc_date=None,
    ):
        super(UDSOEntry, self).__init__(raw_data)
        self.type = type
        self.content = content or ""
        self.notes = notes
        self.scan_action = scan_action
        self.expiration_utc_date = expiration_utc_date

    def to_csv(self):
        return {"Entity": self.content, "Note": self.notes, "Action": self.scan_action}

    def to_enrichment_data(self, prefix=ENRICHMENT_PREFIX):
        enrichment_table = {
            "type": self.type,
            "note": self.notes,
            "action": self.scan_action,
            "expiration": self.expiration_utc_date,
        }
        return add_prefix_to_dict(dict_to_flat(enrichment_table), prefix)

    def to_insight(self):
        return UDSO_INSIGHT_TEMPLATE.format(
            entity_identifier=self.content,
            scan_action=self.scan_action if self.scan_action else NOT_ASSIGNED,
            notes=self.notes if self.notes else NOT_ASSIGNED,
        )


class SecurityAgent(BaseModel):
    """
    Security Agent data model
    """

    def __init__(
        self,
        raw_data,
        entity_id=None,
        product=None,
        managing_server_id=None,
        ad_domain=None,
        folder_path=None,
        ip_address_list=None,
        mac_address_list=None,
        host_name=None,
        isolation_status=None,
    ):
        super(SecurityAgent, self).__init__(raw_data)
        self.entity_id = entity_id
        self.product = product
        self.managing_server_id = managing_server_id
        self.ad_domain = ad_domain
        self.folder_path = folder_path
        self.ip_address_list = ip_address_list
        self.mac_address_list = mac_address_list
        self.host_name = host_name
        self.isolation_status = isolation_status
        self.has_endpoint_sensor = None

    def set_if_has_endpoint_sensor(self, is_endpoint_sensor_enabled):
        self.has_endpoint_sensor = bool(is_endpoint_sensor_enabled)

    def to_enrichment_data(self, prefix=ENRICHMENT_PREFIX):
        enrichment_table = {
            "ip_address": self.ip_address_list,
            "mac_address": self.mac_address_list,
            "hostname": self.host_name,
            "isolation_status": self.isolation_status,
            "ad_domain": self.ad_domain,
        }
        if self.has_endpoint_sensor is not None:
            enrichment_table["has_endpoint_sensor"] = self.has_endpoint_sensor
        return add_prefix_to_dict(dict_to_flat(enrichment_table), prefix)

    def to_csv(self):
        csv_table = {
            "IP Address": self.ip_address_list,
            "MAC Address": self.mac_address_list,
            "Hostname": self.host_name,
            "Isolation Status": self.isolation_status,
        }
        if self.has_endpoint_sensor is not None:
            csv_table["Has Endpoint Sensor"] = self.has_endpoint_sensor
        return csv_table

    def to_insight(self, identifier):
        return ENDPOINTS_INSIGHT_TEMPLATE.format(
            endpoint_identifier=identifier,
            ip_address=self.ip_address_list if self.ip_address_list else NOT_ASSIGNED,
            mac_address=(
                self.mac_address_list if self.mac_address_list else NOT_ASSIGNED
            ),
            host_name=self.host_name if self.host_name else NOT_ASSIGNED,
            isolation_status=(
                self.isolation_status
                if self.isolation_status is not None
                else NOT_ASSIGNED
            ),
            ad_domain=self.ad_domain if self.ad_domain else NOT_ASSIGNED,
            has_endpoint_sensor=(
                "Available" if bool(self.has_endpoint_sensor) else NOT_ASSIGNED
            ),
        )

    def to_json(self):
        json_data = copy.deepcopy(self.raw_data)
        if self.has_endpoint_sensor is not None:
            json_data["has_endpoint_sensor"] = self.has_endpoint_sensor
        return json_data


class EnabledEndpointSecurityAgent(BaseModel):
    """
    Enabled Security Agent data model
    """

    def __init__(
        self,
        raw_data,
        agent_guid=None,
        server_guid=None,
        machine_name=None,
        is_important=None,
        is_online=None,
        ip=None,
        machine_guid=None,
        machine_type=None,
        machine_os=None,
        isolation_status=None,
        is_enabled=None,
        username=None,
        user_guid=None,
        product_type=None,
    ):
        super(EnabledEndpointSecurityAgent, self).__init__(raw_data)
        self.agent_guid = agent_guid
        self.server_guid = server_guid
        self.machine_name = machine_name
        self.is_important = is_important
        self.is_online = is_online
        self.ip = ip
        self.machine_guid = machine_guid
        self.machine_type = machine_type
        self.machine_os = machine_os
        self.isolation_status = isolation_status
        self.is_enabled = is_enabled
        self.username = username
        self.user_guid = user_guid
        self.product_type = product_type
