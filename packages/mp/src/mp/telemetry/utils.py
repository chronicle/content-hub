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

import hashlib
import uuid
from pathlib import Path

import yaml

from mp.core.utils import get_current_platform
from mp.telemetry.constants import CONFIG_FILE_PATH, MP_CACHE_DIR, ConfigYaml


def get_or_create_config_yaml() -> ConfigYaml:
    """Load the configuration from the config YAML file.

    If the config file doesn't exist, it will be created with default values.
    Handles YAML parsing errors by recreating the config file.

    Returns:
        ConfigYaml: The loaded or newly created configuration.

    """
    if not CONFIG_FILE_PATH.exists():
        config_yaml: ConfigYaml = _create_config_yaml()
        _save_config_yaml(config_yaml)
        return config_yaml

    try:
        with CONFIG_FILE_PATH.open(encoding="utf-8") as f:
            config_yaml = yaml.safe_load(f) or {}

    except (yaml.YAMLError, OSError):
        config_yaml: ConfigYaml = _create_config_yaml()
        _save_config_yaml(config_yaml)
        return config_yaml

    return config_yaml


def _save_config_yaml(config_yaml: ConfigYaml) -> None:
    try:
        MP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with CONFIG_FILE_PATH.open("w", encoding="utf-8") as f:
            yaml.safe_dump(config_yaml, f)
    except OSError:
        pass


def fix_missing_keys_and_save_if_fixed(config_yaml: ConfigYaml) -> ConfigYaml:
    """Check the configuration and fix missing values in the config YAML.

    Args:
        config_yaml: The configuration to check.

    Returns:
        The updated configuration.

    """
    if "uuid4" not in config_yaml:
        new_config: ConfigYaml = _create_config_yaml()
        _save_config_yaml(new_config)
        return new_config

    made_changes: bool = False
    if "report" not in config_yaml:
        config_yaml["report"] = True
        made_changes = True

    if "install_id" not in config_yaml:
        base_dir: Path = Path("~").expanduser()
        platform_name = get_current_platform()[0]
        config_yaml["install_id"] = hashlib.sha256(
            f"{base_dir}{platform_name}{config_yaml['uuid4']}".encode()
        ).hexdigest()
        made_changes = True

    if made_changes:
        _save_config_yaml(config_yaml)

    return config_yaml


def _create_config_yaml() -> ConfigYaml:
    base_dir: Path = Path("~").expanduser()
    platform_name = get_current_platform()[0]
    unique_id: str = str(uuid.uuid4())
    hashed_id: str = hashlib.sha256(
        f"{base_dir}{platform_name}{unique_id}".encode(), usedforsecurity=False
    ).hexdigest()
    return ConfigYaml(
        install_id=hashed_id,
        uuid4=unique_id,
        report=True,
    )


def is_report_enabled(config_yaml: ConfigYaml) -> bool:
    """Check if telemetry reporting is enabled.

    Args:
        config_yaml: The configuration object.

    Returns:
        True if reporting is enabled, False otherwise.

    """
    return config_yaml["report"]


def get_install_id(config_yaml: ConfigYaml) -> str:
    """Get the installation ID from the configuration.

    Args:
        config_yaml: The configuration object.

    Returns:
        The installation ID.

    """
    return config_yaml["install_id"]
