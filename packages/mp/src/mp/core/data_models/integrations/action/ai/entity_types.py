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

from enum import StrEnum


class EntityType(StrEnum):
    ADDRESS = "ADDRESS"
    ALERT = "ALERT"
    APPLICATION = "APPLICATION"
    CHILD_HASH = "CHILDHASH"
    CHILD_PROCESS = "CHILDPROCESS"
    CLUSTER = "CLUSTER"
    CONTAINER = "CONTAINER"
    CREDIT_CARD = "CREDITCARD"
    CVE = "CVE"
    CVE_ID = "CVEID"
    DATABASE = "DATABASE"
    DEPLOYMENT = "DEPLOYMENT"
    DESTINATION_DOMAIN = "DESTINATIONDOMAIN"
    DOMAIN = "DOMAIN"
    EMAIL_MESSAGE = "EMAILSUBJECT"
    EVENT = "EVENT"
    FILE_HASH = "FILEHASH"
    FILE_NAME = "FILENAME"
    GENERIC = "GENERICENTITY"
    HOST_NAME = "HOSTNAME"
    IP_SET = "IPSET"
    MAC_ADDRESS = "MacAddress"
    PARENT_HASH = "PARENTHASH"
    PARENT_PROCESS = "PARENTPROCESS"
    PHONE_NUMBER = "PHONENUMBER"
    POD = "POD"
    PROCESS = "PROCESS"
    SERVICE = "SERVICE"
    SOURCE_DOMAIN = "SOURCEDOMAIN"
    THREAT_ACTOR = "THREATACTOR"
    THREAT_CAMPAIGN = "THREATCAMPAIGN"
    THREAT_SIGNATURE = "THREATSIGNATURE"
    URL = "DestinationURL"
    USB = "USB"
    USER = "USERUNIQNAME"
