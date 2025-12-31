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

import json
from pathlib import Path

import rich
import typer

from mp.dev_env import api

CONFIG_PATH: Path = Path.home() / ".mp_dev_env.json"


def load_dev_env_config() -> dict[str, str]:
    """Load the dev environment configuration from the config file.

    Returns:
        dict: The loaded configuration.

    Raises:
        typer.Exit: If the config file does not exist.

    """
    if not CONFIG_PATH.exists():
        rich.print("[red] Not logged in. Please run 'mp dev-env login' first. [/red]")
        raise typer.Exit(1)
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def get_backend_api(config: dict[str, str]) -> api.BackendAPI:
    """Initialize and authenticates the backend API client.

    Args:
        config: Dictionary containing 'api_root' and either 'api_key'
            or 'username' and 'password'.

    Returns:
        An authenticated BackendAPI instance.

    Raises:
        typer.Exit: If authentication fails or configuration is missing.

    """
    try:
        if config.get("api_key"):
            backend_api = api.BackendAPI(api_root=config["api_root"], api_key=config["api_key"])
        else:
            backend_api = api.BackendAPI(
                api_root=config["api_root"],
                username=config["username"],
                password=config["password"],
            )
            backend_api.login()

        return backend_api  # noqa: TRY300

    except Exception as e:
        rich.print(f"[red]Authentication failed: {e}[/red]")
        raise typer.Exit(1) from e
