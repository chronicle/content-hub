# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from abc import abstractmethod, ABCMeta
import copy
from enum import Enum
from typing import Any
from soar_sdk.SiemplifyUtils import dict_to_flat, convert_string_to_unix_time
from TIPCommon.types import SingleJson

from .constants import (
    DEFAULT_VENDOR_NAME,
    DEFAULT_PRODUCT_NAME,
    GRAPH_VENDOR,
    PRODUCT_NAME_V2,
)
import uuid
import json


class AbstractData(metaclass=ABCMeta):
    """
    Abstract Data Model for others Data Models
    """

    def to_table(self):
        return [self.to_csv()]

    def to_csv(self):
        return dict_to_flat(self.to_json())

    @abstractmethod
    def to_json(self):
        pass

    @abstractmethod
    def to_enrichment_data(self):
        pass

    @staticmethod
    def convert_list_to_comma_string(values_list):
        if not values_list:
            return ""
        return ", ".join(values_list) if isinstance(values_list, list) else values_list


class DefenderPriorityEnum(Enum):
    UNSPECIFIED = "UnSpecified"
    INFO = "Informational"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class SiemplifyPriorityEnum(Enum):
    UNSPECIFIED = -1
    INFO = -1
    LOW = 40
    MEDIUM = 60
    HIGH = 80


class AlertUser(AbstractData):
    def __init__(self, accountName=None, domainName=None, **kwargs):
        self.account_name = accountName
        self.domain_name = domainName

    def to_json(self):
        return {"account_name": self.account_name, "domain_name": self.domain_name}

    def to_enrichment_data(self):
        pass


class Indicator(AbstractData):
    def __init__(
        self,
        raw_data=None,
        identifier=None,
        indicator_value=None,
        indicator_type=None,
        action=None,
        severity=None,
        description=None,
        title=None,
        recommended_actions=None,
    ):
        self.raw_data = raw_data
        self.identifier = identifier
        self.indicator_value = indicator_value
        self.indicator_type = indicator_type
        self.action = action
        self.severity = severity
        self.description = description
        self.title = title
        self.recommended_actions = recommended_actions

    def to_json(self):
        return self.raw_data

    def to_enrichment_data(self):
        pass

    def to_table(self):
        data = dict_to_flat(
            {
                "Type": self.indicator_type,
                "Action": self.action,
                "Severity": self.severity,
                "Description": self.description,
                "Title": self.title,
                "Recommendation": self.recommended_actions,
            }
        )
        data = {key: value for key, value in list(data.items()) if value is not None}
        return data


class AlertFile(AbstractData):
    def __init__(self, sha1=None, sha256=None, filePath=None, fileName=None, **kwargs):
        self.sha1 = sha1
        self.sha256 = sha256
        self.file_path = filePath
        self.file_name = fileName

    def to_json(self):
        return {
            "sha1": self.sha1,
            "sha256": self.sha256,
            "file_path": self.file_path,
            "file_name": self.file_name,
        }

    def to_enrichment_data(self):
        pass


class Alert(AbstractData):
    def __init__(
        self,
        raw_data,
        id=None,
        incidentId=None,
        investigationId=None,
        assignedTo=None,
        severity=None,
        status=None,
        classification=None,
        determination=None,
        investigationState=None,
        detectionSource=None,
        category=None,
        threatFamilyName=None,
        title=None,
        description=None,
        alertCreationTime=None,
        firstEventTime=None,
        lastEventTime=None,
        lastUpdateTime=None,
        resolvedTime=None,
        machineId=None,
        alertUser=None,
        comments=None,
        alertFiles=None,
        alertDomains=None,
        alertIps=None,
        alertProcesses=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.id = id
        self.incident_id = incidentId
        self.investigation_id = investigationId
        self.assigned_to = assignedTo
        self.severity = severity
        self.status = status
        self.classification = classification
        self.determination = determination
        self.investigation_state = investigationState
        self.detection_source = detectionSource
        self.category = category
        self.threat_family_name = threatFamilyName
        self.title = title
        self.description = description
        self.alert_creation_time = alertCreationTime or kwargs.get("createdDateTime")
        try:
            self.alert_creation_time_timestamp = convert_string_to_unix_time(
                self.alert_creation_time
            )
        except Exception:
            self.alert_creation_time_timestamp = 1
        self.first_event_time = firstEventTime or kwargs.get("firstActivityDateTime")
        self.last_event_time = lastEventTime or kwargs.get("lastActivityDateTime")
        self.last_update_time = lastUpdateTime or kwargs.get("lastUpdateDateTime")
        self.resolved_time = resolvedTime or kwargs.get("resolvedDateTime")
        self.machine_id = machineId
        user_data = alertUser or kwargs.get("user")
        self.alert_user = AlertUser(**user_data) if user_data else None
        self.comments = comments
        files_source = alertFiles or kwargs.get("files")
        self.alert_files = (
            [AlertFile(**alert_file) for alert_file in files_source]
            if files_source
            else []
        )
        self.alert_domains = alertDomains
        self.alert_ips = alertIps
        self.alert_processes = alertProcesses
        self.alert_data = {}

    def to_json(self):
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "investigation_id": self.investigation_id,
            "assigned_to": self.assigned_to,
            "severity": self.severity,
            "status": self.status,
            "classification": self.classification,
            "determination": self.determination,
            "investigation_state": self.investigation_state,
            "detection_source": self.detection_source,
            "category": self.category,
            "threat_family_name": self.threat_family_name,
            "title": self.title,
            "description": self.description,
            "alert_creation_time": self.alert_creation_time,
            "first_event_time": self.first_event_time,
            "last_event_time": self.last_event_time,
            "last_update_time": self.last_update_time,
            "resolved_time": self.resolved_time,
            "machine_id": self.machine_id,
            "alert_user": self.alert_user.to_json() if self.alert_user else None,
            "alert_files": [file.to_json() for file in self.alert_files],
            "comments": self.comments,
            "alert_domains": self.alert_domains,
            "alert_ips": self.alert_ips,
            "alert_processes": self.alert_processes,
        }

    def to_enrichment_data(self):
        pass

    def to_table(self):
        return {
            "Alert ID": self.id,
            "Incident ID": self.incident_id,
            "Status": self.status,
            "Severity": self.severity,
            "Title": self.title,
            "Description": self.description,
            "Assigned To": self.assigned_to,
            "Category": self.category,
            "Alert Creation Time": self.alert_creation_time,
            "Last Update Time": self.last_update_time,
        }

    def to_extension(
        self,
        extended: bool = False,
        use_v2_api: bool = False,
    ) -> SingleJson:
        """Convert alert to extension dict."""
        extensions = {
            "incidentId": self.incident_id,
            "investigationId": self.investigation_id,
            "assignedTo": self.assigned_to,
            "status": self.status,
            "classification": self.classification,
            "determination": self.determination,
            "investigationState": self.investigation_state,
            "detectionSource": self.detection_source,
            "category": self.category,
            "threatFamilyName": self.threat_family_name,
            "machineId": self.machine_id,
            "alertUser": (
                json.dumps(self.alert_user.to_json())
                if self.alert_user and use_v2_api
                else (self.alert_user.to_json() if self.alert_user else None)
            ),
            "alertCreationTime": self.alert_creation_time,
            "lastUpdateTime": self.last_update_time,
            "resolvedTime": self.resolved_time,
        }

        if extended:
            extensions["mitreTechniques"] = json.dumps(
                self.raw_data.get("mitreTechniques")
            )
            extensions["comments"] = json.dumps(
                [dict_to_flat(comment) for comment in self.raw_data.get("comments")]
            )

        return extensions

    @staticmethod
    def _safe_convert_to_unix(value: str | None) -> int:
        try:
            return convert_string_to_unix_time(value)
        except Exception:
            return 1

    def get_alert_info(
        self,
        alert_info,
        environment_common,
        device_product_field,
        severity,
        use_v2_api=False,
    ):
        alert_info.environment = environment_common.get_environment(self.raw_data)
        alert_info.display_id = str(uuid.uuid4())
        alert_info.ticket_id = self.id
        alert_info.name = self.title
        alert_info.description = self.description
        alert_info.device_vendor = (
            DEFAULT_VENDOR_NAME if not use_v2_api else PRODUCT_NAME_V2
        )

        if use_v2_api:
            alert_info.device_product = GRAPH_VENDOR
            alert_info.rule_generator = self.category
        else:
            alert_info.device_product = (
                self.raw_data.get(device_product_field) or DEFAULT_PRODUCT_NAME
            )
            alert_info.rule_generator = self.detection_source

        alert_info.source_grouping_identifier = self.incident_id
        alert_info.extensions = self.to_extension(extended=True, use_v2_api=use_v2_api)
        alert_info.priority = severity
        alert_info.start_time = Alert._safe_convert_to_unix(self.first_event_time)
        alert_info.end_time = Alert._safe_convert_to_unix(self.last_event_time)
        alert_info.events = self.to_events() if not use_v2_api else self.to_events_v2()

        return alert_info

    def set_events(self, alert_data):
        self.alert_data = alert_data

    def to_events(self):
        events = []
        events.extend(
            [
                dict_to_flat(self.prepare_device_event(device))
                for device in self.alert_data.get("devices", [])
            ]
        )
        events.extend(
            [
                dict_to_flat(self.prepare_entity_event(entity))
                for entity in self.alert_data.get("entities", [])
            ]
        )
        events.extend(
            [
                dict_to_flat(self.prepare_alert_response_event(data))
                for data in self.alert_data.get("alert_response", [])
            ]
        )

        return events

    def to_events_v2(self) -> list[SingleJson]:
        """Converts Evidences into Google Secops events with proper UI mapping."""
        events = []
        alert_metadata = copy.deepcopy(self.raw_data)
        for evidence in alert_metadata.pop("evidence"):
            evidence["event_class"] = "Evidence"
            evidence.update(alert_metadata)
            formatted_event = dict_to_flat(evidence)
            events.append(formatted_event)

        return events

    def prepare_event_additional_fields(self):
        return {
            "alertCreationTime": self.alert_creation_time,
            "firstEventTime": self.first_event_time,
            "lastEventTime": self.last_event_time,
            "lastUpdateTime": self.last_update_time,
        }

    def prepare_device_event(self, device):
        device["EventName"] = "device"
        device["ProductName"] = DEFAULT_PRODUCT_NAME
        device.update(self.prepare_event_additional_fields())
        return device

    def prepare_entity_event(self, entity):
        entity["EventName"] = entity.get("entityType")
        entity["ProductName"] = DEFAULT_PRODUCT_NAME
        entity.update(self.prepare_event_additional_fields())
        return entity

    def prepare_alert_response_event(self, alert_response):
        alert_response["EventName"] = alert_response.get("detectionSource")
        alert_response["ProductName"] = DEFAULT_PRODUCT_NAME
        alert_response.update(self.prepare_event_additional_fields())
        return alert_response


class Machine(AbstractData):
    def __init__(
        self,
        raw_data,
        id=None,
        computerDnsName=None,
        firstSeen=None,
        lastSeen=None,
        osPlatform=None,
        osVersion=None,
        osProcessor=None,
        version=None,
        lastIpAddress=None,
        lastExternalIpAddress=None,
        agentVersion=None,
        osBuild=None,
        healthStatus=None,
        rbacGroupId=None,
        rbacGroupName=None,
        riskScore=None,
        exposureLevel=None,
        aadDeviceId=None,
        machineTags=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.id = id
        self.computer_dns_name = computerDnsName
        self.first_seen = firstSeen
        self.last_seen = lastSeen
        self.last_seen_unix = convert_string_to_unix_time(lastSeen) if lastSeen else 0
        self.os_platform = osPlatform
        self.os_version = osVersion
        self.os_processor = osProcessor
        self.version = version
        self.last_ip_address = lastIpAddress
        self.last_external_ip_address = lastExternalIpAddress
        self.agent_version = agentVersion
        self.os_build = osBuild
        self.health_status = healthStatus
        self.rbac_group_id = rbacGroupId
        self.rbac_group_name = rbacGroupName
        self.risk_score = riskScore
        self.exposure_level = exposureLevel
        self.aad_device_id = aadDeviceId
        self.machine_tags = machineTags

    def to_json(self):
        return {
            "id": self.id,
            "computer_dns_name": self.computer_dns_name,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "os_platform": self.os_platform,
            "os_version": self.os_version,
            "os_processor": self.os_processor,
            "version": self.version,
            "last_ip_address": self.last_ip_address,
            "last_external_ip_address": self.last_external_ip_address,
            "agent_version": self.agent_version,
            "os_build": self.os_build,
            "health_status": self.health_status,
            "rbac_group_id": self.rbac_group_id,
            "rbac_group_name": self.rbac_group_name,
            "risk_score": self.risk_score,
            "exposure_level": self.exposure_level,
            "aad_device_id": self.aad_device_id,
            "machine_tags": ",".join(self.machine_tags),
        }

    def to_enrichment_data(self):
        enrichment_data = {
            "machine_id": self.id,
            "computer_dns_name": self.computer_dns_name,
            "agent_version": self.agent_version,
            "health_status": self.health_status,
            "risk_score": self.risk_score,
            "exposure_level": self.exposure_level,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "last_ip_address": self.last_ip_address,
            "last_external_ip_address": self.last_external_ip_address,
        }

        if self.risk_score in ["Low", "Medium", "High"]:
            enrichment_data["is_suspicious"] = self.risk_score

        if self.machine_tags:
            enrichment_data["machine_tags"] = ",".join(self.machine_tags)

        if self.os_platform:
            enrichment_data["os_platform"] = self.os_platform

        if self.os_version:
            enrichment_data["os_version"] = self.os_version

        if self.os_processor:
            enrichment_data["os_processor"] = self.os_processor

        if self.version:
            enrichment_data["version"] = self.version

        if self.os_build:
            enrichment_data["os_build"] = self.os_build

        if self.rbac_group_id:
            enrichment_data["rbac_group_id"] = self.rbac_group_id

        if self.rbac_group_name:
            enrichment_data["rbac_group_name"] = self.rbac_group_name

        if self.aad_device_id:
            enrichment_data["aad_device_id"] = self.aad_device_id

        return enrichment_data

    def to_table(self):
        return {
            "Machine ID": self.id,
            "Machine DNS Name": self.computer_dns_name,
            "Risk Score": self.risk_score,
            "Exposure Level": self.exposure_level,
            "Health Status": self.health_status,
            "First Seen": self.first_seen,
            "Last Seen": self.last_seen,
            "Last Seen Lan IP Address": self.last_ip_address,
            "Last Seen External IP Address": self.last_external_ip_address,
            "OS Platform": self.os_platform,
            "OS Version": self.os_version,
            "OS Build": self.os_build,
            "DATP Agent Version": self.agent_version,
        }


class User(AbstractData):
    def __init__(
        self,
        raw_data,
        id=None,
        accountName=None,
        accountDomain=None,
        accountSid=None,
        firstSeen=None,
        lastSeen=None,
        mostPrevalentMachineId=None,
        leastPrevalentMachineId=None,
        logonTypes=None,
        logOnMachinesCount=None,
        isDomainAdmin=None,
        isOnlyNetworkUser=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.id = id
        self.account_name = accountName
        self.account_domain = accountDomain
        self.account_sid = accountSid
        self.first_seen = firstSeen
        self.last_seen = lastSeen
        self.most_prevalent_machine_id = mostPrevalentMachineId
        self.least_prevalent_machine_id = leastPrevalentMachineId
        self.logon_types = logonTypes
        self.log_on_machines_count = logOnMachinesCount
        self.is_domain_admin = isDomainAdmin
        self.is_only_network_user = isOnlyNetworkUser

    def to_json(self):
        return {
            "id": self.id,
            "account_name": self.account_name,
            "account_domain": self.account_domain,
            "account_sid": self.account_sid,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "most_prevalent_machine_id": self.most_prevalent_machine_id,
            "least_prevalent_machine_id": self.least_prevalent_machine_id,
            "logon_types": self.logon_types,
            "log_on_machines_count": self.log_on_machines_count,
            "is_domain_admin": self.is_domain_admin,
            "is_only_network_user": self.is_only_network_user,
        }

    def to_enrichment_data(self):
        pass

    def to_table(self):
        return {
            "ID": self.id,
            "First Seen": self.first_seen,
            "Last Seen": self.last_seen,
            "Most Prevalent Machine ID": self.most_prevalent_machine_id,
            "Least Prevalent Machine ID": self.least_prevalent_machine_id,
            "Logon Types": self.logon_types,
            "Log On Machines Count": self.log_on_machines_count,
            "Is Domain Admin": self.is_domain_admin,
            "Is Only Network User": self.is_only_network_user,
        }


class File(AbstractData):
    def __init__(
        self,
        raw_data,
        sha1=None,
        sha256=None,
        md5=None,
        globalPrevalence=None,
        globalFirstObserved=None,
        globalLastObserved=None,
        size=None,
        fileType=None,
        isPeFile=None,
        filePublisher=None,
        fileProductName=None,
        signer=None,
        issuer=None,
        signerHash=None,
        isValidCertificate=None,
        orgPrevalence=None,
        orgFirstSeen=None,
        orgLastSeen=None,
        topFileNames=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.sha1 = sha1
        self.sha256 = sha256
        self.md5 = md5
        self.global_prevalence = globalPrevalence
        self.global_first_observed = globalFirstObserved
        self.global_last_observed = globalLastObserved
        self.size = size
        self.file_type = fileType
        self.is_pe_file = isPeFile
        self.file_publisher = filePublisher
        self.file_product_name = fileProductName
        self.signer = signer
        self.issuer = issuer
        self.signer_hash = signerHash
        self.is_valid_certificate = isValidCertificate
        self.org_prevalence = orgPrevalence
        self.org_first_seen = orgFirstSeen
        self.org_last_seen = orgLastSeen
        self.top_file_names = topFileNames

    def to_json(self):
        return {
            "sha1": self.sha1,
            "sha256": self.sha256,
            "md5": self.md5,
            "global_prevalence": self.global_prevalence,
            "global_first_observed": self.global_first_observed,
            "global_last_observed": self.global_last_observed,
            "size": self.size,
            "file_type": self.file_type,
            "is_pe_file": self.is_pe_file,
            "file_publisher": self.file_publisher,
            "file_product_name": self.file_product_name,
            "signer": self.signer,
            "issuer": self.issuer,
            "signer_hash": self.signer_hash,
            "is_valid_certificate": self.is_valid_certificate,
            "org_prevalence": self.org_prevalence,
            "org_first_seen": self.org_first_seen,
            "org_last_seen": self.org_last_seen,
            "top_file_names": self.top_file_names,
        }

    def to_enrichment_data(self):
        return {
            "sha1": self.sha1,
            "sha256": self.sha256,
            "md5": self.md5,
            "global_prevalence": self.global_prevalence,
            "global_first_observed": self.global_first_observed,
            "global_last_observed": self.global_last_observed,
            "size": self.size,
            "file_type": self.file_type,
            "is_pe_file": self.is_pe_file,
            "file_publisher": self.file_publisher,
            "file_product_name": self.file_product_name,
            "signer": self.signer,
            "issuer": self.issuer,
            "signer_hash": self.signer_hash,
            "is_valid_certificate": self.is_valid_certificate,
            "org_prevalence": self.org_prevalence,
            "org_first_seen": self.org_first_seen,
            "org_last_seen": self.org_last_seen,
            "top_file_names": self.convert_list_to_comma_string(self.top_file_names),
        }

    def to_table(self):
        return {
            "SHA1": self.sha1,
            "SHA256": self.sha256,
            "MD5": self.md5,
            "Top File Names": self.convert_list_to_comma_string(self.top_file_names),
            "File Type": self.file_type,
            "Is PE file": self.is_pe_file,
            "Organization Prevalence": self.org_prevalence,
            "Organization First Seen": self.org_first_seen,
            "Organization Last Seen": self.org_last_seen,
            "Global Prevalence": self.global_prevalence,
            "Global First Observed": self.global_first_observed,
            "Global Last Observed": self.global_last_observed,
            "Size": self.size,
            "File Published": self.file_publisher,
            "File Product Name": self.file_product_name,
            "Is Valid Certificate": self.is_valid_certificate,
            "Signer": self.signer,
            "Signer Hash": self.signer_hash,
            "Issuer": self.issuer,
        }


class Detection(AbstractData):
    def __init__(
        self,
        raw_data,
        Actor=None,
        AlertId=None,
        AlertPart=None,
        AlertTime=None,
        AlertTitle=None,
        Category=None,
        CloudCreatedMachineTags=None,
        CommandLine=None,
        ComputerDnsName=None,
        CreatorIocName=None,
        CreatorIocValue=None,
        Description=None,
        DeviceCreatedMachineTags=None,
        DeviceID=None,
        ExternalId=None,
        FileHash=None,
        FileName=None,
        FilePath=None,
        FullId=None,
        IncidentLinkToWDATP=None,
        InternalIPv4List=None,
        InternalIPv6List=None,
        IoaDefinitionId=None,
        IocName=None,
        IocUniqueId=None,
        IocValue=None,
        IpAddress=None,
        LastProcessedTimeUtc=None,
        LinkToWDATP=None,
        LogOnUsers=None,
        MachineDomain=None,
        MachineGroup=None,
        MachineName=None,
        Md5=None,
        RemediationAction=None,
        RemediationIsSuccess=None,
        ReportID=None,
        Severity=None,
        Sha1=None,
        Sha256=None,
        Source=None,
        ThreatCategory=None,
        ThreatFamily=None,
        ThreatName=None,
        Url=None,
        UserDomain=None,
        UserName=None,
        WasExecutingWhileDetected=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.actor = Actor
        self.alert_id = AlertId
        self.alert_part = AlertPart
        self.alert_time = AlertTime
        self.alert_title = AlertTitle
        self.category = Category
        self.cloud_created_machine_tags = CloudCreatedMachineTags
        self.command_line = CommandLine
        self.computer_dns_name = ComputerDnsName
        self.creator_ioc_name = CreatorIocName
        self.creator_ioc_value = CreatorIocValue
        self.description = Description
        self.device_created_machine_tags = DeviceCreatedMachineTags
        self.device_id = DeviceID
        self.external_id = ExternalId
        self.file_hash = FileHash
        self.file_name = FileName
        self.file_path = FilePath
        self.full_id = FullId
        self.incident_link_to_wdatp = IncidentLinkToWDATP
        self.internal_ipv4_list = InternalIPv4List
        self.internal_ipv6_list = InternalIPv6List
        self.ioa_definition_id = IoaDefinitionId
        self.ioc_name = IocName
        self.ioc_unique_id = IocUniqueId
        self.ioc_value = IocValue
        self.ip_address = IpAddress
        self.last_processed_time_utc = LastProcessedTimeUtc
        self.link_to_wdatp = LinkToWDATP
        self.log_on_users = LogOnUsers
        self.machine_domain = MachineDomain
        self.machine_group = MachineGroup
        self.machine_name = MachineName
        self.md5 = Md5
        self.remediation_action = RemediationAction
        self.remediation_is_success = RemediationIsSuccess
        self.report_id = ReportID
        self.severity = Severity
        self.sha1 = Sha1
        self.sha256 = Sha256
        self.source = Source
        self.threat_category = ThreatCategory
        self.threat_family = ThreatFamily
        self.threat_name = ThreatName
        self.url = Url
        self.user_domain = UserDomain
        self.user_name = UserName
        self.was_executing_while_detected = WasExecutingWhileDetected

    def to_json(self):
        return {
            "actor": self.actor,
            "alert_id": self.alert_id,
            "alert_part": self.alert_part,
            "alert_time": self.alert_time,
            "alert_title": self.alert_title,
            "category": self.category,
            "cloud_created_machine_tags": self.cloud_created_machine_tags,
            "command_line": self.command_line,
            "computer_dns_name": self.computer_dns_name,
            "creator_ioc_name": self.creator_ioc_name,
            "creator_ioc_value": self.creator_ioc_value,
            "description": self.description,
            "device_created_machine_tags": self.device_created_machine_tags,
            "device_id": self.device_id,
            "external_id": self.external_id,
            "file_hash": self.file_hash,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "full_id": self.full_id,
            "incident_link_to_wdatp": self.incident_link_to_wdatp,
            "internal_ipv4_list": self.internal_ipv4_list,
            "internal_ipv6_list": self.internal_ipv6_list,
            "ioa_definition_id": self.ioa_definition_id,
            "ioc_name": self.ioc_name,
            "ioc_unique_id": self.ioc_unique_id,
            "ioc_value": self.ioc_value,
            "ip_address": self.ip_address,
            "last_processed_time_utc": self.last_processed_time_utc,
            "link_to_wdatp": self.link_to_wdatp,
            "log_on_users": self.log_on_users,
            "machine_domain": self.machine_domain,
            "machine_group": self.machine_group,
            "machine_name": self.machine_name,
            "md5": self.md5,
            "remediation_action": self.remediation_action,
            "remediation_is_success": self.remediation_is_success,
            "report_id": self.report_id,
            "severity": self.severity,
            "sha1": self.sha1,
            "sha256": self.sha256,
            "source": self.source,
            "threat_category": self.threat_category,
            "threat_family": self.threat_family,
            "threat_name": self.threat_name,
            "url": self.url,
            "user_domain": self.user_domain,
            "user_name": self.user_name,
            "was_executing_while_detected": self.was_executing_while_detected,
        }

    def to_enrichment_data(self):
        pass


class QueryResult(AbstractData):
    def __init__(self, raw_data, **kwargs):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data.get("Results")

    def to_enrichment_data(self):
        pass

    def to_csv(self):
        return self.to_json()

    def to_table(self):
        return self.to_csv()


class RelatedFileInfo(AbstractData):
    def __init__(self, fileIdentifier, fileIdentifierType, **kwargs):
        self.file_identifier = fileIdentifier
        self.file_identifier_type = fileIdentifierType

    def to_json(self):
        return {
            "file_identifier": self.file_identifier,
            "file_identifier_type": self.file_identifier_type,
        }

    def to_enrichment_data(self):
        pass


class MachineTask(AbstractData):
    def __init__(
        self,
        raw_data,
        id=None,
        type=None,
        requestor=None,
        requestorComment=None,
        status=None,
        machineId=None,
        creationDateTimeUtc=None,
        lastUpdateDateTimeUtc=None,
        cancellationRequestor=None,
        cancellationComment=None,
        cancellationDateTimeUtc=None,
        errorHResult=None,
        scope=None,
        relatedFileInfo=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.id = id
        self.type = type
        self.requestor = requestor
        self.requestor_comment = requestorComment
        self.status = status
        self.machine_id = machineId
        self.creation_date_time_utc = creationDateTimeUtc
        self.last_update_date_time_utc = lastUpdateDateTimeUtc
        self.cancellation_requestor = cancellationRequestor
        self.cancellation_comment = cancellationComment
        self.cancellation_date_time_utc = cancellationDateTimeUtc
        self.error_h_result = errorHResult
        self.scope = scope
        self.related_file_info = (
            RelatedFileInfo(**relatedFileInfo) if relatedFileInfo else relatedFileInfo
        )

    @property
    def is_succeeded(self):
        return self.status == "Succeeded"

    @property
    def is_pending(self):
        return self.status == "Pending"

    @property
    def is_in_progress(self):
        return self.status == "InProgress"

    @property
    def is_timeout(self):
        return self.status == "TimeOut"

    @property
    def is_failed(self):
        return self.status == "Failed"

    @property
    def is_cancelled(self):
        return self.status == "Cancelled"

    @property
    def is_finished_and_not_succeeded(self):
        return any([self.is_failed, self.is_timeout, self.is_cancelled])

    def to_json(self):
        return {
            "id": self.id,
            "type": self.type,
            "requestor": self.requestor,
            "requestor_comment": self.requestor_comment,
            "status": self.status,
            "machine_id": self.machine_id,
            "creation_date_time_utc": self.creation_date_time_utc,
            "last_update_date_time_utc": self.last_update_date_time_utc,
            "cancellation_requestor": self.cancellation_requestor,
            "cancellation_comment": self.cancellation_comment,
            "cancellation_date_time_utc": self.cancellation_date_time_utc,
            "error_h_result": self.error_h_result,
            "scope": self.scope,
            "related_file_info": (
                self.related_file_info.to_json()
                if self.related_file_info
                else self.related_file_info
            ),
        }

    def to_table(self):
        return {"Task ID": self.id, "Status": self.status}

    def to_enrichment_data(self):
        pass

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash((self.id,))


class Vulnerability(AbstractData):
    """Vulnerability Data Model."""
    def __init__(
        self,
        raw_data: Any,
        vulnerability_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
        severity: str | None = None,
        cvss_v3: float | None = None,
        exposed_machines: int | None = None,
        published_on: str | None = None,
        updated_on: str | None = None,
        first_detected: str | None = None,
        patch_first_available: str | None = None,
        public_exploit: str | None = None,
        exploit_types: list[str] | None = None,
        exploit_uris: list[str] | None = None,
        cve_supportability: str | None = None,
        tags: list[str] | None = None,
        epss: float | None = None,
        status: str | None = None,
        **kwargs: Any
    ):
        """Represents a vulnerability and its associated exploit intelligence.

        Args:
            raw_data (SingleJson): The original raw data dictionary.
            vulnerability_id (str): The vulnerability ID.
            name (str): The name of the vulnerability.
            description (str): The description of the vulnerability.
            severity (str): The severity of the vulnerability.
            cvss_v3 (float): The CVSS V3 score.
            exposed_machines (int): The number of exposed machines.
            published_on (str): The publication date.
            updated_on (str): The update date.
            first_detected (str): The date it was first detected.
            patch_first_available (str): The date the patch first became available.
            public_exploit (str): The public exploit information.
            exploit_verified (bool): Whether the exploit is verified.
            exploit_in_kit (bool): Whether the exploit is in a kit.
            exploit_types (list): The types of the exploit.
            exploit_uris (list): The URIs of the exploit.
            cve_supportability (str): The CVE supportability information.
            tags (list): The tags.
            epss (float): The EPSS score.
            status (str): The status.
            **kwargs: Additional keyword arguments.
        """
        self.raw_data = raw_data
        self.vulnerability_id = (
            vulnerability_id or kwargs.get("id") or kwargs.get("vulnerabilityId")
        )
        self.name = name or kwargs.get("name")
        self.description = description or kwargs.get("description")
        self.severity = severity or kwargs.get("severity")
        self.cvss_v3 = cvss_v3 or kwargs.get("cvssV3")
        self.exposed_machines = exposed_machines or kwargs.get("exposedMachines")
        self.published_on = published_on or kwargs.get("publishedOn")
        self.updated_on = updated_on or kwargs.get("updatedOn")
        self.first_detected = first_detected or kwargs.get("firstDetected")
        self.patch_first_available = patch_first_available or kwargs.get(
            "patchFirstAvailable"
        )
        self.public_exploit = public_exploit or kwargs.get("publicExploit")
        self.exploit_types = exploit_types or kwargs.get("exploitTypes")
        self.exploit_uris = exploit_uris or kwargs.get("exploitUris")
        self.cve_supportability = cve_supportability or kwargs.get("cveSupportability")
        self.tags = tags or kwargs.get("tags")
        self.epss = epss or kwargs.get("epss")
        self.status = status or kwargs.get("status")
        self.is_threat_active = bool(kwargs.get("isThreatActive"))
        self.has_exploit = bool(kwargs.get("publicExploit"))
        self.exploit_verified = bool(kwargs.get("exploitVerified"))
        self.exploit_in_kit = bool(kwargs.get("exploitInKit"))

    def to_json(self) -> Any:
        """Returns the original raw data dictionary."""
        return self.raw_data

    def to_table(self) -> SingleJson:
        """Returns a dictionary representation suitable for tables."""
        return {
            "ID": self.vulnerability_id,
            "Name": self.name,
            "Description": self.description,
            "Severity": self.severity,
            "CVSS V3": self.cvss_v3,
            "Exposed Machines": self.exposed_machines,
            "Published On": self.published_on,
            "Updated On": self.updated_on,
            "First Detected": self.first_detected,
            "Public Exploit": self.public_exploit,
            "Exploit Verified": self.exploit_verified,
            "Status": self.status,
        }

    def to_enrichment_data(self) -> Any:
        pass


class Recommendation(AbstractData):
    def __init__(self, raw_data, **kwargs):
        self.raw_data: dict = raw_data
        self.id: str = kwargs.get("id")
        self.product_name: str = kwargs.get("productName")
        self.recommendation_name: str = kwargs.get("recommendationName")
        self.weaknesses: list[str] = kwargs.get("weaknesses")
        self.vendor: str = kwargs.get("vendor")
        self.recommended_version: str = kwargs.get("recommendedVersion")
        self.recommended_vendor: str = kwargs.get("recommendedVendor")
        self.recommended_program: str = kwargs.get("recommendedProgram")
        self.recommendation_category: str = kwargs.get("recommendationCategory")
        self.sub_category: str = kwargs.get("subCategory")
        self.severity_score: int = kwargs.get("severityScore")
        self.public_exploit: bool = kwargs.get("publicExploit")
        self.active_alert: bool = kwargs.get("activeAlert")
        self.associated_threats: list[str] = kwargs.get("associatedThreats")
        self.remediation_type: str = kwargs.get("remediationType")
        self.status: str = kwargs.get("status")
        self.config_score_impact: int = kwargs.get("configScoreImpact")
        self.exposure_impact: int = kwargs.get("exposureImpact")
        self.total_machine_count: int = kwargs.get("totalMachineCount")
        self.exposed_machines_count: int = kwargs.get("exposedMachinesCount")
        self.non_productivity_impacted_assets: int = kwargs.get(
            "nonProductivityImpactedAssets"
        )
        self.related_component: str = kwargs.get("relatedComponent")
        self.has_unpatchable_cve: bool = kwargs.get("hasUnpatchableCve")
        self.tags: list[str] = kwargs.get("tags")
        self.exposed_critical_devices: int = kwargs.get("exposedCriticalDevices")

    def to_json(self):
        return {
            "id": self.id,
            "productName": self.product_name,
            "recommendationName": self.recommendation_name,
            "weaknesses": self.weaknesses,
            "vendor": self.vendor,
            "recommendedVersion": self.recommended_version,
            "recommendedVendor": self.recommended_vendor,
            "recommendedProgram": self.recommended_program,
            "recommendationCategory": self.recommendation_category,
            "subCategory": self.sub_category,
            "severityScore": self.severity_score,
            "publicExploit": self.public_exploit,
            "activeAlert": self.active_alert,
            "associatedThreats": self.associated_threats,
            "remediationType": self.remediation_type,
            "status": self.status,
            "configScoreImpact": self.config_score_impact,
            "exposureImpact": self.exposure_impact,
            "totalMachineCount": self.total_machine_count,
            "exposedMachinesCount": self.exposed_machines_count,
            "nonProductivityImpactedAssets": self.non_productivity_impacted_assets,
            "relatedComponent": self.related_component,
            "hasUnpatchableCve": self.has_unpatchable_cve,
            "tags": self.tags,
            "exposedCriticalDevices": self.exposed_critical_devices,
        }

    def to_enrichment_data(self):
        pass
