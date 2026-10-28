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
from soar_sdk.SiemplifyUtils import dict_to_flat

MONITORED = "monitored"


class Endpoint:
    def __init__(
        self,
        raw_data,
        domain=None,
        updated_at=None,
        id=None,
        display_operating_system=None,
        hostname=None,
        mac_address=None,
        status=None,
        tags=None,
        groups=None,
        sensors=None,
        ip_address=None,
        is_isolated=None,
        operating_system=None,
        name=None,
        core_os=None,
        created_at=None,
        machine_id=None,
        ad_distinguished_name=None,
        ad_hostname=None,
        alert_count=None,
        isolation_request_status=None,
        **kwargs,
    ):
        self.raw_data = raw_data
        self.domain = domain
        self.updated_at = updated_at
        self.id = id
        self.display_operating_system = display_operating_system
        self.hostname = hostname
        self.mac_address = mac_address
        self.status = status
        self.tags = tags
        self.groups = groups
        self.sensors = sensors
        self.ip_address = ip_address
        self.is_isolated = is_isolated
        self.operating_system = operating_system
        self.name = name
        self.core_os = core_os
        self.created_at = created_at
        self.machine_id = machine_id
        self.ad_distinguished_name = ad_distinguished_name
        self.ad_hostname = ad_hostname
        self.alert_count = alert_count
        self.isolation_request_status = isolation_request_status
        self.is_active = self.status == MONITORED

    def as_enrichment_data(self):
        return dict_to_flat(
            {
                "domain": self.domain,
                "endpoint_id": self.id,
                "hostname": self.hostname,
                "ip_address": self.ip_address,
                "display_operating_system": self.display_operating_system,
                "status": self.status,
                "ad_distinguished_name": self.ad_distinguished_name,
                "ad_hostname": self.ad_hostname,
                "alert_count": self.alert_count,
                "is_isolated": self.is_isolated,
                "sensors": [sensor.raw_data for sensor in self.sensors],
                "groups": [group.raw_data for group in self.groups],
            }
        )

    def as_csv(self):
        return {
            "Hostname": self.hostname,
            "ID": self.id,
            "IP Address": self.ip_address,
            "Status": self.status,
            "OS": self.display_operating_system,
            "AD Name": self.ad_distinguished_name,
            "AD Hostname": self.ad_hostname,
            "Sensor ID": (
                "\n".join([sensor.id for sensor in self.sensors])
                if self.sensors
                else None
            ),
            "Sensor Status": (
                "\n".join([sensor.status for sensor in self.sensors])
                if self.sensors
                else None
            ),
            "Policy Name": (
                "\n".join([sensor.policy_name for sensor in self.sensors])
                if self.sensors
                else None
            ),
            "Policy ID": (
                "\n".join([sensor.policy_id for sensor in self.sensors])
                if self.sensors
                else None
            ),
            "Policy Status": (
                "\n".join([sensor.policy_status for sensor in self.sensors])
                if self.sensors
                else None
            ),
            "Isolated": self.is_isolated,
        }


class Group:
    def __init__(
        self, raw_data, is_dynamic=None, count=None, id=None, name=None, **kwargs
    ):
        self.raw_data = raw_data
        self.is_dynamic = is_dynamic
        self.count = count
        self.id = id
        self.name = name


class Sensor:
    def __init__(
        self,
        raw_data,
        status=None,
        sensor_version=None,
        policy_status=None,
        policy_name=None,
        sensor_type=None,
        id=None,
        policy_id=None,
        **kwargs,
    ):
        self.raw_data = raw_data
        self.status = status
        self.sensor_version = sensor_version
        self.policy_status = policy_status
        self.policy_name = policy_name
        self.policy_id = policy_id
        self.sensor_type = sensor_type
        self.id = id


class Investigation:
    def __init__(
        self,
        raw_data,
        id=None,
        name=None,
        hunt_count=None,
        endpoint_count=None,
        core_os=None,
        updated_at=None,
        completed_tasks=None,
        total_tasks=None,
        created_by_username=None,
        created_at=None,
        sensors=None,
        task_completions=None,
        **kwargs,
    ):
        self.raw_data = raw_data
        self.id = id
        self.name = name
        self.hunt_count = hunt_count
        self.endpoint_count = endpoint_count
        self.core_os = core_os
        self.updated_at = updated_at
        self.created_by = created_by_username
        self.created_at = created_at
        self.sensors = sensors
        self.task_completions = task_completions
        self.completed_tasks = completed_tasks
        self.total_tasks = total_tasks

    def as_csv(self):
        return {
            "Investigation ID": self.id,
            "Name": self.name,
            "Hunt Count": self.hunt_count,
            "Endpoint Count": self.endpoint_count,
            "Core OS": self.core_os,
            "Last Update At": self.updated_at,
            "Created By": self.created_by,
            "Created At": self.created_at,
        }

    def as_detailed_csv(self):
        return {
            "Investigation ID": self.id,
            "Name": self.name,
            "Hunt Count": self.hunt_count,
            "Endpoint Count": self.endpoint_count,
            "Core OS": self.core_os,
            "Last Update At": self.updated_at,
            "Created By": self.created_by,
            "Created At": self.created_at,
            "Tasks Completed": (
                "\n".join([task.as_text() for task in self.task_completions])
                if self.task_completions
                else None
            ),
            "Sensors": "\n".join(self.sensors) if self.sensors else None,
        }


class TaskCompletion:
    def __init__(self, task_name, completed_tasks=0, total_tasks=0):
        self.task_name = task_name
        self.completed_tasks = completed_tasks
        self.total_tasks = total_tasks

    def as_text(self):
        return f"{self.task_name}: {self.completed_tasks}/{self.total_tasks}"


class IsolationRuleComment:
    def __init__(
        self,
        raw_data=None,
        comment=None,
        entity_id=None,
        entity_type=None,
        created_at=None,
        updated_at=None,
        id=None,
        activity_type=None,
        **kwargs,
    ):
        self.raw_data = raw_data
        self.comment = comment
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.created_at = created_at
        self.updated_at = updated_at
        self.id = id
        self.activity_type = activity_type


class IsolationRule:
    def __init__(self, raw_data, id=None, rule_comments=None, addr=None, **kwargs):
        self.raw_data = raw_data
        self.id = id
        self.rule_comments = rule_comments
        self.addr = addr

    def as_csv(self):
        return {
            "IP Subnets": self.addr,
            "Description": (
                "\n".join([rule_comment.comment for rule_comment in self.rule_comments])
                if self.rule_comments
                else None
            ),
        }


class HostIsolationConfig:
    def __init__(self, raw_data, isolation_rules=None):
        self.raw_data = raw_data
        self.isolation_rules = isolation_rules

    def as_csv(self):
        return (
            [isolation_rule.as_csv() for isolation_rule in self.isolation_rules]
            if self.isolation_rules
            else []
        )
