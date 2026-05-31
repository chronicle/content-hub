"""Main entry point for the `mp` CLI tool.

This script initializes and runs the Typer application, exposing various
commands for building, checking, configuring, and formatting integration
projects within the marketplace. It imports the sub-applications from
the `build_project`, `check`, `config`, and `format` modules and mounts
them onto the main Typer instance.
"""

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

from . import build_project, check, config, describe, dev_env, run_pre_build_tests, validate
from . import format as format_app

__all__: list[str] = [
    "build_project",
    "check",
    "config",
    "describe",
    "dev_env",
    "format_app",
    "run_pre_build_tests",
    "validate",
]
