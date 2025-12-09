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
    "validate": "validate",
    "run_pre_build_tests": "test",
    "format_files": "format",
    "login": "dev-env login",
    "deploy": "dev-env deploy",
    "push": "dev-env push",
    "build": "build",
}

ALLOWED_COMMAND_ARGUMENTS: set[str] = {
    "repositories",
    "integrations",
    "integration",
    "playbooks",
    "playbook",
    "group",
    "only_pre_build",
    "quiet",
    "verbose",
    "raise_error_on_violations",
    "deconstruct",
    "changed_files",
    "-r",
    "-i",
    "-p",
}
