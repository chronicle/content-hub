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

from pydantic import BaseModel


class EntityTypesUsage(BaseModel):
    address: bool = False
    alert: bool = False
    application: bool = False
    child_hash: bool = False
    child_process: bool = False
    cluster: bool = False
    container: bool = False
    credit_card: bool = False
    cve: bool = False
    cve_id: bool = False
    database: bool = False
    deployment: bool = False
    destination_domain: bool = False
    domain: bool = False
    email_message: bool = False
    event: bool = False
    file_hash: bool = False
    file_name: bool = False
    generic: bool = False
    host_name: bool = False
    ip_set: bool = False
    mac_address: bool = False
    parent_hash: bool = False
    parent_process: bool = False
    phone_number: bool = False
    pod: bool = False
    process: bool = False
    service: bool = False
    source_domain: bool = False
    threat_actor: bool = False
    threat_campaign: bool = False
    threat_signature: bool = False
    url: bool = False
    usb: bool = False
    user: bool = False


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


ENTITY_TYPE_TO_DEF_ENTITY_TYPE: dict[str, EntityType] = {
    "address": EntityType.ADDRESS,
    "alert": EntityType.ALERT,
    "application": EntityType.APPLICATION,
    "child_hash": EntityType.CHILD_HASH,
    "child_process": EntityType.CHILD_PROCESS,
    "cluster": EntityType.CLUSTER,
    "container": EntityType.CONTAINER,
    "credit_card": EntityType.CREDIT_CARD,
    "cve": EntityType.CVE,
    "cve_id": EntityType.CVE_ID,
    "database": EntityType.DATABASE,
    "deployment": EntityType.DEPLOYMENT,
    "destination_domain": EntityType.DESTINATION_DOMAIN,
    "domain": EntityType.DOMAIN,
    "email_message": EntityType.EMAIL_MESSAGE,
    "event": EntityType.EVENT,
    "file_hash": EntityType.FILE_HASH,
    "file_name": EntityType.FILE_NAME,
    "generic": EntityType.GENERIC,
    "host_name": EntityType.HOST_NAME,
    "ip_set": EntityType.IP_SET,
    "mac_address": EntityType.MAC_ADDRESS,
    "parent_hash": EntityType.PARENT_HASH,
    "parent_process": EntityType.PARENT_PROCESS,
    "phone_number": EntityType.PHONE_NUMBER,
    "pod": EntityType.POD,
    "process": EntityType.PROCESS,
    "service": EntityType.SERVICE,
    "source_domain": EntityType.SOURCE_DOMAIN,
    "threat_actor": EntityType.THREAT_ACTOR,
    "threat_campaign": EntityType.THREAT_CAMPAIGN,
    "threat_signature": EntityType.THREAT_SIGNATURE,
    "url": EntityType.URL,
    "usb": EntityType.USB,
    "user": EntityType.USER,
}
