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

from typing import Annotated

import typer

from .describe import DescribeAction

app = typer.Typer(help="Commands for describing actions")


@app.command()
def describe(
    integration: Annotated[str, typer.Option("-i", "--integration", help="Integration name")],
    actions: Annotated[list[str], typer.Argument(help="Action names")],
) -> None:
    """Describe actions in a given integration.

    Args:
        integration: The name of the integration.
        actions: The names of the actions to describe.

    """
    DescribeAction(integration, set(actions)).describe_actions()
