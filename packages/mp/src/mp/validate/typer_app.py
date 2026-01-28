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


import typer

from .commands.deprecated.typer_app import validate as validate_deprecated
from .commands.integrations.typer_app import app as validate_integrations
from .commands.playbooks.typer_app import app as validate_playbooks
from .commands.repository.typer_app import app as validate_repository

validate_app: typer.Typer = typer.Typer(
    name="validate", help="Command that runs the validation on the content-hub."
)

validate_app.callback(invoke_without_command=True)(validate_deprecated)
validate_app.add_typer(validate_repository)
validate_app.add_typer(validate_integrations)
validate_app.add_typer(validate_playbooks)
