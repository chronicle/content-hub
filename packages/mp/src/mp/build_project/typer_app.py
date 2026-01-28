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

import typer

from .sub_commands.deprecated.build import build as build_deprecated
from .sub_commands.integrations.build import app as build_integrations
from .sub_commands.playbooks.build import app as build_playbooks
from .sub_commands.repository.build import app as build_repository

build_app: typer.Typer = typer.Typer(
    name="build",
    help="Command that builds content from the content-hub and transforms "
    "it into a format suitable for SOAR platform.",
)

build_app.callback(invoke_without_command=True)(build_deprecated)
build_app.add_typer(build_integrations)
build_app.add_typer(build_playbooks)
build_app.add_typer(build_repository)
