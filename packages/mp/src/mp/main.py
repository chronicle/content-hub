"""Main entry point for the `mp` CLI tool.

This script initializes and runs the Typer application, exposing various
commands for building, checking, configuring, and formatting integration
projects within the marketplace. It imports the sub-applications from
the `build_project`, `check`, `config`, and `format` modules and mounts
them onto the main Typer instance.
"""

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

import atexit
from typing import Annotated

import typer

from mp.core import config as mp_config
from mp.core.logger.setup import setup_logging
from mp.core.update_checker import UpdateChecker, get_mp_version, print_mp_version

from . import describe
from .build_project.typer_app import build_app
from .check.typer_app import check_app
from .config.typer_app import config_app
from .dev_env.typer_app import dev_env_app
from .format.typer_app import format_app
from .run_pre_build_tests.typer_app import test_app
from .self_update.typer_app import self_app
from .validate.typer_app import validate_app

app: typer.Typer = typer.Typer()


def main() -> None:
    """Entry point for the `mp` CLI tool, initializing all sub-applications."""
    setup_logging(verbose=mp_config.is_verbose(), quiet=mp_config.is_quiet())

    app.add_typer(build_app, name="build")
    app.add_typer(check_app)
    app.add_typer(config_app, name="config")
    app.add_typer(format_app)
    app.add_typer(test_app)
    app.add_typer(dev_env_app, name="dev-env")
    app.add_typer(validate_app, name="validate")
    app.add_typer(describe.app, name="describe")
    app.add_typer(self_app, name="self")
    app()


@app.callback(invoke_without_command=True)
def version_check(
    *,
    _version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            callback=print_mp_version,
            is_eager=True,
            help="Show the version of the mp tool.",
        ),
    ] = False,
) -> None:
    """Set up mp tool and initialize background tasks."""
    checker: UpdateChecker = UpdateChecker()
    checker.start_background_check(get_mp_version())
    atexit.register(checker.print_warning_if_needed)


if __name__ == "__main__":
    main()
