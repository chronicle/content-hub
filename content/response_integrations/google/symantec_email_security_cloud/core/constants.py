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
INTEGRATION_NAME = "SymantecEmailSecurityCloud"
INTEGRATION_DISPLAY_NAME = "Symantec Email Security.Cloud"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
BLOCK_ENTITIES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Block Entities"

ENDPOINTS = {
    "ping": "/domains/global/iocs/download",
    "block_entities": "/domains/global/iocs/upload?api-list-action=MERGE",
}

IOC_TYPES_MAPPING = {
    "DestinationURL": ["url"],
    "FILEHASH": {"MD5": ["md5attachment"], "SHA256": ["sha2attachment"]},
    "ADDRESS": ["senderipaddress"],
    "HOSTNAME": ["bodysenderdomain", "envelopesenderdomain"],
    "EMAILSUBJECT": ["subject"],
    "USERUNIQNAME": ["envelopesenderemail", "bodysenderemail"],
}

REMEDIATION_MAPPING = {
    "Block and Delete": "B",
    "Quarantine": "Q",
    "Redirect": "M",
    "Tag Subject": "T",
    "Append Header": "H",
}
DEFAULT_REMEDIATION = "Block and Delete"
SHA256_LENGTH = 64
MD5_LENGTH = 32
