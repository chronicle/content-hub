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
INTEGRATION_NAME = "ThreatQ"
INTEGRATION_PREFIX = "TQ"
LINK_OBJECTS_SCRIPT = f"{INTEGRATION_NAME} - Link Objects"
CREATE_ADVERSARY_SCRIPT = f"{INTEGRATION_NAME} - Create Adversary"
CREATE_INDICATOR_SCRIPT = f"{INTEGRATION_NAME} - Create Indicator"
LIST_RELATED_OBJECTS_SCRIPT = f"{INTEGRATION_NAME} - List Related Objects"
ADD_ATTRIBUTE_SCRIPT = f"{INTEGRATION_NAME} - Add Attribute"
ADD_SOURCE_SCRIPT = f"{INTEGRATION_NAME} - Add Source"
GET_MALWARE_DETAILS = f"{INTEGRATION_NAME} - Get Malware Details"
CREATE_OBJECT_SCRIPT = f"{INTEGRATION_NAME} - Create Object"
LIST_ENTITY_RELATED_OBJECTS_SCRIPT = f"{INTEGRATION_NAME} - List Entity Related Objects"
CREATE_EVENT_SCRIPT = f"{INTEGRATION_NAME} - Create Event"
UPDATE_INDICATOR_STATUS = f"{INTEGRATION_NAME} - Update Indicator Status"
LINK_ENTITIES_SCRIPT = f"{INTEGRATION_NAME} - Link Entities"
LINK_ENTITIES_TO_OBJECTS_SCRIPT = f"{INTEGRATION_NAME} - Link Entities To Objects"
UPDATE_INDICATOR_SCORE = f"{INTEGRATION_NAME} - Update Indicator Score"
LIST_EVENTS_SCRIPT = f"{INTEGRATION_NAME} - List Events"

HAPPENED_AT_DATETIME_DEFAULT_FORMAT = "%Y-%m-%d %H:%M:%S"
EMAIL_REGEX = r"^[\w\.\+\-]+\@[\w]+\.[a-z]{2,63}$"
THREATQ_PREFIX = "TQ"

ADDITIONAL_FIELDS_LIST = [
    "adversaries",
    "attachments",
    "attributes",
    "comments",
    "events",
    "indicators",
    "signatures",
    "sources",
    "spearphish",
    "tags",
    "type",
    "watchlist",
]

ASCENDING_SORT = "Ascending"

INDICATOR_TYPE_MAPPING = {
    "ASN": 1,
    "Binary String": 2,
    "CIDR Block": 3,
    "CVE": 4,
    "Email Address": 5,
    "Email Attachment": 6,
    "Email Subject": 7,
    "File Mapping": 8,
    "File Path": 9,
    "File name": 10,
    "FQDN": 11,
    "Fuzzy Hash": 12,
    "GOST Hash": 13,
    "Hash ION": 14,
    "IPv4 Address": 15,
    "IPv6 Address": 16,
    "MAC Address": 17,
    "MD5": 18,
    "Mutex": 19,
    "Password": 20,
    "Registry Key": 21,
    "Service Name": 22,
    "SHA-1": 23,
    "SHA-256": 24,
    "SHA-384": 25,
    "SHA-512": 26,
    "String": 27,
    "x509 Serial": 28,
    "x509 Subject": 29,
    "URL": 30,
    "URL Path": 31,
    "User-agent": 32,
    "Username": 33,
    "X-Mailer": 34,
}

OBJECT_TYPE_MAPPING = {
    "Adversary": "adversaries",
    "Attack Pattern": "attack_pattern",
    "Campaign": "campaign",
    "Course of Action": "course_of_action",
    "Event": "events",
    "Exploit Target": "exploit_target",
    "File": "attachments",
    "Identity": "identity",
    "Incident": "incident",
    "Indicator": "indicators",
    "Intrusion Set": "intrusion_set",
    "Malware": "malware",
    "Report": "report",
    "Signature": "signatures",
    "Task": "tasks",
    "Tool": "tool",
    "TTP": "ttp",
    "Vulnerability": "vulnerability",
}

STATUS_MAPPING = {
    "Active": 1,
    "Expired": 2,
    "Indirect": 3,
    "Review": 4,
    "Whitelisted": 5,
}

SCORE_MAPPING = {
    "0 - Very Low": 0,
    "1 - Very Low": 1,
    "2 - Very Low": 2,
    "3 - Very Low": 3,
    "4 - Very Low": 4,
    "5 - Low": 5,
    "6 - Low": 6,
    "7 - Medium": 7,
    "8 - Medium": 8,
    "9 - High": 9,
    "10 - Very High": 10,
}
