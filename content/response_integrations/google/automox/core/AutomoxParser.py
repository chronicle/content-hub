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
from .datamodels import Policy, Device, Patch, QueueObjectCommand
from typing import List


class AutomoxParser:
    @staticmethod
    def build_policies(policies_data) -> List[Policy]:
        return [
            Policy(
                raw_data=policy_data,
                id=policy_data.get("id"),
                name=policy_data.get("name"),
                policy_type_name=policy_data.get("policy_type_name"),
                status=policy_data.get("status"),
                notes=policy_data.get("notes"),
            )
            for policy_data in policies_data
        ]

    @staticmethod
    def build_devices(devices_data) -> List[Device]:
        return [
            Device(
                raw_data=device_data,
                id=device_data.get("id"),
                ip_addrs_private=device_data.get("ip_addrs_private"),
                display_name=device_data.get("display_name"),
                connected=device_data.get("connected"),
            )
            for device_data in devices_data
        ]

    @staticmethod
    def build_queue_command_objects(queue_command_data) -> List[QueueObjectCommand]:
        return [
            QueueObjectCommand(
                raw_data=queue_item_data,
                id=queue_item_data.get("id"),
                server_id=queue_item_data.get("server_id"),
                command_id=queue_item_data.get("command_id"),
                organization_id=queue_item_data.get("organization_id"),
                args=queue_item_data.get("args"),
                exec_time=queue_item_data.get("exec_time"),
                response=queue_item_data.get("response"),
                response_time=queue_item_data.get("response_time"),
                policy_id=queue_item_data.get("policy_id"),
                agent_command_type=queue_item_data.get("agent_command_type"),
                command_type_name=queue_item_data.get("command_type_name"),
            )
            for queue_item_data in queue_command_data
        ]

    @staticmethod
    def build_patches(patches_data) -> List[Patch]:
        return [
            Patch(
                raw_data=patch_data,
                id=patch_data.get("id"),
                installed=patch_data.get("installed"),
                ignored=patch_data.get("ignored"),
            )
            for patch_data in patches_data
        ]
