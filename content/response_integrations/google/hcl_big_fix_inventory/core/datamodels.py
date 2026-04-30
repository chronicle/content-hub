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

from TIPCommon import add_prefix_to_dict, dict_to_flat

from .UtilsManager import convert_list_to_comma_string


class BaseModel:
    """Base model for inheritance"""

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_table(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Device(BaseModel):
    def __init__(
        self,
        raw_data,
        bigfix_id,
        name,
        dns_name,
        ip_address,
        os,
        first_seen,
        last_seen,
        is_deleted,
        deletion_date,
        last_scan_attempt,
        is_out_of_date,
        is_out_of_sync,
        is_missing_prereqs,
        is_low_on_disk_space,
    ):
        super().__init__(raw_data)
        self.bigfix_id = bigfix_id
        self.name = name
        self.dns_name = dns_name
        self.ip_address = ip_address
        self.ip_addresses = convert_list_to_comma_string(ip_address)
        self.os = os
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.is_deleted = is_deleted
        self.deletion_date = deletion_date
        self.last_scan_attempt = last_scan_attempt
        self.is_out_of_date = is_out_of_date
        self.is_out_of_sync = is_out_of_sync
        self.is_missing_prereqs = is_missing_prereqs
        self.is_low_on_disk_space = is_low_on_disk_space

    def to_table(self):
        return {
            "name": self.name,
            "dns_name": self.dns_name,
            "ip_address": self.ip_addresses,
            "os": self.os,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "is_deleted": self.is_deleted,
            "deletion_date": self.deletion_date,
            "last_scan_attempt": self.last_scan_attempt,
            "is_out_of_date": self.is_out_of_date,
            "is_out_of_sync": self.is_out_of_sync,
            "is_missing_prereqs": self.is_missing_prereqs,
            "is_low_on_disk_space": self.is_low_on_disk_space,
        }

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.to_table())
        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_insight(self):
        return (
            f"<p><strong>Name:</strong> {self.name}<br /><strong>DNS Name:</strong> "
            f"{self.dns_name}<br />"
            f"<strong>IP Addresses:</strong> {self.ip_addresses}<br /><strong>OS"
            f":</strong> {self.os}<br />"
            f"<strong>First Seen:</strong> {self.first_seen}<br /><strong>Last "
            f"Seen:</strong> {self.last_seen}<br />"
            f"<strong>Last Scan Attempt:</strong> {self.last_scan_attempt}<br />"
            f"<strong>Is Out Of Date:</strong> {self.is_out_of_date}<br />"
            f"<strong>Is Out Of Sync:</strong> {self.is_out_of_sync}<br />"
            f"<strong>Is Missing Prereqs:</strong> {self.is_missing_prereqs}<br />"
            f"<strong>Is Low On Disk Space:</strong> {self.is_low_on_disk_space}<br />"
            f"<strong>Is Deleted:</strong> {self.is_deleted}<br />"
            f"<strong>Deletion Date:</strong> {self.deletion_date}</p>"
        )
