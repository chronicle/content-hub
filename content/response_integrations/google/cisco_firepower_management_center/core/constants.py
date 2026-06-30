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
UPDATE_URL_GROUP_PAYLOAD = {
    "id": "url_group_uuid",
    "name": "urlgroup_name",
    "literals": [],
}

CREATE_PORT_OBJECT_PAYLOAD = {
    "name": "SIEMPLIFY_{0}",
    "port": "6868",
    "protocol": "TCP",
}

UPDATE_PORT_GROUP_PAYLOAD = {"objects": [], "type": "PortObjectGroup"}

PORT_OBJECT_STRUCTURE = {
    "type": "ProtocolPortObject",
    "id": "1834d812-38bb-11e2-86aa-62f0c593a59a",
}

OBTAIN_TOKEN_URL = "/api/fmc_platform/v1/auth/generatetoken"
GET_POLICIES_URL = "/api/fmc_config/v1/domain/{0}/policy/accesspolicies"
GET_RULES_FOR_POLICY_URL = (
    "/api/fmc_config/v1/domain/{0}/policy/accesspolicies/{1}/accessrules"
)
GET_RULE_URL = "/api/fmc_config/v1/domain/{0}/policy/accesspolicies/{1}/accessrules/{2}"
GET_URL_GROUPS_URL = "/api/fmc_config/v1/domain/{0}/object/urlgroups"
GET_URL_GROUP_OBJECT_URL = "/api/fmc_config/v1/domain/{0}/object/urlgroups/{1}"
CREATE_PORT_OBJECT_URL = "/api/fmc_config/v1/domain/{0}/object/protocolportobjects"
GET_ALL_PORT_GROUP_OBJECTS_URL = "/api/fmc_config/v1/domain/{0}/object/portobjectgroups"
GET_PORT_GROUP_OBJECT_URL = "/api/fmc_config/v1/domain/{0}/object/portobjectgroups/{1}"
GET_PORT_OBJECT_BY_ID_URL = (
    "/api/fmc_config/v1/domain/{0}/object/protocolportobjects/{1}"
)
GET_NETWORK_GROUP_OBJECT_BY_ID_URL = (
    "/api/fmc_config/v1/domain/{0}/object/networkgroups/{1}"
)
GET_NETWORK_GROUP_OBJECTS_URL = "/api/fmc_config/v1/domain/{0}/object/networkgroups"
RULE_LITERAL_OBJECT = {"url": "google.com", "type": "Url"}
RULE_URL_PATTERN = {"literals": []}
IP_ADDRESS_LITERAL_PATTERN = {"type": "host", "value": "1.2.3.0"}
PAGINATION_LIMIT = 1000
PAGE_SIZE = 25
