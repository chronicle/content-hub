"""Module for managing the application's configuration using a config.ini file."""

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

import configparser
import dataclasses
import functools
import typing
import warnings
from pathlib import Path
from typing import TypeVar

import typer
from platformdirs import user_config_dir

import mp.core.constants

from .utils import is_ci_cd

APP_AUTHOR: str = "Google"
APP_NAME: str = "mp-cli-tool"
MP_CACHE_DIR: Path = Path(user_config_dir(APP_NAME, APP_AUTHOR))
CONFIG_FILE_NAME: str = ".mp_config"
if is_ci_cd():
    CONFIG_PATH: Path = Path.home() / CONFIG_FILE_NAME
else:
    CONFIG_PATH: Path = MP_CACHE_DIR / CONFIG_FILE_NAME

MARKETPLACE_PATH_KEY: str = "marketplace_path"
PROCESSES_NUMBER_KEY: str = "processes"
VERBOSE_LOG_KEY: str = "is_verbose"
QUIET_LOG_KEY: str = "is_quiet"
DEFAULT_SECTION_NAME: str = "DEFAULT"
RUNTIME_SECTION_NAME: str = "RUNTIME"
PROCESSES_MIN_VALUE: int = 1
PROCESSES_MAX_VALUE: int = 10
DEFAULT_PROCESSES_NUMBER: int = 5
DEFAULT_QUIET_VALUE: str = "no"
DEFAULT_VERBOSE_VALUE: str = "no"
DEFAULT_MARKETPLACE_PATH: Path = Path.home() / mp.core.constants.REPO_NAME


def get_marketplace_path() -> Path:
    """Get the marketplace path as a `pathlib.Path` object.

    Returns:
        The marketplace path as a `pathlib.Path` object.

    Raises:
        ValueError: when `None` is the configured value

    """
    path: Path | None = _get_config_key(DEFAULT_SECTION_NAME, MARKETPLACE_PATH_KEY, Path)
    msg: str
    if path is None:
        msg = "Got 'None' for content-hub path"
        raise ValueError(msg)

    if not path.exists():
        msg = (
            f"Content Hub path '{path}' does not exist."
            " Please use 'mp config --root-path ...' to set it to the repo's"
            " root directory"
        )
        warnings.warn(msg, RuntimeWarning, stacklevel=2)

    return path.expanduser().resolve().absolute()


def set_marketplace_path(p: Path, /) -> None:
    """Set the marketplace path."""
    _set_config_key(
        DEFAULT_SECTION_NAME,
        MARKETPLACE_PATH_KEY,
        value=p.resolve().absolute().expanduser(),
    )


def get_processes_number() -> int:
    """Get the number of processes configured for the project.

    Returns:
        The number of processes configured for the project.

    Raises:
        ValueError: when `None` is the configured value

    """
    p: int | None = _get_config_key(DEFAULT_SECTION_NAME, PROCESSES_NUMBER_KEY, int)
    if p is None:
        msg: str = "Got 'None' for processes number"
        raise ValueError(msg)

    return p


def set_processes_number(n: int, /) -> None:
    """Set the number of processes for the project."""
    _set_config_key(DEFAULT_SECTION_NAME, PROCESSES_NUMBER_KEY, value=n)


def is_verbose() -> bool:
    """Check whether verbose logging is enabled for the project.

    Returns:
        Whether the script logging mode is set to verbose

    Raises:
        ValueError: when `None` is the configured value

    """
    v: bool | None = _get_config_key(RUNTIME_SECTION_NAME, VERBOSE_LOG_KEY, bool)
    if v is None:
        msg: str = "Got 'None' for verbose"
        raise ValueError(msg)

    return v


def set_is_verbose(*, value: bool) -> None:
    """Set if verbose logging is enabled for the project."""
    b: str = "no"
    if value is True:
        b = "yes"

    _set_config_key(RUNTIME_SECTION_NAME, VERBOSE_LOG_KEY, value=b)


def is_quiet() -> bool:
    """Check whether quiet logging is enabled for the project.

    Returns:
        Whether the script logging mode is set to quiet

    Raises:
        ValueError: when `None` is the configured value

    """
    q: bool | None = _get_config_key(RUNTIME_SECTION_NAME, QUIET_LOG_KEY, bool)
    if q is None:
        msg: str = "Got 'None' for quiet"
        raise ValueError(msg)

    return q


def set_is_quiet(*, value: bool) -> None:
    """Set if quiet logging is enabled for the project."""
    b: str = "no"
    if value is True:
        b = "yes"

    _set_config_key(RUNTIME_SECTION_NAME, QUIET_LOG_KEY, value=b)


_T = TypeVar("_T", int | bool | float, Path)


@functools.lru_cache
def _get_config_key(section: str, key: str, val_type: type[_T], /) -> _T | None:
    config: configparser.ConfigParser = _read_config_if_exists_or_create_defaults()
    if val_type is bool:
        return typing.cast("_T | None", config[section].getboolean(key))

    if val_type is int:
        return typing.cast("_T | None", config[section].getint(key))

    if val_type is float:
        return typing.cast("_T | None", config[section].getfloat(key))

    if val_type is Path:
        return val_type(config.get(section, key))

    msg: str = f"Unsupported type {val_type}"
    raise ValueError(msg)


def _set_config_key(section: str, key: str, *, value: str | bool | int | Path) -> None:
    config: configparser.ConfigParser = _read_config_if_exists_or_create_defaults()
    config[section][key] = str(value)
    _write_config_to_file(config)


def _read_config_if_exists_or_create_defaults() -> configparser.ConfigParser:
    config: configparser.ConfigParser = configparser.ConfigParser()
    CONFIG_PATH.touch()
    config.read(CONFIG_PATH)
    _add_defaults_to_config(config)
    return config


def _add_defaults_to_config(config: configparser.ConfigParser) -> None:
    if DEFAULT_SECTION_NAME not in config or not config[DEFAULT_SECTION_NAME]:
        _create_default_config(config)
        _write_config_to_file(config)

    if RUNTIME_SECTION_NAME not in config or not config[RUNTIME_SECTION_NAME]:
        _create_runtime_config(config)
        _write_config_to_file(config)


def _create_default_config(config: configparser.ConfigParser) -> None:
    mp_path: Path = DEFAULT_MARKETPLACE_PATH.expanduser().resolve().absolute()
    config[DEFAULT_SECTION_NAME] = {
        MARKETPLACE_PATH_KEY: str(mp_path),
        PROCESSES_NUMBER_KEY: str(DEFAULT_PROCESSES_NUMBER),
    }


def _create_runtime_config(config: configparser.ConfigParser) -> None:
    config[RUNTIME_SECTION_NAME] = {
        VERBOSE_LOG_KEY: DEFAULT_VERBOSE_VALUE,
        QUIET_LOG_KEY: DEFAULT_QUIET_VALUE,
    }


def _write_config_to_file(config: configparser.ConfigParser) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as config_file:
        config.write(config_file)


@dataclasses.dataclass(slots=True, frozen=True)
class RuntimeParams:
    quiet: bool
    verbose: bool

    def set_in_config(self) -> None:
        """Set the runtime parameters in the global configuration."""
        self.validate()
        set_is_quiet(value=self.quiet)
        set_is_verbose(value=self.verbose)

    def validate(self) -> None:
        """Validate the runtime parameters.

        Raises:
            typer.BadParameter: If the runtime parameters are invalid.

        """
        if self.verbose and self.quiet:
            msg: str = "Cannot use --quiet and --verbose together"
            raise typer.BadParameter(msg)
