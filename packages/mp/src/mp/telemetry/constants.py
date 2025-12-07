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

from typing import TYPE_CHECKING

from mp.core.config import get_marketplace_path

if TYPE_CHECKING:
    from pathlib import Path

ENDPOINT: str = "https://34-36-216-242.sslip.io/v1/ingest"
REQUEST_TIMEOUT: int = 3
MP_CACHE_DIR: Path = get_marketplace_path() / ".mp_cache"
CONFIG_FILE_PATH: Path = MP_CACHE_DIR / "config.yaml"


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
    "repository",
    "integration",
    "group",
    "only_pre_build",
    "quiet",
    "verbose",
    "raise_error_on_violations",
    "deconstruct",
    "changed_files",
}
