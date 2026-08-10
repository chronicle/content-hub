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

import asyncio
import logging
import pathlib  # ruff:ignore[typing-only-standard-library-import]
from typing import Annotated

import typer

import mp.core.config

from .describe_all import describe_all_integrations

logger: logging.Logger = logging.getLogger(__name__)


app = typer.Typer(help="Commands for describing integrations")


@app.command(
    name="integration",
    help="Describe integrations using Gemini.",
    epilog=(
        "Examples:\n\n"
        "    $ mp describe integration aws_ec2\n\n"
        "    $ mp describe integration --all\n\n"
        "    $ mp describe integration --all --src ./custom_folder\n\n"
        "    $ mp describe integration aws_ec2 --prompt-overrides /path/to/overrides.yaml\n\n"
        "YAML Prompt Overrides Schema:\n\n"
        "    The --prompt-overrides flag accepts a path to a YAML configuration file.\n"
        "    Expected YAML structure (same format as evaluation ruleset):\n\n"
        '    - target_field: "product_categories"\n'
        "      criteria: >\n"
        "        Custom criteria and rules for product categories...\n\n"
        '    - target_field: "field_with_undefined_schema"\n'
        "      criteria: >\n"
        "        Custom criteria and rules...\n"
        "      schema:\n"
        '        model_name: "ModelName"\n'
        '        type: "string"\n'
        '        description: "Description of the field we do not have schema defined in code."\n'
        "        required: true\n"
    ),
    no_args_is_help=True,
)
def describe(  # ruff:ignore[too-many-arguments]
    integrations: Annotated[list[str] | None, typer.Argument(help="Integration names")] = None,
    *,
    all_marketplace: Annotated[
        bool, typer.Option("-a", "--all", help="Describe all integrations in the marketplace")
    ] = False,
    src: Annotated[pathlib.Path | None, typer.Option(help="Customize source folder to describe from.")] = None,
    dst: Annotated[
        pathlib.Path | None, typer.Option(help="Customize destination folder to save the AI descriptions.")
    ] = None,
    prompt_overrides: Annotated[
        pathlib.Path | None,
        typer.Option(
            "--prompt-overrides",
            help="Path to YAML prompt configuration file to override prompts for specific fields.",
        ),
    ] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Log less on runtime.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Log more on runtime.")] = False,
    override: Annotated[
        bool, typer.Option("--override", "-o", help="Rewrite integrations that already have their description.")
    ] = False,
) -> None:
    """Describe integrations.

    Args:
        integrations: The names of the integrations.
        all_marketplace: Whether to describe all integrations in the marketplace.
        src: Customize the source folder to describe from.
        dst: Customize destination folder to save the AI descriptions.
        prompt_overrides: Path to YAML prompt configuration file.
        quiet: Quiet log options.
        verbose: Verbose log options.
        override: Whether to rewrite existing descriptions.

    Raises:
        typer.Exit: If neither integrations nor --all is specified.

    """
    run_params: mp.core.config.RuntimeParams = mp.core.config.RuntimeParams(quiet, verbose)
    run_params.set_in_config()

    if integrations and not all_marketplace:
        asyncio.run(
            describe_all_integrations(
                src=src,
                dst=dst,
                override=override,
                prompt_overrides=prompt_overrides,
                integrations=integrations,
            )
        )
    elif all_marketplace:
        asyncio.run(
            describe_all_integrations(
                src=src,
                dst=dst,
                override=override,
                prompt_overrides=prompt_overrides,
            )
        )
    else:
        logger.error("Please specify either integrations or --all")
        raise typer.Exit(code=1)
