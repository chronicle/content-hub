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
PROVIDER_NAME = "SiemplifyUtilities"

# Actions name
PARSE_EML_TO_JSON_SCRIPT_NAME = f"{PROVIDER_NAME} - Parse EML to JSON"
EXPORT_ENTITIES_AS_OPENIOC_FILE_SCRIPT_NAME = "Export Entities as OpenIOC file"
DELETE_FILE_SCRIPT_NAME = "{PROVIDER_NAME} - Delete File"

PARAMETERS_DEFAULT_DELIMITER = ","
MAGIC = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"
LOCALHOST = "127.0.0.1"

# status
FILE_DELETE_STATUS = "deleted"
FILE_NOT_FOUND_STATUS = "not found"

IOC_STRING_CONTENT_TYPE = "string"
IOC_BOOL_CONTENT_TYPE = "bool"

MD5_HASH_LENGTH = 32
SHA1_HASH_LENGTH = 40
SHA256_HASH_LENGTH = 64
IOC_EXTENSION = "ioc"
IOC_FILE_DESCRIPTION = "Siemplify Generated IOC"
IOC_FILE_AUTHOR = "Siemplify"
NUMERIC_REGEX = r"^\d+$"
UNDERSCORE = "_"
# IOC
MD5_HASH = "md5"
SHA1_HASH = "sha1"
SHA256_HASH = "sha256"
IP_ADDRESS = "ip_address"
DOMAIN = "domain"
HOSTNAME = "hostname"
IS_USER_ENABLED = "is_enabled"
MAC_ADDRESS = "mac_address"
OS = "os"
ASSET_TYPE = "asset_type"
PROCESSOR = "processor"
USERNAME = "username"
MEMORY = "memory"
USER_GROUPS = "groups"
USER_EMAIL = "email"
USER_DISPLAY_NAME = "display_name"
URL = "url"
HOST_MEMORY = "memory"
HOST_OS_VERSION = "os_version"
IOC_MAPPINGS = {  # IOC search term type and text
    MD5_HASH: (IOC_STRING_CONTENT_TYPE, "FileItem/Md5sum"),
    SHA1_HASH: (IOC_STRING_CONTENT_TYPE, "FileItem/Sha1sum"),
    SHA256_HASH: (IOC_STRING_CONTENT_TYPE, "FileItem/Sha256sum"),
    IP_ADDRESS: (IOC_STRING_CONTENT_TYPE, "DnsEntryItem/RecordData/IPv4Address"),
    IS_USER_ENABLED: (IOC_BOOL_CONTENT_TYPE, "UserItem/disabled"),
    DOMAIN: (IOC_STRING_CONTENT_TYPE, "SystemInfoItem/domain"),
    HOSTNAME: (IOC_STRING_CONTENT_TYPE, "DnsEntryItem/HOST"),
    MAC_ADDRESS: (IOC_STRING_CONTENT_TYPE, "SystemInfoItem/MAC"),
    OS: (IOC_STRING_CONTENT_TYPE, "SystemInfoItem/OS"),
    ASSET_TYPE: (IOC_STRING_CONTENT_TYPE, "DnsEntryItem/RecordData/Type"),
    PROCESSOR: (IOC_STRING_CONTENT_TYPE, "SystemInfoItem/processor"),
    USERNAME: (IOC_STRING_CONTENT_TYPE, "UserItem/Username"),
    USER_GROUPS: (IOC_STRING_CONTENT_TYPE, "UserItem/grouplist/groupname"),
    USER_EMAIL: (IOC_STRING_CONTENT_TYPE, "UserItem/userid"),
    USER_DISPLAY_NAME: (IOC_STRING_CONTENT_TYPE, "UserItem/fullname"),
    HOST_MEMORY: (IOC_STRING_CONTENT_TYPE, "SystemInfoItem/totalphysical"),
    HOST_OS_VERSION: [
        (IOC_STRING_CONTENT_TYPE, "SystemInfoItem/kernelVersion"),
        (IOC_STRING_CONTENT_TYPE, "SystemInfoItem/biosInfo/biosVersion"),
    ],
    URL: (IOC_STRING_CONTENT_TYPE, "UrlHistoryItem/URL"),
}
NEGATABLE_IOCS = [IS_USER_ENABLED]
