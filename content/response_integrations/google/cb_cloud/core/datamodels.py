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
from TIPCommon.transformation import dict_to_flat, add_prefix_to_dict, flat_dict_to_csv
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
import uuid
from .constants import (
    EMPTY_LEGACY_ID,
    WATCHLIST_TYPE,
    ALERT_TYPES_WITHOUT_ENRICHED_EVENTS,
    SIEMPLIFY_ALERT_NAME,
    PROVIDER_NAME,
    DEFAULT_VENDOR,
    SIEMPLIFY_RULE_GENERATOR,
    CHARACTERS_LIMIT,
)
from .utils import transform_template_string


ENRICHMENT_PREFIX = "CB_CLOUD"


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_flat(self):
        return dict_to_flat(self.to_json())

    def to_table(self):
        return [self.to_csv()]

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def is_empty(self):
        return not bool(self.raw_data)


class Device(BaseModel):
    def __init__(
        self,
        raw_data,
        av_engine=None,
        av_status=None,
        id=None,
        av_last_scan_time=None,
        email=None,
        first_name=None,
        last_name=None,
        last_contact_time=None,
        last_device_policy_changed_time=None,
        last_external_ip_address=None,
        last_internal_ip_address=None,
        last_location=None,
        name=None,
        organization_id=None,
        organization_name=None,
        os=None,
        os_version=None,
        passive_mode=None,
        policy_id=None,
        policy_name=None,
        policy_override=None,
        quarantined=None,
        scan_status=None,
        sensor_out_of_date=None,
        sensor_states=None,
        sensor_version=None,
        status=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.av_engine = av_engine
        self.av_status = av_status
        self.id = id
        self.av_last_scan_time = av_last_scan_time
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.last_contact_time = last_contact_time
        self.last_device_policy_changed_time = last_device_policy_changed_time
        self.last_external_ip_address = last_external_ip_address
        self.last_internal_ip_address = last_internal_ip_address
        self.last_location = last_location
        self.organization_id = organization_id
        self.name = name
        self.organization_name = organization_name
        self.os = os
        self.os_version = os_version
        self.passive_mode = passive_mode
        self.policy_id = policy_id
        self.policy_name = policy_name
        self.policy_override = policy_override
        self.quarantined = quarantined
        self.scan_status = scan_status
        self.sensor_out_of_date = sensor_out_of_date
        self.sensor_states = sensor_states
        self.sensor_version = sensor_version
        self.status = status

    def as_enrichment_data(self):
        enrichment_data = self._get_enrichment_data()

        return add_prefix_to_dict(dict_to_flat(enrichment_data), ENRICHMENT_PREFIX)

    def _get_enrichment_data(self):
        enrichment_data = {
            "antivirus_last_scan_time": self.av_last_scan_time,
            "owner_email": self.email,
            "owner_first_name": self.first_name,
            "owner_last_name": self.last_name,
            "last_device_policy_changed_time": self.last_device_policy_changed_time,
            "device_os": self.os,
            "device_os_version": self.os_version,
            "scan_status": self.scan_status,
        }

        # Clear out None values
        enrichment_data = {k: v for k, v in enrichment_data.items() if v is not None}

        if self.policy_override:
            enrichment_data.update({"device_policy_override": self.policy_override})

        enrichment_data.update(
            {
                "device_id": self.id,
                "antivirus_status": ", ".join(self.av_status) if self.av_status else "",
                "last_contact_time": self.last_contact_time,
                "last_external_ip_address": self.last_external_ip_address,
                "last_internal_ip_address": self.last_internal_ip_address,
                "last_location": self.last_location,
                "full_device_name": self.name,
                "organization_id": self.organization_id,
                "organization_name": self.organization_name,
                "passive_mode": self.passive_mode,
                "device_policy_id": self.policy_id,
                "device_policy_name": self.policy_name,
                "quarantined": self.quarantined,
                "sensor_out_of_date": self.sensor_out_of_date,
                "sensor_states": (
                    ", ".join(self.sensor_states) if self.sensor_states else ""
                ),
                "sensor_version": self.sensor_version,
                "device_status": self.status,
            }
        )

        return enrichment_data

    def to_csv(self):
        data = {
            "antivirus_last_scan_time": self.av_last_scan_time,
            "owner_email": self.email,
            "owner_first_name": self.first_name,
            "owner_last_name": self.last_name,
            "last_device_policy_changed_time": self.last_device_policy_changed_time,
            "device_os": self.os,
            "device_os_version": self.os_version,
            "scan_status": self.scan_status,
            "device_id": self.id,
            "antivirus_status": "; ".join(self.av_status) if self.av_status else "",
            "last_contact_time": self.last_contact_time,
            "last_external_ip_address": self.last_external_ip_address,
            "last_internal_ip_address": self.last_internal_ip_address,
            "last_location": self.last_location,
            "full_device_name": self.name,
            "organization_id": self.organization_id,
            "organization_name": self.organization_name,
            "passive_mode": self.passive_mode,
            "device_policy_id": self.policy_id,
            "device_policy_name": self.policy_name,
            "quarantined": self.quarantined,
            "sensor_out_of_date": self.sensor_out_of_date,
            "sensor_states": (
                "; ".join(self.sensor_states) if self.sensor_states else ""
            ),
            "sensor_version": self.sensor_version,
            "device_status": self.status,
        }

        if self.policy_override:
            data.update({"device_policy_override": self.policy_override})

        return flat_dict_to_csv(data)


class Alert(BaseModel):
    def __init__(
        self,
        raw_data,
        alert_type=None,
        alert_id=None,
        org_key=None,
        backend_timestamp=None,
        backend_update_timestamp=None,
        first_event_timestamp=None,
        last_event_timestamp=None,
        threat_id=None,
        severity=None,
        device=None,
        reason=None,
        process_reputation=None,
        workflow=None,
        policy_applied=None,
        watchlists_names=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.type = alert_type
        self.id = alert_id
        self.legacy_alert_id = str(self.id) or EMPTY_LEGACY_ID
        self.org_key = org_key
        self.create_time = backend_timestamp
        self.last_update_time = backend_update_timestamp
        self.first_event_time = first_event_timestamp
        self.last_event_time = last_event_timestamp
        self.threat_id = threat_id
        self.severity = severity
        self.device_id = device.device_id
        self.device_os = device.device_os
        self.device_os_version = device.device_os_version
        self.device_name = device.device_name
        self.device_username = device.device_username
        self.policy_id = device.device_policy_id
        self.policy_name = device.device_policy
        self.target_value = device.device_target_value
        self.reason = reason
        self.threat_cause_reputation = process_reputation or "N/A"
        self.workflow = workflow
        self.policy_applied = policy_applied
        self.watchlists_names = watchlists_names
        self.has_events = self.type not in ALERT_TYPES_WITHOUT_ENRICHED_EVENTS

        try:
            self.create_time_ms = convert_string_to_unix_time(backend_timestamp)
        except Exception:
            self.create_time_ms = 1

        try:
            self.last_update_time_ms = convert_string_to_unix_time(
                backend_update_timestamp
            )
        except Exception:
            self.last_update_time_ms = 1

        try:
            self.first_event_time_ms = convert_string_to_unix_time(
                first_event_timestamp
            )
        except Exception:
            self.first_event_time_ms = 1

        try:
            self.last_event_time_ms = convert_string_to_unix_time(last_event_timestamp)
        except Exception:
            self.last_event_time_ms = 1

    def is_watchlist_type(self):
        return self.type.lower() == WATCHLIST_TYPE

    def as_event(self):
        event_data = self.raw_data
        event_data["event_type"] = self.raw_data.get("type")
        return dict_to_flat(self.raw_data)

    def as_json(self):
        return self.raw_data

    @property
    def priority(self):
        if self.severity < 4:
            return -1

        elif self.severity < 6:
            return 40

        elif self.severity < 8:
            return 60

        elif self.severity < 10:
            return 80

        return 100

    @property
    def id_for_logging(self):
        return self.id_with_legacy_id

    @property
    def id_with_legacy_id(self):
        return f"{self.id}_{self.legacy_alert_id}"

    def as_extension(self):
        return dict_to_flat(
            {
                "id": self.id,
                "legacy_alert_id": self.legacy_alert_id,
                "threat_id": self.threat_id,
                "policy_id": self.policy_id,
                "device_policy_id": self.policy_id,
                "policy_name": self.policy_name,
                "device_policy": self.policy_name,
                "target_value": self.target_value,
                "device_target_value": self.target_value,
                "workflow": self.workflow,
                "policy_applied": self.policy_applied,
                "type": self.type,
                "severity": self.severity,
                "reason": self.reason,
                "threat_cause_reputation": self.threat_cause_reputation,
                "process_reputation": self.threat_cause_reputation,
            }
        )

    def pass_watchlist_filter(self, watchlist_name_filter):
        if not self.is_watchlist_type():
            return True

        if not watchlist_name_filter:
            return True
        return bool(
            [
                watchlist_name
                for watchlist_name in self.watchlists_names
                if watchlist_name in watchlist_name_filter
            ]
        )

    def to_alert_info(
        self,
        environment_common,
        alert_name_field_name,
        rule_generator_field_name,
        is_tracking=False,
        alert_name_template=None,
        rule_generator_template=None,
    ):
        alert_info = AlertInfo()
        alert_info.start_time = self.create_time_ms
        alert_info.end_time = self.last_update_time_ms
        alert_info.ticket_id = str(uuid.uuid4())
        alert_info.display_id = (
            str(uuid.uuid4())
            if is_tracking
            else str(uuid.uuid5(uuid.NAMESPACE_OID, self.id))
        )
        alert_info.name = self.get_field_value(
            alert_name_template,
            self.raw_data,
            SIEMPLIFY_ALERT_NAME.format(getattr(self, alert_name_field_name)),
            CHARACTERS_LIMIT,
        )
        alert_info.rule_generator = self.get_field_value(
            rule_generator_template,
            self.raw_data,
            SIEMPLIFY_RULE_GENERATOR.format(getattr(self, rule_generator_field_name)),
            CHARACTERS_LIMIT,
        )
        alert_info.priority = self.priority
        alert_info.description = self.reason
        alert_info.device_product = PROVIDER_NAME
        alert_info.device_vendor = DEFAULT_VENDOR
        alert_info.environment = environment_common.get_environment(self.as_json())
        alert_info.source_grouping_identifier = self.id
        alert_info.extensions.update(self.as_extension())

        return alert_info

    @staticmethod
    def get_field_value(template, data, default_value, characters_limit=None):
        value = transform_template_string(template, data) if template else default_value
        return (
            value[:characters_limit] if characters_limit else value
        ) or default_value


class AlertDevice(BaseModel):
    def __init__(
        self,
        raw_data,
        device_id=None,
        device_os=None,
        device_os_version=None,
        device_name=None,
        device_username=None,
        device_policy_id=None,
        device_policy=None,
        device_target_value=None,
    ):
        super().__init__(raw_data)
        self.device_id = device_id
        self.device_os = device_os
        self.device_os_version = device_os_version
        self.device_name = device_name
        self.device_username = device_username
        self.device_policy_id = device_policy_id
        self.device_policy = device_policy
        self.device_target_value = device_target_value


class EnrichedEvent:
    """
    Represents CB Cloud event
    """

    def __init__(
        self,
        raw_data,
        event_id=None,
        backend_timestamp="1970-01-01T00:00:01.661Z",
        observation_id=None,
        **kwargs,
    ):
        self.raw_data = raw_data
        self.id = event_id
        self.backend_timestamp = backend_timestamp
        self.observation_id = observation_id

    def as_event(self):
        return dict_to_flat(self.raw_data)

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)


class Results:
    def __init__(
        self,
        raw_data,
        alert_category=None,
        alert_id=None,
        device_external_ip=None,
        device_group_id=None,
        device_id=None,
        device_internal_ip=None,
        device_location=None,
        device_name=None,
        device_os=None,
        device_os_version=None,
        device_policy=None,
        event_threat_score=None,
        parent_effective_reputation=None,
        parent_guid=None,
        parent_hash=None,
        parent_name=None,
        parent_pid=None,
        parent_reputation=None,
        process_cmdline=None,
        process_effective_reputation=None,
        process_guid=None,
        process_hash=None,
        process_name=None,
        process_pid=None,
        process_reputation=None,
        process_sha256=None,
        process_start_time=None,
        process_username=None,
        watchlist_hit=None,
        **kwargs,
    ):
        self.raw_data = raw_data
        self.alert_category = alert_category if alert_category else []
        self.alert_id = alert_id if alert_id else []
        self.device_external_ip = device_external_ip
        self.device_group_id = device_group_id
        self.device_id = device_id
        self.device_internal_ip = device_internal_ip
        self.device_location = device_location
        self.device_name = device_name
        self.device_os = device_os
        self.device_os_version = device_os_version
        self.device_policy = device_policy
        self.event_threat_score = event_threat_score
        self.parent_effective_reputation = parent_effective_reputation
        self.parent_guid = parent_guid
        self.parent_hash = parent_hash if parent_hash else []
        self.parent_name = parent_name
        self.parent_pid = parent_pid
        self.parent_reputation = parent_reputation
        self.process_cmdline = process_cmdline if process_cmdline else []
        self.process_effective_reputation = process_effective_reputation
        self.process_guid = process_guid
        self.process_hash = process_hash if process_hash else []
        self.process_name = process_name
        self.process_pid = process_pid
        self.process_reputation = process_reputation
        self.process_sha256 = process_sha256
        self.process_start_time = process_start_time
        self.process_username = process_username if process_username else []
        self.watchlist_hit = watchlist_hit if watchlist_hit else []

    def to_csv(self):
        return {
            "alert_category": "; ".join(self.alert_category),
            "Alert_id": "; ".join(self.alert_id),
            "device_external_ip": self.device_external_ip,
            "device_group_id": self.device_group_id,
            "device_id": self.device_id,
            "device_internal_ip": self.device_internal_ip,
            "device_location": self.device_location,
            "device_name": self.device_name,
            "device_os": self.device_os,
            "device_os_version": self.device_os_version,
            "device_policy": self.device_policy,
            "event_threat_score": self.event_threat_score,
            "parent_effective_reputation": self.parent_effective_reputation,
            "parent_guid": self.parent_guid,
            "Parent_hash": "; ".join(self.parent_hash),
            "parent_name": self.parent_name,
            "parent_pid": self.parent_pid,
            "Parent_reputation": self.parent_reputation,
            "process_cmdline": "; ".join(self.process_cmdline),
            "process_effective_reputation": self.process_effective_reputation,
            "process_guid": self.process_guid,
            "Process_hash": "; ".join(self.process_hash),
            "Process_name": self.process_name,
            "process_pid": "; ".join(str(pid) for pid in self.process_pid),
            "process_reputation": self.process_reputation,
            "Process_sha256": self.process_sha256,
            "process_start_time": self.process_start_time,
            "process_username": "; ".join(self.process_username),
            "watchlist_hit": "; ".join(self.watchlist_hit),
        }


class Event(BaseModel):
    def __init__(self, raw_data, results=None, process_guids=None, **kwargs):
        super().__init__(raw_data)
        self.results = results
        self.process_guids = process_guids if process_guids else []


class DetailedEvent(BaseModel):
    def __init__(
        self,
        raw_data,
        results=None,
        num_found=None,
        num_available=None,
        approximate_unaggregated=None,
        num_aggregated=None,
        contacted=None,
        completed=None,
    ):
        super().__init__(raw_data)
        self.results = results
        self.num_found = num_found
        self.num_available = num_available
        self.approximate_unaggregated = approximate_unaggregated
        self.num_aggregated = num_aggregated
        self.contacted = contacted
        self.completed = completed

    def get_len_of_alert_ids(self):
        alert_ids = []
        for result in self.results:
            alert_ids.extend(result.alert_id)

        return len(alert_ids)

    def get_alert_categories(self):
        alert_categories = []
        for result in self.results:
            alert_categories.extend(result.alert_category)

        return set(alert_categories)

    def to_insight(self, entity_identifier=None):
        insight_content = f"<p><span>Vmware CB Cloud process search results for {entity_identifier} </span> <br/> <br/>"
        insight_content += (
            f"<strong>Alert categories associated with {entity_identifier}: "
            f"</strong>{', '.join(self.get_alert_categories())}<br />"
        )
        insight_content += (
            f"<strong>Alert IDs associated with processes fetched for {entity_identifier}: "
            f"</strong>{self.get_len_of_alert_ids()}</p>"
        )

        return insight_content


class OverriddenReputation(BaseModel):
    def __init__(
        self,
        raw_data,
        id=None,
        created_by=None,
        create_time=None,
        override_list=None,
        override_type=None,
        description=None,
        source=None,
        source_ref=None,
    ):
        super().__init__(raw_data)
        self.id = id
        self.created_by = created_by
        self.create_time = create_time
        self.override_list = override_list
        self.override_type = override_type
        self.description = description
        self.source = source
        self.source_ref = source_ref

    def to_csv(self):
        return {
            "ID": self.id,
            "Override List": self.override_list,
            "Description": self.description,
            "Source": self.source,
            "Source Reference": self.source_ref,
            "Create Time": self.create_time,
            "Created By": self.created_by,
        }


class OverriddenITToolReputation(OverriddenReputation):
    def __init__(
        self,
        raw_data,
        id=None,
        created_by=None,
        create_time=None,
        override_list=None,
        override_type=None,
        description=None,
        source=None,
        source_ref=None,
        path=None,
        include_child_processes=None,
    ):
        super().__init__(
            raw_data,
            id,
            created_by,
            create_time,
            override_list,
            override_type,
            description,
            source,
            source_ref,
        )
        self.path = path
        self.include_child_processes = include_child_processes

    def to_csv(self):
        base_table = super(OverriddenITToolReputation, self).to_csv()
        base_table.update(
            {
                "IT Tool Path": self.path,
                "Include Child Processes": self.include_child_processes,
            }
        )
        return base_table


class OverriddenCertificateReputation(OverriddenReputation):
    def __init__(
        self,
        raw_data,
        id=None,
        created_by=None,
        create_time=None,
        override_list=None,
        override_type=None,
        description=None,
        source=None,
        source_ref=None,
        signed_by=None,
        certificate_authority=None,
    ):
        super().__init__(
            raw_data,
            id,
            created_by,
            create_time,
            override_list,
            override_type,
            description,
            source,
            source_ref,
        )
        self.signed_by = signed_by
        self.certificate_authority = certificate_authority

    def to_csv(self):
        base_table = super(OverriddenCertificateReputation, self).to_csv()
        base_table.update(
            {
                "Certificate Authority": self.certificate_authority,
                "Signed By": self.signed_by,
            }
        )
        return base_table


class OverriddenSHA256Reputation(OverriddenReputation):
    def __init__(
        self,
        raw_data,
        id=None,
        created_by=None,
        create_time=None,
        override_list=None,
        override_type=None,
        description=None,
        source=None,
        source_ref=None,
        sha256_hash=None,
        filename=None,
    ):
        super().__init__(
            raw_data,
            id,
            created_by,
            create_time,
            override_list,
            override_type,
            description,
            source,
            source_ref,
        )
        self.sha256_hash = sha256_hash
        self.filename = filename

    def to_csv(self):
        base_table = super(OverriddenSHA256Reputation, self).to_csv()
        base_table.update({"SHA-256 Hash": self.sha256_hash, "Filename": self.filename})
        return base_table


class VulnerabilityDetail(BaseModel):
    def __init__(self, raw_data, cve_id, score, severity, cve_description):
        super(VulnerabilityDetail, self).__init__(raw_data)
        self.cve_id = cve_id
        self.score = score
        self.severity = severity
        self.cve_description = cve_description

    def to_table(self):
        return {
            "Name": self.cve_id,
            "Risk Meter": self.score,
            "Severity ": self.severity,
            "Description  ": self.cve_description,
        }
