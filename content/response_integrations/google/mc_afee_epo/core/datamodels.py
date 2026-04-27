from __future__ import annotations
import json
import uuid
from hashlib import sha1

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from TIPCommon import dict_to_flat, add_prefix_to_dict
from .constants import (
    MCAFEE_EPO_PROVIDER_PREFIX,
    MCAFEE_ePO_PROVIDER_PREFIX,
    DEVICE_VENDOR,
    PRODUCT_NAME,
    SEVERITY_TO_PRIORITY_MAPPING,
)
from .utils import (
    dotted_field_to_underscored,
    ipv4_str,
    SeverityLevelMappingEnum,
    ipv4_mapped_from_ipv6,
)

AGENT_PROPERTIES_KEY_PREFIX = "EPOLeafNode."
TASK_SUCCESS_STATUSES = ["Succeeded"]


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_table(self):
        return [self.to_csv()]

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self):
        pass

    def to_flat(self):
        return dict_to_flat(self.to_json())

    @staticmethod
    def convert_list_to_comma_string(value_list):
        return (
            ", ".join(value_list)
            if value_list and isinstance(value_list, list)
            else value_list
        )

    def is_empty(self):
        return not bool(self.raw_data)


class SystemInformation(BaseModel):
    def __init__(
        self,
        raw_data,
        agent_guid=None,
        cpu_speed=None,
        cpu_type=None,
        default_lang_id=None,
        description=None,
        domain_name=None,
        email_address=None,
        ethernet_mac_address_count=None,
        free_space_of_drive_c=None,
        free_disk_space=None,
        free_memory=None,
        ip_address=None,
        ip_host_name=None,
        ipv4x=None,
        ipv6=None,
        ipx_address=None,
        is_portable=None,
        last_agent_handler=None,
        last_update=None,
        management_type=None,
        net_address=None,
        node_text_path2=None,
        num_of_cpu=None,
        num_of_hard_drives=None,
        os_bit_mode=None,
        os_build_num=None,
        os_csd_version=None,
        os_platform=None,
        os_type=None,
        osoemid=None,
        other_mac_address_count=None,
        platform_id=None,
        sm_bios_uuid=None,
        subnet_address=None,
        subnet_mask=None,
        system_boot_time=None,
        system_manufacturer=None,
        system_model=None,
        system_reboot_pending=None,
        system_serial_number=None,
        tags=None,
        time_zone=None,
        total_space_of_drive_c=None,
        total_physical_memory=None,
        user_name=None,
        user_property1=None,
        user_property2=None,
        user_property3=None,
        user_property4=None,
        user_property5=None,
        user_property6=None,
        user_property7=None,
        user_property8=None,
        vdi=None,
        wireless_mac_address_count=None,
        computer_name=None,
        agent_version=None,
        parent_id=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.agent_guid = agent_guid
        self.cpu_speed = cpu_speed
        self.cpu_type = cpu_type
        self.default_lang_id = default_lang_id
        self.description = description
        self.domain_name = domain_name
        self.email_address = email_address
        self.ethernet_mac_address_count = ethernet_mac_address_count
        self.free_space_of_drive_c = free_space_of_drive_c
        self.free_disk_space = free_disk_space
        self.free_memory = free_memory
        self.ip_address = ip_address
        self.ip_host_name = ip_host_name
        self.ipv4x = ipv4x
        self.ipv6 = ipv6
        self.ipx_address = ipx_address
        self.is_portable = is_portable
        self.last_agent_handler = last_agent_handler
        self.last_update = last_update
        self.management_type = management_type
        self.net_address = net_address
        self.node_text_path2 = node_text_path2
        self.num_of_cpu = num_of_cpu
        self.num_of_hard_drives = num_of_hard_drives
        self.os_bit_mode = os_bit_mode
        self.os_build_num = os_build_num
        self.os_csd_version = os_csd_version
        self.os_platform = os_platform
        self.os_type = os_type
        self.osoemid = osoemid
        self.other_mac_address_count = other_mac_address_count
        self.platform_id = platform_id
        self.sm_bios_uuid = sm_bios_uuid
        self.subnet_address = subnet_address
        self.subnet_mask = subnet_mask
        self.system_boot_time = system_boot_time
        self.system_manufacturer = system_manufacturer
        self.system_model = system_model
        self.system_reboot_pending = system_reboot_pending
        self.system_serial_number = system_serial_number
        self.tags = tags
        self.time_zone = time_zone
        self.total_space_of_drive_c = total_space_of_drive_c
        self.total_physical_memory = total_physical_memory
        self.user_name = user_name
        self.user_property1 = user_property1
        self.user_property2 = user_property2
        self.user_property3 = user_property3
        self.user_property4 = user_property4
        self.user_property5 = user_property5
        self.user_property6 = user_property6
        self.user_property7 = user_property7
        self.user_property8 = user_property8
        self.vdi = vdi
        self.wireless_mac_address_count = wireless_mac_address_count
        self.computer_name = computer_name
        self.parent_id = parent_id[-1] if isinstance(parent_id, tuple) else parent_id
        self.agent_version = (agent_version,)
        self.entity_identifier = None

    def to_json(self):
        return {key.replace(".", "_"): value for key, value in self.raw_data.items()}

    def to_enrichment_data(self):
        enrichment_data = self._get_enrichment_data()
        return {key.replace(" ", "_"): value for key, value in enrichment_data.items()}

    def _get_enrichment_data(self):
        return {
            # Because no info about system location in API request
            "System Location": None,
            "Time Zone": self.time_zone,
            "Default Language": self.default_lang_id,
            "User Name": self.user_name,
            "Domain Name": self.domain_name,
            "DNS Name": self.ip_host_name,
            "IPV6": self.ipv6,
            "IP Address": self.ip_address,
            "Subnet Address": self.subnet_address,
            "Subnet Mask": self.subnet_mask,
            "IP4 Address": self.ipv4x,
            "IPX Address": self.ipx_address,
            "MAC Address": self.net_address,
            "OS Type": self.os_type,
            "OS Service Pack V": self.os_csd_version,
            "OS Build Number": self.os_build_num,
            "OS Platform": self.os_platform,
            "OS OEM Identifier": self.osoemid,
            "CPU Type": self.cpu_type,
            "CPU Speed": self.cpu_speed,
            "Management Type": self.management_type,
            "Number of CPUs": self.num_of_cpu,
            "Total Physical Memory": self.total_physical_memory,
            "Free Memory": self.free_memory,
            "Free Disk Space": self.free_disk_space,
            "Is Laptop": self.is_portable,
            "Is 64 bit OS": self.os_bit_mode,
            "Agent Handler": self.last_agent_handler,
            "Custom1": self.user_property1,
            "Custom2": self.user_property2,
            "Custom3": self.user_property3,
            "Custom4": self.user_property4,
            "Custom5": self.user_property5,
            "Custom6": self.user_property6,
            "Custom7": self.user_property7,
            "Custom8": self.user_property8,
            "Free C Drive space": self.free_space_of_drive_c,
            "Total C Drive space": self.total_space_of_drive_c,
            "VDI": self.vdi,
            "Email Address": self.email_address,
            "Last Communication": self.last_update,
            "Platform ID": self.platform_id,
            "SM Bios UUID": self.sm_bios_uuid,
            "System Serial Number": self.system_serial_number,
            "Reboot Pending": self.system_reboot_pending,
            "System Model": self.system_model,
            "System Manufacturer": self.system_manufacturer,
            "Last System Boot Time": self.system_boot_time,
            "Number of Hard Drives": self.num_of_hard_drives,
            "Number of Ethernet MAC Address": self.ethernet_mac_address_count,
            "Number of Wireless MAC Address": self.wireless_mac_address_count,
            "Number of Other MAC Address": self.other_mac_address_count,
            "Agent GUID": self.agent_guid,
            "Description": self.description,
            "Tags": self.tags,
            "Assignment Path": self.node_text_path2,
        }

    def to_csv(self):
        return {
            "Endpoint": self.entity_identifier,
            "DNS Name": self.ip_host_name,
            "IP Address": self.ip_address,
            "Username": self.user_name,
            "Last Communication": self.last_update,
            "OS Type": self.os_type,
            "OS Platform": self.os_platform,
            "Domain Name": self.domain_name,
            "Email Address": self.email_address,
        }

    def to_insight(self):
        content = "<table><tbody><tr>"
        for key, value in self.to_csv().items():
            content += f"<td><strong>{key}:</strong></td><td>&nbsp;<strong>{value}</strong></td></tr>"
        content += "</tbody></table>"
        content += "<p>&nbsp;</p>"

        return content

    def to_agent_info_json(self):
        return {
            key.split(AGENT_PROPERTIES_KEY_PREFIX)[1]: str(value)
            for key, value in self.raw_data.items()
            if AGENT_PROPERTIES_KEY_PREFIX in key
        }

    def to_agent_enrichment_data(self):
        return add_prefix_to_dict(self.to_agent_info_json(), MCAFEE_EPO_PROVIDER_PREFIX)

    def to_agent_version_json(self):
        return add_prefix_to_dict(
            {"agent_version": self.agent_version[0]}, MCAFEE_ePO_PROVIDER_PREFIX
        )


class MachineGUID(BaseModel):
    def __init__(self, raw_data, agent_guid=None):
        super().__init__(raw_data)
        self.agent_guid = agent_guid

    def to_json(self):
        return {"agent_guid": self.agent_guid}


class Group(BaseModel):
    def __init__(self, raw_data, group_id=None, group_path=None):
        super().__init__(raw_data)
        self.group_id = group_id
        self.group_path = group_path
        self.group_name = self.get_name()

    def get_name(self):
        path = self.group_path.split("\\")
        return path[-1] if len(path) > 1 else ""


class HipProperty(BaseModel):
    def __init__(self, raw_data, hips_status):
        super().__init__(raw_data)
        self.status = hips_status

    def to_csv(self, entity_identifier=None, status_key=None):
        return {"Host": entity_identifier, status_key: self.status}

    def to_json(self, status_key=None):
        return {status_key: self.status}


class LastCommunicationTime(BaseModel):
    def __init__(self, raw_data, last_update=None):
        super().__init__(raw_data)
        self.last_update = last_update

    def to_json(self):
        return {"last_communication_time": self.last_update}

    def to_csv(self, entity_identifier=None):
        return dict_to_flat(
            {"Host": entity_identifier, "Last Communication Time": self.last_update}
        )


class DatVersion(BaseModel):
    def __init__(self, raw_data, datver):
        super().__init__(raw_data)
        self.dat_version = datver[-1] if isinstance(datver, tuple) else datver

    def to_json(self):
        return {"DAT_version": self.dat_version}

    def to_csv(self, entity_identifier=None):
        return {"host": entity_identifier, "version": self.dat_version}


class Task(BaseModel):
    def __init__(
        self,
        raw_data,
        *,
        product_id=None,
        type_name=None,
        object_name=None,
        prevention=None,
        object_id=None,
        product_name=None,
        type_id=None,
    ):
        super().__init__(raw_data)
        self.product_id = product_id
        self.type_name = type_name
        self.type_id = type_id
        self.object_name = object_name
        self.prevention = prevention
        self.object_id = object_id
        self.product_name = product_name

    def to_csv(self):
        return {
            "ID": self.object_id,
            "Name": self.object_name,
            "Product ID": self.product_id,
            "Type": self.type_name,
        }


class TaskStatus(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)
        self.status = raw_data

    @property
    def is_success(self):
        return self.status in TASK_SUCCESS_STATUSES

    def to_json(self):
        return {"status": "success" if self.is_success else "failure"}


class ServerDat(BaseModel):
    def __init__(self, raw_data, product_version):
        super().__init__(raw_data)
        self.server_version = (
            product_version[-1]
            if isinstance(product_version, tuple)
            else product_version
        )

    def to_csv(self):
        return {"host": "Server", "version": self.server_version}


class VirusScanVersion(BaseModel):
    def __init__(self, raw_data, productversion=None):
        super().__init__(raw_data)
        self.product_version = productversion

    def to_json(self):
        return {"Virus_Engine_Agent_version": self.product_version}


class CustomQuery(BaseModel):
    def __init__(self, raw_data, **kwargs):
        super().__init__(raw_data)

    def to_json(self):
        return {k.replace(".", "_"): v for k, v in super().to_json().items()}

    def to_csv(self):
        return {k.split("_")[-1]: v for k, v in self.to_flat().items()}


class EPOEvent(BaseModel):
    def __init__(self, raw_data, md5=None, **kwargs):
        super().__init__(raw_data)
        self.md5_hash = md5
        self.visible_json_fields = None

    def to_csv(self):
        return {k.split("_")[-1]: v for k, v in self.to_flat().items()}

    def to_json(self):
        raw_data = {k.replace(".", "_"): v for k, v in super().to_json().items()}
        return (
            {k: v for k, v in raw_data.items() if k in self.visible_json_fields}
            if self.visible_json_fields
            else raw_data
        )


class EPExtendedEvent(EPOEvent):
    def __init__(self, raw_data, target_hash=None, **kwargs):
        super().__init__(raw_data, md5=target_hash, **kwargs)


class EPEEntityEvent(EPOEvent):
    def __init__(self, raw_data, **kwargs):
        super().__init__(raw_data, **kwargs)

    def __getitem__(self, *args, **kwargs):
        return self.raw_data.get(*args, **kwargs)


class QueryResult(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)

    def to_underscored_json(self):
        return {dotted_field_to_underscored(k): v for k, v in self.to_json().items()}

    def to_underscored_csv(self):
        return self.to_underscored_json()


class Query(BaseModel):
    def __init__(self, raw_data, *, query_id=None, name=None, description=None):
        super().__init__(raw_data)
        self.query_id = query_id
        self.name = name
        self.description = description

    def __getitem__(self, *args, **kwargs):
        self.raw_data.get(*args, **kwargs)

    def values(self):
        return self.raw_data.values()

    def to_csv(self):
        return {"ID": self.query_id, "Name": self.name, "Description": self.description}


class EPEndpointEvent(EPOEvent):
    def __init__(
        self,
        raw_data,
        target_ipv4=None,
        target_host_name=None,
        target_mac=None,
        **kwargs,
    ):
        super().__init__(raw_data, **kwargs)
        self.target_mac = target_mac
        self.target_ipv4 = target_ipv4
        self.target_host_name = target_host_name


class Threat(EPOEvent):
    def __init__(
        self,
        raw_data,
        threat_name=None,
        threat_severity=None,
        analyzer_name=None,
        received_utc=None,
        **kwargs,
    ):
        super().__init__(raw_data, **kwargs)
        self.hash_id = str(self.sha1_hash_of_event)
        self.threat_name = threat_name
        self.threat_severity = int(threat_severity) if threat_severity else None
        self.analyzer_name = analyzer_name
        self.received_utc = received_utc
        self.timestamp = convert_string_to_unix_time(self.received_utc)

    @property
    def sha1_hash_of_event(self):
        event_json = json.dumps(self.as_event(), sort_keys=True).encode()
        return sha1(event_json).hexdigest()

    @property
    def case_priority(self):
        map_name = SeverityLevelMappingEnum.get_level_name_by_value(
            self.threat_severity
        )
        return SEVERITY_TO_PRIORITY_MAPPING.get(map_name, -1)

    def as_event(self):
        event_json = self.to_flat()
        ip_v4_keys_to_convert = [
            "EPOEvents_TargetIPV4",
            "EPOEvents_AnalyzerIPV4",
            "EPOEvents_SourceIPV4",
        ]
        event_json.update(
            {
                ip_key: ipv4_str(event_json.get(ip_key))
                for ip_key in ip_v4_keys_to_convert
            }
        )

        converted_src_ip = ipv4_mapped_from_ipv6(event_json.get("EPOEvents_SourceIPV6"))
        converted_dst_ip = ipv4_mapped_from_ipv6(event_json.get("EPOEvents_TargetIPV6"))

        if converted_src_ip:
            event_json.update({"converted_src_ip": converted_src_ip})

        if converted_dst_ip:
            event_json.update({"converted_dst_ip": converted_dst_ip})

        return event_json

    def get_alert_info(self, environment_common, device_product_field):
        """
        Get alert info from an insight
        :param environment_common: {EnvironmentHandle} object instance
        :param device_product_field: {str} key to map device_product
        :return: {AlertInfo} Alert Info data model
        """
        event_json = self.as_event()
        alert_info = AlertInfo()
        alert_info.environment = environment_common.get_environment(self.as_event())
        alert_info.ticket_id = self.sha1_hash_of_event
        alert_info.display_id = str(uuid.uuid4())
        alert_info.name = f"Incident: {self.threat_name}"
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            event_json.get(dotted_field_to_underscored(device_product_field))
            or PRODUCT_NAME
        )
        alert_info.priority = self.case_priority
        alert_info.rule_generator = self.analyzer_name
        alert_info.end_time = alert_info.start_time = int(self.timestamp)
        alert_info.events = [event_json]

        return alert_info
