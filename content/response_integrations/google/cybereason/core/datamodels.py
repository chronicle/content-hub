from __future__ import annotations

import uuid
import copy
from TIPCommon import dict_to_flat, flat_dict_to_csv
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from .utils import convert_list_to_comma_string, milliseconds_to_human_time
from .constants import SUSPICIOUS_TYPES, BLOCK_ACTION_LIST


DEVICE_VENDOR = "Cybereason"
DEVICE_PRODUCT = "Cybereason"

MACHINES_KEY = "machines"
USERS_KEY = "users"
ENTITY_KEY = "entity"

EVENT_PROPERTIES_FROM_SINGLE_MALOP = [
    "affected_machines",
    "affected_users",
    "file_suspects",
    "process_suspects",
    "connections",
    "timeline_events",
]

CYBEREASON_TO_SIEM_SEVERITY = {"Low": 40, "Medium": 60, "High": 80}


class QueryResultObject:
    def __init__(self, raw_data, constructed_data=None):
        self.raw_data = raw_data
        self.constructed_data = constructed_data

    def to_json(self):
        return self.constructed_data

    def as_json(self):
        return self.raw_data


class Malop(QueryResultObject):
    def __init__(
        self,
        raw_data,
        element_name=None,
        detection_type=None,
        malop_activity_types=None,
        affected_machines=None,
        affected_users=None,
        root_cause_elements_length=None,
        file_suspects=None,
        process_suspects=None,
        connections=None,
        timeline_events=None,
        updating_time=None,
    ):
        super().__init__(raw_data)
        self.element_name = element_name
        self.detection_type = detection_type
        self.malop_activity_types = malop_activity_types
        self.affected_machines = affected_machines
        self.affected_users = affected_users
        self.root_cause_elements = root_cause_elements_length
        self.updating_time = updating_time
        self.file_suspects = file_suspects
        self.process_suspects = process_suspects
        self.connections = connections
        self.timeline_events = timeline_events

    def to_json(self):
        return self.raw_data

    def to_table(self):
        return {
            "Element Name": self.element_name,
            "Detection Type": self.detection_type,
            "Malop Activity Types": (
                " ".join(self.malop_activity_types) if self.malop_activity_types else ""
            ),
            "Affected Machines": f"{len(self.affected_machines) if self.affected_machines else 0} machines",
            "Affected Users": f"{len(self.affected_users) if self.affected_users else 0} users",
            "Root Cause Elements": f"{self.root_cause_elements} elements",
        }

    def to_csv(self):
        return flat_dict_to_csv(self.to_table())


class Process(QueryResultObject):
    def __init__(
        self,
        raw_data,
        constructed_data=None,
        guid=None,
        element_name=None,
        creation_time=None,
        end_time=None,
        command=None,
        signed_and_verified=None,
        product_type=None,
        owner_machine=None,
        user=None,
        md5=None,
        execution_prevented=None,
        icon_base64=None,
        company_name=None,
        malicious_classification_type=None,
        product_name=None,
        sha1_string=None,
        is_white_list_classification=None,
        image_file=None,
        parent_process=None,
        children=None,
        matched_white_list_rule_ids=None,
        pid=None,
        ransomware_auto_remediation_suspended=None,
    ):
        super(Process, self).__init__(raw_data, constructed_data)
        self.element_name = element_name
        self.creation_time = creation_time
        self.end_time = end_time
        self.command = command
        self.signed_and_verified = signed_and_verified
        self.product_type = product_type
        self.owner_machine = owner_machine
        self.user = user
        self.md5 = md5
        self.guid = guid
        self.execution_prevented = execution_prevented
        self.icon_base64 = icon_base64
        self.company_name = company_name
        self.malicious_classification_type = malicious_classification_type
        self.product_name = product_name
        self.sha1_string = sha1_string
        self.is_whiteList_classification = is_white_list_classification
        self.image_file = image_file
        self.parent_process = parent_process
        self.children = children
        self.matched_white_list_rule_ids = matched_white_list_rule_ids
        self.pid = pid
        self.ransomware_auto_remediation_suspended = (
            ransomware_auto_remediation_suspended
        )

    def to_csv(self):
        data = {
            "Element Name": self.element_name,
            "Creation Time": self.creation_time,
            "End Time": self.end_time,
            "Command": self.command,
            "Signed And Verified": self.signed_and_verified,
            "Product Type": self.product_type,
            "Owner Machine": self.owner_machine,
            "User": self.user,
            "MD5": self.md5,
            "PID": self.pid,
        }

        data = {key: (value if value else "") for key, value in data.items()}

        return data

    def to_json(self):
        return self.raw_data


class MalopProcess(QueryResultObject):
    def __init__(
        self,
        raw_data,
        constructed_data=None,
        guid=None,
        element_name=None,
        detection_type=None,
        malop_activity_types=None,
        affected_machines=None,
        affected_users=None,
        root_cause_elements=None,
    ):
        super(MalopProcess, self).__init__(raw_data, constructed_data)
        self.element_name = element_name
        self.detection_type = detection_type
        self.malop_activity_types = malop_activity_types
        self.affected_machines = affected_machines
        self.affected_users = affected_users
        self.root_cause_elements = root_cause_elements
        self.guid = guid

    def to_table(self):
        return {
            "Element Name": self.element_name,
            "Detection Type": self.detection_type,
            "Malop Activity Types": (
                " ".join(self.malop_activity_types) if self.malop_activity_types else ""
            ),
            "Affected Machines": f"{len(self.affected_machines) if self.affected_machines else 0} machines",
            "Affected Users": f"{len(self.affected_users) if self.affected_users else 0} users",
            "Root Cause Elements": f"{len(self.root_cause_elements) if self.root_cause_elements else 0} elements",
        }

    def to_csv(self):
        return flat_dict_to_csv(self.to_table())


class Machine(QueryResultObject):
    def __init__(
        self,
        raw_data=None,
        constructed_data=None,
        guid=None,
        element_name=None,
        os_version=None,
        os_type=None,
        dns_hostname=None,
        isolated=None,
        users=None,
        network_interfaces=None,
        logon_sessions=None,
        platform_arch=None,
        uptime=None,
        is_connected=None,
        last_seen=None,
        is_malicious=None,
    ):
        super(Machine, self).__init__(raw_data, constructed_data)
        self.element_name = element_name
        self.os_version = os_version
        self.os_type = os_type
        self.dns_hostname = dns_hostname
        self.isolated = isolated
        self.users = users
        self.network_interfaces = network_interfaces
        self.logon_sessions = logon_sessions
        self.platform_arch = platform_arch
        self.uptime = uptime
        self.is_connected = is_connected
        self.last_seen = last_seen
        self.guid = guid
        self.is_malicious = is_malicious

    def to_csv(self):
        return {
            "Element Name": self.element_name,
            "OS Version": self.os_version,
            "Platform Architecture": self.platform_arch,
            "Uptime": self.uptime,
            "Cybereason Service Active": self.is_connected,
            "Last Seen": self.last_seen,
        }

    def to_json(self):
        return self.raw_data

    def as_enrichment_data(self):
        enrichment_data = self.constructed_data
        enrichment_data = {k: v for k, v in enrichment_data.items() if v}
        enrichment_data["timeStampSinceLastConnectionTime"] = (
            milliseconds_to_human_time(
                enrichment_data.get("timeStampSinceLastConnectionTime")
            )
        )
        enrichment_data["uptime"] = milliseconds_to_human_time(
            enrichment_data.get("uptime")
        )
        try:
            enrichment_data["self"] = enrichment_data["self"][0]
        except:
            pass
        return dict_to_flat(enrichment_data)

    def to_insight(self):
        color = "#ff0000" if self.is_malicious else "#339966"
        return (
            f'<h2>Malicious: <span style="color: {color};"> {self.is_malicious}'
            f'</span></span></h2><br><p><strong>OS:</strong> {self.os_type or ""}, {self.os_version or ""}'
            f'<br /><strong>DNS Name: </strong>{self.dns_hostname or ""}<br /><strong>Isolated: '
            f'</strong>{self.isolated or ""}<br />'
            f'<strong>Uptime: </strong>{self.uptime or ""}<br /><strong>Users: '
            f'</strong>{self.users or ""}<br />'
            f'<strong>Network Interfaces: </strong>{self.network_interfaces or ""}<br /><strong>Logon Sessions: '
            f'</strong>{self.logon_sessions or ""}</p>'
        )


class SingleMalopMachine(QueryResultObject):
    def __init__(
        self,
        raw_data,
        element_name=None,
        os_version=None,
        platform_arch=None,
        uptime=None,
        is_connected=None,
        last_seen=None,
    ):
        super().__init__(raw_data)
        self.element_name = element_name
        self.os_version = os_version
        self.platform_arch = platform_arch
        self.uptime = uptime
        self.is_connected = is_connected
        self.last_seen = last_seen


class MachineObject(QueryResultObject):
    def __init__(
        self,
        raw_data,
        constructed_data,
        guid=None,
        is_isolated=None,
        pylum_id=None,
        element_name=None,
        os_version=None,
        platform_arch=None,
        uptime=None,
        is_connected=None,
        last_seen=None,
    ):
        super().__init__(raw_data, constructed_data)
        self.guid = guid
        self.is_isolated = is_isolated
        self.pylum_id = pylum_id
        self.element_name = element_name
        self.os_version = os_version
        self.platform_arch = platform_arch
        self.uptime = uptime
        self.is_connected = is_connected
        self.last_seen = last_seen

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        return {
            "Element Name": self.element_name,
            "OS Version": self.os_version,
            "Platform Architecture": self.platform_arch,
            "Uptime": self.uptime,
            "Cybereason Service Active": self.is_connected,
            "Last Seen": self.last_seen,
        }


class File(QueryResultObject):
    def __init__(
        self,
        raw_data=None,
        constructed_data=None,
        guid=None,
        element_name=None,
        md5=None,
        sha1=None,
        size=None,
        path=None,
        owner_machine=None,
        is_signed=None,
        signature_verified=None,
        malicious_classification_type=None,
        product_name=None,
        product_version=None,
        company_name=None,
        internal_name=None,
        creation_time=None,
        modified_time=None,
        av_remediation_status=None,
    ):
        super(File, self).__init__(raw_data, constructed_data)
        self.element_name = element_name
        self.guid = guid
        self.md5 = md5
        self.sha1 = sha1
        self.size = size
        self.path = path
        self.owner_machine = owner_machine
        self.is_signed = is_signed
        self.signature_verified = signature_verified
        self.malicious_classification_type = malicious_classification_type
        self.product_name = product_name
        self.product_version = product_version
        self.company_name = company_name
        self.internal_name = internal_name
        self.creation_time = creation_time
        self.modified_time = modified_time
        self.av_remediation_status = av_remediation_status

    def to_csv(self, fields_to_return):
        data = {
            "Element Name": self.element_name,
            "MD5": self.md5,
            "SHA1": self.sha1,
            "Path": self.path,
            "Size": self.size,
            "Creation Time": self.creation_time,
            "Modification Time": self.modified_time,
        }
        if fields_to_return:
            data.update(
                {
                    "Modification Time": self.modified_time,
                    "Owner Machine": self.owner_machine,
                    "Is Signed": self.is_signed,
                    "Product Name": self.product_name,
                    "Product Version": self.product_version,
                    "Company Name": self.company_name,
                    "Internal Name": self.internal_name,
                    "Av Remediation Status": self.av_remediation_status,
                    "Signature Verified": self.signature_verified,
                    "Malicious Classification Type": self.malicious_classification_type,
                }
            )
        data = {key: value for key, value in data.items() if value}
        return data

    def to_json(self):
        return self.raw_data

    def as_enrichment_data(self, type, owner_machine=None):
        enrichment_data = {
            "type": type,
            "path": self.path,
            "md5": self.md5,
            "signed": self.is_signed,
            "verified_signature": self.signature_verified,
            "display_name": self.element_name,
            "affected_machines": "; ".join(owner_machine) if owner_machine else None,
            "sha1": self.sha1,
            "size": self.size,
        }

        enrichment_data = {k: v for k, v in enrichment_data.items() if v}
        return dict_to_flat(enrichment_data)

    def to_insight(self, type, owner_machine=None):
        color = "#ff0000" if type in SUSPICIOUS_TYPES else "#ffffff"
        return (
            f'<h2>TYPE:<span style="color: {color};"> {type}'
            f'</h2><br><p><strong>Display Name:</strong> {self.element_name or ""}&nbsp;'
            f'<br /><strong>Path:</strong> {self.path or ""}<br /><strong>Signed:</strong> '
            f'{self.is_signed or ""}<br /><strong>Verified Signature:</strong> '
            f'{self.signature_verified or ""}<br /><strong>Size:</strong> {self.size or ""}'
            f'<br /><strong>Affected Machines:</strong> {", ".join(owner_machine) if owner_machine else ""}</p>'
        )


class MalopDetails:
    def __init__(self, raw_data, element_type, name):
        self.raw_data = raw_data
        self.element_type = element_type
        self.name = name

    def to_json(self):
        return self.raw_data

    def to_event(self):
        event_json = copy.deepcopy(self.raw_data)
        event_json[self.element_type] = self.name
        return event_json


class Alert:
    def __init__(
        self,
        raw_data,
        guid,
        display_name,
        detection_types,
        severity,
        malop_detection_type,
        creation_time,
        updating_time,
        status,
        machines,
        users,
    ):
        self.raw_data = raw_data
        self.guid = guid
        self.display_name = display_name
        self.detection_types = detection_types
        self.severity = severity
        self.malop_detection_type = malop_detection_type
        self.creation_time = creation_time
        self.updating_time = updating_time
        self.status = status
        self.machines = machines
        self.users = users

    def to_json(self):
        return self.raw_data

    @property
    def priority(self):
        """
        Converts API severity format to SIEM priority
        :return: SIEM priority
        """
        return CYBEREASON_TO_SIEM_SEVERITY.get(self.severity, -1)

    def to_alert_info(self, environment, events):
        """
        Creates Siemplify Alert Info based on Malop Alert information
        :param environment: EnvironmentHandle object
        :param events: List of Malop events
        :return: Alert Info object
        """
        alert_info = AlertInfo()
        alert_info.ticket_id = self.guid
        alert_info.display_id = str(uuid.uuid4())
        alert_info.name = self.display_name
        alert_info.description = convert_list_to_comma_string(self.detection_types)
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = DEVICE_PRODUCT
        alert_info.priority = self.priority
        alert_info.rule_generator = self.malop_detection_type
        alert_info.start_time = self.creation_time
        alert_info.end_time = self.creation_time
        alert_info.events = events
        alert_info.environment = environment.get_environment(self.raw_data)

        return alert_info

    def to_flat(self):
        return dict_to_flat(self.to_json())

    def to_event(self):
        return dict_to_flat(self.raw_data)

    def get_events(self, events):
        malop_data = copy.deepcopy(self.to_json())
        machines = malop_data.pop(MACHINES_KEY, [])
        users = malop_data.pop(USERS_KEY, [])
        if not events:
            return self.merge_non_entity_events(malop_data, machines or [], users or [])
        return self.merge_events(
            malop_data, [item.to_event() for item in events], ENTITY_KEY
        )

    @staticmethod
    def get_events_with_multiple_keys(events):
        events_data = []

        for event in events:
            for attribute in EVENT_PROPERTIES_FROM_SINGLE_MALOP:
                if getattr(event, attribute):
                    for item in getattr(event, attribute):
                        item.update({"lastUpdateTime": event.updating_time})
                        events_data.append(dict_to_flat(item))

        return events_data

    @staticmethod
    def merge_events(malop_data, events, key):
        merged_events = []
        for event in events:
            malop_data[key] = event
            merged_events.append(dict_to_flat(malop_data))

        return merged_events

    @staticmethod
    def merge_non_entity_events(malop_data, machines, users):
        merged_events = []
        if len(machines) >= len(users):
            for i, machine in enumerate(machines):
                malop_data[MACHINES_KEY] = machine
                user = users[i] if i < len(users) else users[0] if users else None
                if user:
                    malop_data[USERS_KEY] = user
                merged_events.append(dict_to_flat(malop_data))
        elif len(machines) < len(users):
            for i, user in enumerate(users):
                malop_data[USERS_KEY] = user
                machine = (
                    machines[i]
                    if i < len(machines)
                    else machines[0] if machines else None
                )
                if machine:
                    malop_data[MACHINES_KEY] = machine
                merged_events.append(dict_to_flat(malop_data))

        return merged_events


class Reputation:
    def __init__(
        self,
        raw_data,
        key=None,
        reputation=None,
        prevent_execution=None,
        comment=None,
        remove=None,
    ):
        self.raw_data = raw_data
        self.key = key
        self.reputation = reputation
        self.prevent_execution = prevent_execution
        self.comment = comment if comment != "null" else None
        self.remove = remove

    def to_json(self):
        return {
            "key": self.key,
            "reputation": self.reputation,
            "prevent_execution": self.prevent_execution,
            "comment": self.comment,
            "remove": self.remove,
        }

    def to_csv(self):
        return {
            "Key": self.key,
            "Reputation": self.reputation,
            "Prevent Execution": self.prevent_execution,
            "Comment": self.comment,
            "Remove": self.remove,
        }


class Entity_Details(QueryResultObject):
    def __init__(self, raw_data=None, type=None):
        super(Entity_Details, self).__init__(raw_data)
        self.type = type

    def to_json(self):

        return self.raw_data

    def as_enrichment_data(self, type=None, owner_machine=None):
        enrichment_data = {"type": self.type}
        enrichment_data = {k: v for k, v in enrichment_data.items() if v}

        return dict_to_flat(enrichment_data)

    def to_insight(self, type=None, owner_machine=None):
        color = "#ff0000" if self.type in SUSPICIOUS_TYPES else "#ffffff"
        return f'<h2>TYPE: <span style="color: {color};"> {self.type or ""}</h2>'


class SingleMalopProcess(QueryResultObject):
    def __init__(
        self,
        raw_data,
        clas=None,
        first_seen=None,
        last_seen=None,
        counter=None,
        was_ever_detected_in_scan=None,
        was_ever_detected_by_access=None,
        detection_decision_status=None,
        command=None,
        pid=None,
        user=None,
        owner_machine=None,
        creation_time=None,
        end_time=None,
        element_display_name=None,
        guid=None,
    ):
        super(SingleMalopProcess, self).__init__(raw_data)
        self.raw_data = raw_data
        self.clas = clas
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.counter = counter
        self.was_ever_detected_in_scan = was_ever_detected_in_scan
        self.was_ever_detected_by_access = was_ever_detected_by_access
        self.detection_decision_status = detection_decision_status
        self.command = command
        self.pid = pid
        self.owner_machine = owner_machine
        self.user = user
        self.creation_time = creation_time
        self.end_time = end_time
        self.element_display_name = element_display_name
        self.guid = guid

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        data = {
            "Command": self.command,
            "PID": self.pid,
            "Owner Machine": self.owner_machine,
            "User": self.user,
            "Creation Time": self.creation_time,
            "End Time": self.end_time,
            "Element Name": self.element_display_name,
        }
        data = {key: (value if value else "") for key, value in data.items()}

        return data


class InvestigationSearchItem(QueryResultObject):
    def __init__(self, raw_data, simple_values, element_values):
        super(InvestigationSearchItem, self).__init__(raw_data)
        self.simple_values = simple_values
        self.element_values = element_values

    def to_json(self) -> dict:
        return {
            "simpleValues": self.simple_values,
            "elementValues": self.element_values,
        }

    def to_table(self) -> dict:
        table_dict = {}

        for simple_key, simple_value in self.simple_values.items():
            table_dict[simple_key] = convert_list_to_comma_string(
                simple_value.get("values")
            )

        for element_key, element_value in self.element_values.items():
            table_dict[element_key] = convert_list_to_comma_string(element_value)

        return table_dict


class Sensor(QueryResultObject):
    def __init__(
        self,
        raw_data=None,
        guid=None,
        status=None,
        group_name=None,
        policy_name=None,
        isolated=None,
        internal_ip_address=None,
        pylum_id=None,
        machine_name=None,
        fqdn=None,
        service_status=None,
        os_type=None,
        site=None,
        uptime=None,
    ):
        super(Sensor, self).__init__(raw_data)
        self.status = status
        self.group_name = group_name
        self.policy_name = policy_name
        self.isolated = isolated
        self.pylum_id = pylum_id
        self.internal_ip_address = internal_ip_address
        self.machine_name = machine_name
        self.fqdn = fqdn
        self.service_status = service_status
        self.os_type = os_type
        self.site = site
        self.uptime = milliseconds_to_human_time(uptime)
        self.guid = guid

    def to_csv(self):
        return {
            "FQDN": self.fqdn,
            "Name": self.machine_name,
            "IP Address": self.internal_ip_address,
            "Site": self.site,
            "Isolated": self.isolated,
            "Uptime": self.uptime,
            "Policy": self.policy_name,
            "Group": self.group_name,
            "Status": self.status,
            "Service Status": self.service_status,
        }

    def to_json(self):
        return self.raw_data

    def as_enrichment_data(self):
        enrichment_data = {
            "status": self.status,
            "groupName": self.group_name,
            "policyName": self.policy_name,
            "isolated": self.isolated,
            "internalIpAddress": self.internal_ip_address,
            "machineName": self.machine_name,
            "fqdn": self.fqdn,
            "serviceStatus": self.service_status,
            "osType": self.os_type,
            "site": self.site,
            "upTime": self.uptime,
        }
        enrichment_data = {k: v for k, v in enrichment_data.items() if v is not None}
        return dict_to_flat(enrichment_data)

    def to_insight(self):
        return (
            f"<h3><strong>Service Status:&nbsp;</strong> {self.service_status}</h3><div><div><div><div>"
            f"<div><strong>FQDN</strong>: {self.fqdn}</div>"
            f"<div><strong>Name</strong>: {self.machine_name}</div>"
            f"<div><strong>IP Address</strong>: {self.internal_ip_address}</div>"
            f"<div><strong>Site</strong>: {self.site}</div>"
            f"<div><strong>Isolated</strong>: {self.isolated}</div>"
            f"<div><strong>Uptime</strong>: {self.uptime}</div>"
            f"<div><strong>Policy</strong>: {self.policy_name}</div>"
            f"<div><strong>Group</strong>: {self.group_name}</div>"
            f"<div><strong>Status</strong>: {self.status}</div>"
            f"</div></div></div></div><p>&nbsp;</p>"
        )


class MalopSuspeciousDetails(QueryResultObject):
    """MalopSuspeciousDetails class with inherit QueryResultObject class."""

    def __init__(
        self,
        raw_data: dict,
        unique_id: str = None,
        remediation_type: str = None,
        target_name: str = None,
        target_id: str = None,
        machine_name: str = None,
        machine_id: str = None,
        **kwargs,
    ) -> None:
        super().__init__(raw_data)
        self.unique_id = unique_id
        self.remediation_type = remediation_type
        self.target_name = target_name
        self.target_id = target_id
        self.machine_name = machine_name
        self.machine_id = machine_id
        self.is_block_action = (
            True if self.remediation_type in BLOCK_ACTION_LIST else False
        )

    def to_json(self) -> dict:
        return self.raw_data


class RemediateMalop(QueryResultObject):
    """RemediateMalop class with inherit QueryResultObject class."""

    def __init__(self, raw_data: dict, remediation_id: str | None = None) -> None:
        super().__init__(raw_data)
        self.remediation_id = remediation_id
        self.status_log = raw_data.get("statusLog")
        if self.status_log:
            self.is_success = (
                True if next(iter(self.status_log)).get("error") is None else False
            )

    def to_json(self) -> dict:
        return self.raw_data
