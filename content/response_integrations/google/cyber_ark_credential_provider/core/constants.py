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

import paramiko


INTEGRATION_NAME: str = "CyberArkCredentialProvider"

RUN_CLI_APP_PASSWORD_SDK_COMMAND_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - Run CLI Application Password SDK Command"
)
GET_APPLICATION_PASSWORD_VALUE_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - Get Application Password Value"
)
PING_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Ping"
SYNC_CREDENTIAL_JOB_SCRIPT_NAME: str = "Sync Integration Credentials"

TEST_COMMAND: str = "-?"

PASSWORD_OUTPUT_FIELD: str = "Password"

# Credential mapping JSON keys
INTEGRATION_INSTANCES_KEY: str = "integration_instances"
CONNECTORS_KEY: str = "connectors"
JOBS_KEY: str = "jobs"

# API Filter Values
LIST_ALL_RESULTS_VALUE: str = "-"

KEY_CLASSES: dict[str, type[paramiko.PKey] | None] = {
    "ssh-rsa": paramiko.RSAKey,
    "ssh-dss": getattr(paramiko, "DSSKey", None),
    "ecdsa-sha2-nistp256": paramiko.ECDSAKey,
    "ecdsa-sha2-nistp384": paramiko.ECDSAKey,
    "ecdsa-sha2-nistp521": paramiko.ECDSAKey,
    "ssh-ed25519": paramiko.Ed25519Key,
}

# Types & Concurrency Constants
NameIdentifierMap = dict[str, str]
TIMEOUT_THRESHOLD_MS: int = 120000
ASYNC_SEMAPHORE_LIMIT: int = 10

# SSH & SDK Execution Constants
SUCCESS_EXIT_CODE: int = 0

# Job Parameter Attribute Names (matches self.params.<attr_name>)
PATH_TO_CLIPASSWORDSDK_JOB_PARAM: str = "pathtoclipasswordsdk"
USERNAME_JOB_PARAM: str = "usernamefor_credential_providerfor_linux"
DOCKER_GATEWAY_IP_JOB_PARAM: str = "docker_gateway_ip_address"
HOST_PUBLIC_KEY_JOB_PARAM: str = "host_public_key"
SSH_PRIVATE_KEY_PATH_JOB_PARAM: str = "ssh_private_key_path"
PASSWORD_JOB_PARAM: str = "passwordfor_credential_providerfor_linux"

# Integration/Action Configuration Parameter Names (UI names)
PATH_TO_CLIPASSWORDSDK_CONFIG_PARAM: str = "Path to clipasswordsdk"
USERNAME_CONFIG_PARAM: str = "Username for Credential Provider for Linux"
DOCKER_GATEWAY_IP_CONFIG_PARAM: str = "Docker Gateway IP Address"
HOST_PUBLIC_KEY_CONFIG_PARAM: str = "Host Public Key"
SSH_PRIVATE_KEY_PATH_CONFIG_PARAM: str = "SSH Private Key Path"
PASSWORD_CONFIG_PARAM: str = "Password for Credential Provider for Linux"
