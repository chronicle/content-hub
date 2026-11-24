from __future__ import annotations
import copy
import hashlib
import json
from TIPCommon.transformation import add_prefix_to_dict, flat_dict_to_csv, dict_to_flat
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from sentinel_one_v2.core.constants import ENRICH_PREFIX, THREAT_MITIGATED_STATUS


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_flat(self):
        return dict_to_flat(self.to_json())

    def to_csv(self):
        return flat_dict_to_csv(self.to_flat())

    def is_empty(self):
        return not bool(self.raw_data)


class SystemStatus(BaseModel):
    def __init__(self, raw_data, is_ok=False, errors=None):
        super().__init__(raw_data)
        self.is_ok = is_ok
        self.errors = errors or []


class SystemInfo(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)


class AgentInterface(BaseModel):
    def __init__(
        self,
        raw_data,
        inet6=None,
        id=None,
        name=None,
        inet=None,
        physical=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.inet6 = inet6
        self.id = id
        self.name = name
        self.inet = inet
        self.physical = physical


class Agent(BaseModel):
    def __init__(
        self,
        raw_data,
        uuid=None,
        accountName=None,
        osUsername=None,
        siteId=None,
        isDecommissioned=None,
        accountId=None,
        machineType=None,
        isUpToDate=None,
        createdAt=None,
        isActive=None,
        domain=None,
        osName=None,
        modelName=None,
        osType=None,
        groupIp=None,
        id=None,
        agentVersion=None,
        groupId=None,
        groupName=None,
        siteName=None,
        externalId=None,
        lastActiveDate=None,
        activeThreats=None,
        networkStatus=None,
        totalMemory=None,
        osStartTime=None,
        scanStatus=None,
        encryptedApplications=None,
        updatedAt=None,
        externalIp=None,
        interfaces=[],
        lastLoggedInUserName=None,
        infected=None,
        osArch=None,
        scanFinishedAt=None,
        computerName=None,
        installerType=None,
        threatRebootRequired=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.uuid = uuid
        self.account_name = accountName
        self.os_username = osUsername
        self.site_id = siteId
        self.is_decommissioned = isDecommissioned
        self.account_id = accountId
        self.machine_type = machineType
        self.is_up_to_date = isUpToDate
        self.created_at = createdAt
        self.is_active = isActive
        self.domain = domain
        self.os_name = osName
        self.model_name = modelName
        self.os_type = osType
        self.group_ip = groupIp
        self.id = id
        self.agent_version = agentVersion
        self.group_id = groupId
        self.group_name = groupName
        self.site_name = siteName
        self.external_id = externalId
        self.last_active_date = lastActiveDate
        self.computer_name = computerName
        self.network_status = networkStatus
        self.total_memory = totalMemory
        self.os_start_time = osStartTime
        self.scan_status = scanStatus
        self.updated_at = updatedAt
        self.external_ip = externalIp
        self.interfaces = interfaces
        self.os_arch = osArch
        self.active_threats = int(activeThreats or 0)
        self.scan_finished_at = scanFinishedAt
        self.installer_type = installerType
        self.last_logged_in_user_name = lastLoggedInUserName
        self.encrypted_apps = encryptedApplications
        self.threat_reboot_required = threatRebootRequired
        self.infected = infected

    def to_insight(self):
        return f"""<table><tbody><tr> <td><strong>Status:</strong></td><td> <strong>&nbsp;</strong> <span style="color: #000000;">{"<span style='color: #ff0000;'><strong>Infected</strong></span>" if self.infected else "<span style='color: #339966;'><strong>Healthy</strong></span>"}</span> </td></tr></tbody></table><br><p><strong>General Information</strong></p><br><table><tbody><tr><td><strong>OS:</strong></td><td><div><div>{self.os_name}&nbsp;{self.os_arch}</div></div></td></tr><tr> <td><strong>Active Threats:</strong></td><td> <div> <div>{f"<span style='color: #ff0000;'>{self.active_threats}</span>" if self.active_threats > 0 else self.active_threats}</div></div></td></tr><tr> <td><strong>Last Active:</strong></td><td> <div> <div>{self.last_active_date}</div></div></td></tr><tr> <td> <div> <div><strong>Last Logged In:</strong></div></div></td><td> <div> <div>{self.last_logged_in_user_name}</div></div></td></tr><tr> <td> <div> <div><strong>Agent Version:</strong></div></div></td><td> <div> <div>{self.agent_version}</div></div></td></tr><tr> <td> <div> <div><strong>Last&nbsp;Disk&nbsp;Scan:</strong></div></div></td><td> <div> <div>{self.scan_finished_at}</div></div></td></tr><tr> <td> <div> <div><strong>Installer&nbsp;Type:</strong></div></div></td><td> <div> <div>{self.installer_type}</div></div></td></tr><tr> <td> <div> <div><strong>Application Encryption:&nbsp;</strong></div></div></td><td> <div> <div>{"On" if self.encrypted_apps else "Off"}</div></div></td></tr><tr> <td> <div> <div><strong>Network Status:</strong></div></div></td><td> <div> <div>{self.network_status}</div></div></td></tr><tr> <td> <div> <div><strong>Domain:</strong></div></div></td><td> <div> <div>{self.domain}</div></div></td></tr><tr> <td> <div> <div> <div> <div><strong>Reboot&nbsp;Required:&nbsp;</strong></div></div></div></div></td><td> <div> <div>{"Yes" if self.threat_reboot_required else "No"}</div></div></td></tr><tr> <td> <div> <div> <div> <div><strong>Console&nbsp;visible&nbsp;IP:</strong></div></div></div></div></td><td><div><div>{self.external_ip}</div></div></td></tr><tr><td><div><div><div><div><strong>Group&nbsp;Name:</strong></div></div></div></div></td><td> <div> <div>{self.group_name}</div></div></td></tr><tr> <td> <div> <div> <div> <div><strong>Site&nbsp;Name:</strong></div></div></div></div></td><td> <div> <div>{self.site_name}</div></div></td></tr></tbody> </table><br>{self.interfaces_insight_html}"""

    @property
    def interfaces_insight_html(self):
        return f"""<p><strong>Network Interfaces</strong></p><table style="table-layout: fixed"><tbody><tr><td style="text-align: center;"><strong>Name</strong></td><td style="text-align: center;"><strong>IP</strong></td><td style="text-align: center;"><strong>Mac Address</strong></td></tr>{"".join(f"<tr><td>{interface.name}&nbsp;</td><td>{''.join((f'<p>{inet}&nbsp</p>' for inet in interface.inet))}</td><td>{interface.physical}&nbsp;</td></tr>" for interface in self.interfaces)}</tbody> </table>"""


class Event(BaseModel):
    def __init__(
        self,
        raw_data,
        agentId=None,
        agentIp=None,
        agentName=None,
        agentOs=None,
        agentUuid=None,
        agentVersion=None,
        createdAt=None,
        eventType=None,
        id=None,
        pid=None,
        user=None,
        processName=None,
        relatedToThreat=None,
        objectType=None,
        uuid=None,
        trueContext=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.agent_id = agentId
        self.agent_ip = agentIp
        self.agent_name = agentName
        self.agent_os = agentOs
        self.agent_uuid = agentUuid
        self.agent_version = agentVersion
        self.created_at = createdAt
        self.event_type = eventType
        self.id = id
        self.raw_data = raw_data
        self.pid = pid
        self.process_name = processName
        self.related_to_threat = relatedToThreat
        self.user = user
        self.object_type = objectType
        self.uuid = uuid
        self.true_context = trueContext

        try:
            # Try parsing the created_at timestamp to unix time
            self.creation_time_unix_time = convert_string_to_unix_time(self.created_at)
        except Exception:
            self.creation_time_unix_time = 1

    def to_csv(self):
        return {
            "Agent Name": self.agent_name,
            "Agent OS": self.agent_os,
            "Agent IP": self.agent_ip,
            "Event Type": self.event_type,
            "Related To Threat": self.related_to_threat,
            "PID": self.pid,
            "Process Name": self.process_name,
            "Username": self.user,
            "Creation Time": self.created_at,
        }

    def to_json(self):
        temp = copy.deepcopy(self.raw_data)
        temp.update({"creation_time_unix_time": self.creation_time_unix_time})
        return temp

    def to_base_json(self):
        return super().to_json()

    def to_event(self):
        return dict_to_flat(self.to_json())

    def to_hash(self):
        temp = copy.deepcopy(self.raw_data)
        if "id" in temp:
            del temp["id"]

        return hashlib.md5(
            json.dumps(dict_to_flat(temp), sort_keys=True).encode()
        ).hexdigest()


class ProcessEvent(Event):
    def __init__(
        self,
        raw_data,
        agentId=None,
        agentIp=None,
        agentName=None,
        agentOs=None,
        agentUuid=None,
        agentVersion=None,
        createdAt=None,
        eventType=None,
        id=None,
        hasParent=None,
        md5=None,
        parentPid=None,
        parentProcessName=None,
        pid=None,
        processDisplayName=None,
        processCmd=None,
        processName=None,
        relatedToThreat=None,
        signedStatus=None,
        user=None,
        objectType=None,
        uuid=None,
        trueContext=None,
        **kwargs,
    ):
        super(ProcessEvent, self).__init__(
            raw_data,
            agentId,
            agentIp,
            agentName,
            agentOs,
            agentUuid,
            agentVersion,
            createdAt,
            eventType,
            id,
            pid,
            user,
            processName,
            relatedToThreat,
            objectType,
            uuid,
            trueContext,
        )
        self.has_parent = hasParent
        self.md5 = md5
        self.parent_pid = parentPid
        self.parent_process_name = parentProcessName
        self.process_display_name = processDisplayName
        self.process_cmd = processCmd
        self.signed_status = signedStatus

    def to_csv(self):
        csv = super(ProcessEvent, self).to_csv()
        csv.update(
            {
                "Command Line": self.process_cmd,
                "Signed Status": self.signed_status,
                "Parent PID": self.parent_pid,
                "Parent Process Name": self.parent_process_name,
            }
        )
        return csv


class FileEvent(Event):
    def __init__(
        self,
        raw_data,
        agentId=None,
        agentIp=None,
        agentName=None,
        agentOs=None,
        agentUuid=None,
        agentVersion=None,
        createdAt=None,
        eventType=None,
        id=None,
        hasParent=None,
        fileFullName=None,
        pid=None,
        processName=None,
        relatedToThreat=None,
        user=None,
        objectType=None,
        uuid=None,
        trueContext=None,
        **kwargs,
    ):
        super(FileEvent, self).__init__(
            raw_data,
            agentId,
            agentIp,
            agentName,
            agentOs,
            agentUuid,
            agentVersion,
            createdAt,
            eventType,
            id,
            pid,
            user,
            processName,
            relatedToThreat,
            objectType,
            uuid,
            trueContext,
        )
        self.has_parent = hasParent
        self.file_full_name = fileFullName

    def to_csv(self):
        csv = super(FileEvent, self).to_csv()
        csv.update({"File name": self.file_full_name})
        return csv


class IndicatorEvent(Event):
    def __init__(
        self,
        raw_data,
        agentId=None,
        agentIp=None,
        agentName=None,
        agentOs=None,
        agentUuid=None,
        agentVersion=None,
        createdAt=None,
        eventType=None,
        id=None,
        indicatorName=None,
        indicatorCategory=None,
        indicatorMetadata=None,
        pid=None,
        processName=None,
        relatedToThreat=None,
        user=None,
        objectType=None,
        uuid=None,
        trueContext=None,
        **kwargs,
    ):
        super(IndicatorEvent, self).__init__(
            raw_data,
            agentId,
            agentIp,
            agentName,
            agentOs,
            agentUuid,
            agentVersion,
            createdAt,
            eventType,
            id,
            pid,
            user,
            processName,
            relatedToThreat,
            objectType,
            uuid,
            trueContext,
        )
        self.indicator_name = indicatorName
        self.indicator_category = indicatorCategory
        self.indicator_metadata = indicatorMetadata

    def to_csv(self):
        csv = super(IndicatorEvent, self).to_csv()
        csv.update(
            {
                "Indicator Name": self.indicator_name,
                "Indicator Category": self.indicator_category,
                "Indicator Metadata": self.indicator_metadata,
            }
        )
        return csv


class DNSEvent(Event):
    def __init__(
        self,
        raw_data,
        agentId=None,
        agentIp=None,
        agentName=None,
        agentOs=None,
        agentUuid=None,
        agentVersion=None,
        createdAt=None,
        eventType=None,
        id=None,
        dnsRequest=None,
        dnsResponse=None,
        pid=None,
        processName=None,
        relatedToThreat=None,
        user=None,
        objectType=None,
        uuid=None,
        trueContext=None,
        **kwargs,
    ):
        super(DNSEvent, self).__init__(
            raw_data,
            agentId,
            agentIp,
            agentName,
            agentOs,
            agentUuid,
            agentVersion,
            createdAt,
            eventType,
            id,
            pid,
            user,
            processName,
            relatedToThreat,
            objectType,
            uuid,
            trueContext,
        )
        self.dns_request = dnsRequest
        self.dns_response = dnsResponse

    def to_csv(self):
        csv = super(DNSEvent, self).to_csv()
        csv.update({"DNS Request": self.dns_request, "DNS Response": self.dns_response})
        return csv


class NetworkActionsEvent(Event):
    def __init__(
        self,
        raw_data,
        agentId=None,
        agentIp=None,
        agentName=None,
        agentOs=None,
        agentUuid=None,
        agentVersion=None,
        createdAt=None,
        eventType=None,
        id=None,
        dstIp=None,
        dstPort=None,
        direction=None,
        connectionStatus=None,
        pid=None,
        processName=None,
        relatedToThreat=None,
        user=None,
        objectType=None,
        uuid=None,
        trueContext=None,
        **kwargs,
    ):
        super(NetworkActionsEvent, self).__init__(
            raw_data,
            agentId,
            agentIp,
            agentName,
            agentOs,
            agentUuid,
            agentVersion,
            createdAt,
            eventType,
            id,
            pid,
            user,
            processName,
            relatedToThreat,
            objectType,
            uuid,
            trueContext,
        )
        self.dst_ip = dstIp
        self.dst_port = dstPort
        self.direction = direction
        self.connection_status = connectionStatus

    def to_csv(self):
        csv = super(NetworkActionsEvent, self).to_csv()
        csv.update(
            {
                "Destination IP": self.dst_ip,
                "Destination Port": self.dst_port,
                "Direction": self.direction,
                "Connection Status": self.connection_status,
            }
        )
        return csv


class URLEvent(Event):
    def __init__(
        self,
        raw_data,
        agentId=None,
        agentIp=None,
        agentName=None,
        agentOs=None,
        agentUuid=None,
        agentVersion=None,
        createdAt=None,
        eventType=None,
        id=None,
        networkUrl=None,
        networkSource=None,
        pid=None,
        processName=None,
        relatedToThreat=None,
        user=None,
        objectType=None,
        uuid=None,
        trueContext=None,
        **kwargs,
    ):
        super(URLEvent, self).__init__(
            raw_data,
            agentId,
            agentIp,
            agentName,
            agentOs,
            agentUuid,
            agentVersion,
            createdAt,
            eventType,
            id,
            pid,
            user,
            processName,
            relatedToThreat,
            objectType,
            uuid,
            trueContext,
        )
        self.url = networkUrl
        self.source = networkSource

    def to_csv(self):
        csv = super(URLEvent, self).to_csv()
        csv.update({"URL": self.url, "Source": self.source})
        return csv


class RegistryEvent(Event):
    def __init__(
        self,
        raw_data,
        agentId=None,
        agentIp=None,
        agentName=None,
        agentOs=None,
        agentUuid=None,
        agentVersion=None,
        createdAt=None,
        eventType=None,
        id=None,
        registryId=None,
        registryPath=None,
        pid=None,
        processName=None,
        relatedToThreat=None,
        user=None,
        objectType=None,
        uuid=None,
        trueContext=None,
        **kwargs,
    ):
        super(RegistryEvent, self).__init__(
            raw_data,
            agentId,
            agentIp,
            agentName,
            agentOs,
            agentUuid,
            agentVersion,
            createdAt,
            eventType,
            id,
            pid,
            user,
            processName,
            relatedToThreat,
            objectType,
            uuid,
            trueContext,
        )
        self.registry_id = registryId
        self.registry_path = registryPath

    def to_csv(self):
        csv = super(RegistryEvent, self).to_csv()
        csv.update(
            {"Registry ID": self.registry_id, "Registry Path": self.registry_path}
        )
        return csv


class QueryEvent(Event):
    """
    Deep Visibility Query Event
    """

    def __init__(
        self,
        raw_data,
        agentId=None,
        agentIp=None,
        agentName=None,
        agentOs=None,
        agentUuid=None,
        agentVersion=None,
        createdAt=None,
        eventType=None,
        id=None,
        pid=None,
        user=None,
        processName=None,
        relatedToThreat=None,
        objectType=None,
        uuid=None,
        trueContext=None,
        siteName=None,
        eventTime=None,
        srcProcUid=None,
        srcProcImageSha256=None,
        srcProcImageMd5=None,
        **kwargs,
    ):
        super(QueryEvent, self).__init__(
            raw_data,
            agentId,
            agentIp,
            agentName,
            agentOs,
            agentUuid,
            agentVersion,
            createdAt,
            eventType,
            id,
            pid,
            user,
            processName,
            relatedToThreat,
            objectType,
            uuid,
            trueContext,
        )
        self.site_name = siteName
        self.event_time = eventTime
        self.proc_uid = srcProcUid
        self.proc_sha256 = srcProcImageSha256
        self.proc_md5 = srcProcImageMd5

    def as_csv(self):
        return {
            "Event Type": self.event_type,
            "Site Name": self.site_name,
            "Time": self.event_time,
            "Agent OS": self.agent_os,
            "Process ID": self.pid,
            "Process UID": self.proc_uid,
            "Process Name": self.process_name,
            "SHA256": self.proc_sha256,
            "MD5": self.proc_md5,
        }

    def as_json(self):
        return self.raw_data


class ScheduledTaskEvent(Event):
    def __init__(
        self,
        raw_data,
        agentId=None,
        agentIp=None,
        agentName=None,
        agentOs=None,
        agentUuid=None,
        agentVersion=None,
        createdAt=None,
        eventType=None,
        id=None,
        taskName=None,
        taskPath=None,
        pid=None,
        processName=None,
        relatedToThreat=None,
        user=None,
        objectType=None,
        uuid=None,
        trueContext=None,
        **kwargs,
    ):
        super(ScheduledTaskEvent, self).__init__(
            raw_data,
            agentId,
            agentIp,
            agentName,
            agentOs,
            agentUuid,
            agentVersion,
            createdAt,
            eventType,
            id,
            pid,
            user,
            processName,
            relatedToThreat,
            objectType,
            uuid,
            trueContext,
        )
        self.task_name = taskName
        self.task_path = taskPath

    def to_csv(self):
        csv = super(ScheduledTaskEvent, self).to_csv()
        csv.update({"Task Name": self.task_name, "Task Path": self.task_path})
        return csv


class Hash(BaseModel):
    def __init__(self, raw_data, rank=None):
        super().__init__(raw_data)
        self.rank = int(rank)
        self.is_suspicious = False
        self._reputation_threshold = None
        self.update_is_risky()

    @property
    def reputation_threshold(self):
        return self._reputation_threshold

    @reputation_threshold.setter
    def reputation_threshold(self, value):
        self._reputation_threshold = value
        self.is_suspicious = self.rank >= self.reputation_threshold
        self.update_is_risky()

    def update_is_risky(self):
        self.raw_data.update({"is_risky": self.is_suspicious})

    def to_dict(self):
        return {"rank": self.rank, "reputation": self.rank}

    def to_insight(self):
        return f"""<table><tbody><tr><td><strong>Reputation</strong>:</td><td>&nbsp;<strong{' style="color: #ff0000"' if self.is_suspicious else ""}>{self.rank}</strong></td></tr></tbody></table>"""

    def to_enrichment_data(self):
        return add_prefix_to_dict(self.to_dict(), ENRICH_PREFIX)


class PathObject(BaseModel):
    def __init__(self, raw_data, value, created_at, path_id, scope_name):
        super().__init__(raw_data)
        self.value = value
        self.created_at = created_at
        self.path_id = path_id
        self.scope_name = scope_name

    def to_csv(self, value_key="Path"):
        return {
            value_key: self.value,
            "Created At": self.created_at,
            "ID": self.path_id,
            "Scope Name": self.scope_name,
        }


class ErrorObject(BaseModel):
    def __init__(self, raw_data, code, detail, title):
        super().__init__(raw_data)
        self.code = code
        self.detail = detail
        self.title = title


class ThreatEvent(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)


class Threat(BaseModel):
    def __init__(
        self,
        raw_data,
        threat_id,
        threat_name=None,
        agent_id=None,
        created_at=None,
        classification=None,
        analyst_verdict=None,
        mitigation_status=None,
        site_id=None,
        site_name=None,
        rank=None,
        marked_as_benign=None,
        resolved=None,
        hash_value=None,
        in_quarantine=None,
        description=None,
    ):
        super().__init__(raw_data)
        self.threat_id = threat_id
        self.threat_name = threat_name
        self.agent_id = agent_id
        self.analyst_verdict = analyst_verdict
        self.created_at = created_at
        self.classification = classification
        self.mitigation_status = mitigation_status
        self.mitigated = mitigation_status == THREAT_MITIGATED_STATUS
        self.site_id = site_id
        self.site_name = site_name
        self.rank = rank
        self.marked_as_benign = marked_as_benign
        self.in_quarantine = in_quarantine
        self.resolved = resolved
        self.hash_value = hash_value
        self.description = description

        try:
            # Try parsing the created_at timestamp to unix time
            self.creation_time_unix_time = convert_string_to_unix_time(self.created_at)
        except Exception:
            self.creation_time_unix_time = 1

    def to_csv(self):
        return {
            "Threat Name": self.threat_name,
            "Created At": self.created_at,
            "ID": self.threat_id,
            "Classification": self.classification,
            "Mitigation status": self.mitigation_status,
            "SiteID": self.site_id,
            "Site Name": self.site_name,
            "Rank": self.rank,
            "MarkedAsBenign": self.marked_as_benign,
            "InQuarantine": self.in_quarantine,
            "Agent ID": self.agent_id,
        }

    def to_mitigate_json(self, mitigation_action):
        return {
            "Threat_ID": self.threat_id,
            "mitigated": self.mitigated,
            "mitigation_action": mitigation_action,
        }

    def to_threat_json(self, marked):
        return {"ID": self.threat_id, "marked_as_threat": marked}

    def to_resolve_json(self):
        return {"Threat_ID": self.threat_id, "resolved": self.resolved}


class BlacklistedThreat(BaseModel):
    def __init__(
        self, raw_data, hash_value, hash_id, scope_name, os_type, description, username
    ):
        super().__init__(raw_data)
        self.hash_value = hash_value
        self.scope_name = scope_name
        self.description = description
        self.os_type = os_type
        self.username = username
        self.hash_id = hash_id

    def to_csv(self):
        return {
            "Hash": self.hash_value,
            "Scope": self.scope_name,
            "Description": self.description,
            "OS": self.os_type,
            "User": self.username,
        }


class Group(BaseModel):
    """
    Group data
    """

    def __init__(
        self,
        raw_data,
        createdAt=None,
        rank=None,
        registrationToken=None,
        inherits=None,
        isDefault=None,
        type=None,
        creator=None,
        id=None,
        name=None,
        filterName=None,
        updatedAt=None,
        siteId=None,
        creatorId=None,
        filterId=None,
        totalAgents=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.created_at = createdAt
        self.rank = rank
        self.registration_token = registrationToken
        self.inherits = inherits
        self.is_default = isDefault
        self.type = type
        self.creator = creator
        self.id = id
        self.name = name
        self.filter_name = filterName
        self.updated_at = updatedAt
        self.site_id = siteId
        self.creator_id = creatorId
        self.filter_id = filterId
        self.total_agents = totalAgents

    def as_csv(self):
        return {
            "Name": self.name,
            "ID": self.id,
            "Type": self.type,
            "Rank": self.rank,
            "Creator": self.creator,
            "Creation Time": self.created_at,
        }


class Application(BaseModel):
    def __init__(self, raw_data, installed_date, name, publisher, size, version):
        super(Application, self).__init__(raw_data)
        self.installed_date = installed_date
        self.name = name
        self.publisher = publisher
        self.size = size
        self.version = version

    def to_csv(self):
        return {
            "Installed Date": self.installed_date,
            "Size": self.size,
            "Name": self.name,
            "Publisher": self.publisher,
            "Version": self.version,
        }


class ThreatNote(BaseModel):
    def __init__(self, raw_data, text):
        super().__init__(raw_data)
        self.text = text
        self.message = text


class Site(BaseModel):
    def __init__(self, raw_data, name, id, creator, expiration, site_type, state):
        super(Site, self).__init__(raw_data)
        self.name = name
        self.id = id
        self.creator = creator
        self.expiration = expiration
        self.site_type = site_type
        self.state = state

    def to_csv(self):
        return {
            "Name": self.name,
            "ID": self.id,
            "Creator": self.creator,
            "Expiration": self.expiration,
            "Type": self.site_type,
            "State": self.state,
        }
