# Copyright 2025 Google LLC
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

from pathlib import Path
from typing import TypedDict

from platformdirs import user_config_dir

ENDPOINT: str = "https://34-36-216-242.sslip.io/v1/ingest"
REQUEST_TIMEOUT: int = 3

APP_AUTHOR: str = "Google"
APP_NAME: str = "mp-cli-tool"
MP_CACHE_DIR: Path = Path(user_config_dir(APP_NAME, APP_AUTHOR))
CONFIG_FILE_PATH: Path = MP_CACHE_DIR / Path("telemetry_config.yaml")


class ConfigYaml(TypedDict):
    install_id: str
    uuid4: str
    report: bool


NAME_MAPPER: dict[str, str] = {
    "build": "build",
    "validate": "validate",
    "run_pre_build_tests": "test",
    "format_files": "format",
    "login": "dev-env login",
    "deploy": "dev-env deploy",
    "build_integration": "build integration",
    "build_playbook": "build playbook",
    "build_repository": "build repository",
    "validate_integration": "validate integration",
    "validate_playbook": "validate playbook",
    "validate_repository": "validate repository",
    "push_integration": "dev-env push integration",
    "pull_integration": "dev-env pull integration",
    "push_playbook": "dev-env push playbook",
    "pull_playbook": "dev-env pull playbook",
    "push_custom_integration_repository": "dev-env push custom integration repository",
    "describe_action_with_ai": "describe action",
    "self_update": "self update"
}

ALLOWED_COMMAND_ARGUMENTS: set[str] = {
    "help",
    "repository",
    "integration",
    "playbook",
    "custom_integration",
    "deconstruct",
    "only_pre_build",
    "is_staging",
    "custom",
    "include_blocks",
    "keep_zip",
    "raise_error_on_violations",
    "changed_files",
    "quiet",
    "src",
    "dst",
    "-q",
    "verbose",
    "-v",
    "-r",
    "-i",
    "-p",
    "-d",
    "all",
    "override",
    "--version",
    "-V",
}
