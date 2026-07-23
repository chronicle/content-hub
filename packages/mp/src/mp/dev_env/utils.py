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
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer

from mp.dev_env import api, chronicle_api

if TYPE_CHECKING:
    from mp.dev_env.interfaces import DevEnvClient

logger: logging.Logger = logging.getLogger(__name__)


CONFIG_PATH: Path = Path.home() / ".mp_dev_env.json"


def load_dev_env_config() -> dict[str, Any]:
    """Load the dev environment configuration from the config file.

    Returns:
        dict: The loaded configuration.

    Raises:
        typer.Exit: If the config file does not exist.

    """
    if not CONFIG_PATH.exists():
        logger.error(" Not logged in. Please run 'mp dev-env login' first. ")
        raise typer.Exit(1)
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _infer_auth_mode(config: dict[str, Any]) -> str:
    """Determine the auth mode for a legacy config that predates the ``auth_mode`` key.

    Older ``mp login`` versions wrote every credential field, using ``null`` for the ones
    that didn't apply, so a truthy ``api_key`` reliably means api-key mode and anything else
    means username/password. New configs always store ``auth_mode`` explicitly and never
    reach this fallback.

    Args:
        config: A raw configuration dictionary with no ``auth_mode`` key.

    Returns:
        'api_key' if an API key is present, otherwise 'user_pass'.

    """
    if config.get("api_key"):
        return "api_key"
    return "user_pass"


def _build_client(auth_mode: str, config: dict[str, Any]) -> DevEnvClient:
    """Construct (without authenticating) the backend client for the given auth mode.

    Args:
        auth_mode: One of 'api_key', 'user_pass', or 'gcp'.
        config: The loaded dev-env configuration.

    Returns:
        An unauthenticated client implementing the DevEnvClient protocol.

    Raises:
        typer.Exit: If the auth mode is unknown.

    """
    if auth_mode == "api_key":
        return api.BackendAPI(api_root=config["api_root"], api_key=config["api_key"])
    if auth_mode == "user_pass":
        return api.BackendAPI(
            api_root=config["api_root"],
            username=config["username"],
            password=config["password"],
        )
    if auth_mode == "gcp":
        return chronicle_api.ChronicleClient(
            project=config["project"],
            location=config["location"],
            instance=config["instance"],
            credentials_file=config.get("credentials_file"),
        )

    logger.error("Unknown auth_mode in config: %s", auth_mode)
    raise typer.Exit(1)


def get_backend_api(config: dict[str, Any]) -> DevEnvClient:
    """Initialize and authenticate the backend client for the configured auth mode.

    Supports three modes: 'api_key' and 'user_pass' (legacy Siemplify SOAR API) and 'gcp'
    (Chronicle API via Application Default Credentials). Configs lacking an 'auth_mode' key
    are treated as legacy for backward compatibility.

    Args:
        config: The loaded dev-env configuration.

    Returns:
        An authenticated client implementing the DevEnvClient protocol.

    Raises:
        typer.Exit: If authentication fails or the configuration is invalid.

    """
    auth_mode: str = config.get("auth_mode") or _infer_auth_mode(config)

    try:
        client: DevEnvClient = _build_client(auth_mode, config)
        client.login()
    except typer.Exit:
        raise
    except Exception as e:
        logger.exception("Authentication failed")
        raise typer.Exit(1) from e
    else:
        return client
