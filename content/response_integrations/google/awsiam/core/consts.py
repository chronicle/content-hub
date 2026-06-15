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
INTEGRATION_NAME = "AWS Identity and Access Management (IAM)"
INTEGRATION_NAME_SHORT = "AWS IAM"
INTEGRATION_IDENTIFIER = "AWSIAM"

VALID_CHARACTERS = "+=.@_-"

#  actions names:
PING = "Ping"
CREATE_USER = "Create a User"
CREATE_GROUP = "Create a Group"
LIST_USERS = "List Users"
LIST_GROUPS = "List Groups"
ADD_USER_TO_GROUP_SCRIPT_NAME = "Add a User to a Group"
REMOVE_USER_FROM_GROUP_SCRIPT_NAME = "Remove a User from a Group"
CREATE_POLICY_SCRIPT_NAME = "Create a Policy"
LIST_POLICIES_SCRIPT_NAME = "List Policies"
ATTACH_POLICY_SCRIPT_NAME = "Attach a Policy"
DISABLE_USER_SCRIPT_NAME = f"{INTEGRATION_NAME} - Disable User"

#  error names:
ENTITY_ALREADY_EXISTS = "EntityAlreadyExists"
VALIDATION_ERROR = "ValidationError"
LIMIT_EXCEEDED = "LimitExceeded"
NO_SUCH_ENTITY_ERROR = "NoSuchEntity"
MALFORMED_POLICY_DOCUMENT_ERROR = "MalformedPolicyDocument"
INVALID_INPUT_ERROR = "InvalidInput"

DEFAULT_MAX_RESULTS = 1000
DEFAULT_MAX_POLICIES_TO_RETURN = 100
DEFAULT_MIN_RESULTS = 1
PAGE_SIZE = 100

DEFAULT_LIST_POLICIES_SCOPE = "All"
GROUP_IDENTITY_TYPE = "Group"
USER_IDENTITY_TYPE = "User"
ROLE_IDENTITY_TYPE = "Role"
