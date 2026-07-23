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
from typing import Any

import typer

from mp.dev_env import api

logger: logging.Logger = logging.getLogger(__name__)


CONFIG_PATH: Path = Path.home() / ".mp_dev_env.json"


def load_dev_env_config() -> dict[str, str]:
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

    except Exception as e:
        logger.exception("Authentication failed")
        raise typer.Exit(1) from e
    else:
        return backend_api


def find_entity_identifier(
    entity_name_or_id: str | int,
    installed_entities: list[dict[str, Any]] | None,
    entity_type_name: str,
    id_keys: tuple[str, ...] = ("Identifier", "identifier", "Id", "id"),
    name_keys: tuple[str, ...] = ("Name", "name", "DisplayName", "displayName"),
) -> int | str | None:
    """Find the entity identifier matching the given name or identifier.

    Args:
        entity_name_or_id: The entity name or identifier to search for.
        installed_entities: The list of installed entities fetched from SOAR.
        entity_type_name: Name of the entity type for logging (e.g., 'View', 'Custom Field').
        id_keys: Keys to check for the identifier.
        name_keys: Keys to check for the name.

    Returns:
        The matching entity identifier.

    Raises:
        typer.Exit: If the entity is not found in the installed entities.

    """
    str_entity_name_or_id = str(entity_name_or_id)

    for entity in installed_entities or []:
        identifier = None
        for key in id_keys:
            if key in entity and entity[key] is not None:
                identifier = entity[key]
                break

        name_values_lower = [str(entity[key]).lower() for key in name_keys if key in entity and entity[key] is not None]

        str_identifier = str(identifier) if identifier is not None else None

        if str_identifier and (
            str_entity_name_or_id.lower() == str_identifier.lower()
            or str_entity_name_or_id.lower() in name_values_lower
        ):
            return identifier

    logger.error("%s '%s' not found in installed entities in SOAR platform.", entity_type_name, entity_name_or_id)
    raise typer.Exit(1)
