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
INTEGRATION_NAME = "AWSWAF"
INTEGRATION_DISPLAY_NAME = "AWS WAF"
MIN_IP_SETS = 1
MAX_IP_SETS = 100
DEFAULT_MAX_IP_SETS = 50
MAX_WEB_ACLS = 100
DEFAULT_WEB_ACLS = 50
MIN_WEB_ACLS = 1

MAX_RULE_GROUPS = 100
DEFAULT_RULE_GROUPS = 50
MIN_RULE_GROUPS = 1


DEFAULT_MAX_REGEX_SETS = 5
MIN_REGEX_PATTERN_SETS = 1
MAX_REGEX_SETS = 10  # AWS WAF fixed quota can't be changed
MAX_REGEX_PATTERNS_IN_REGEX_SET = 10  # AWS WAF fixed quota can't be changed

DEFAULT_DDL_SCOPE = "CloudFront"

MAPPED_SCOPE = {"CloudFront": "CLOUDFRONT", "Regional": "REGIONAL"}

UNMAPPED_SCOPE = {"CLOUDFRONT": "CloudFront", "REGIONAL": "Regional"}

REGIONAL_SCOPE = "REGIONAL"
CLOUDFRONT_SCOPE = "CLOUDFRONT"
BOTH_SCOPE = "Regional/CloudFront"
PARAM_BOTH_SCOPE = "Both"

IPV4_MASK = "/32"
IPV6_MASK = "/128"

MAPPED_IPV = {"IPV4": 4, "IPV6": 6}

UNMAPPED_IPV = {4: "IPV4", 6: "IPV6"}

DEFAULT_RULE_GROUP_CAPACITY = 100

DEFAULT_RULE_SOURCE_TYPE = "IP Set"

RULE_GROUP = "Rule Group"
IP_SET = "IP Set"

DEFAULT_WEB_ACL_DEFAULT_ACTION = "Allow"
DEFAULT_IP_SET_ACTION = "Block"
HTTP_HTTPS_PROTOCOL_REGEX_WRAP = "^(http|https)(:\/\/)(\Q{}\E).*"
DEFAULT_PRIORITY = 0

PAGE_SIZE = 50
PAGE_SIZE_10 = 10
