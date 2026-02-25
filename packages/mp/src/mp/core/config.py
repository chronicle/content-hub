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

import mp.core.constants
from mp.core.logger.setup import setup_logging

CONFIG_FILE_NAME: str = ".mp_config"
CONFIG_PATH: Path = Path.home() / CONFIG_FILE_NAME


MARKETPLACE_PATH_KEY: str = "marketplace_path"
CUSTOM_SRC_KEY: str = "src"
CUSTOM_DST_KEY: str = "dst"
PROCESSES_NUMBER_KEY: str = "processes"
GEMINI_API_KEY_KEY: str = "gemini_api_key"
GEMINI_CONCURRENCY_KEY: str = "gemini_concurrency"
VERBOSE_LOG_KEY: str = "is_verbose"
QUIET_LOG_KEY: str = "is_quiet"
DEFAULT_SECTION_NAME: str = "DEFAULT"
RUNTIME_SECTION_NAME: str = "RUNTIME"
PROCESSES_MIN_VALUE: int = 1
PROCESSES_MAX_VALUE: int = 10
DEFAULT_PROCESSES_NUMBER: int = 5
DEFAULT_GEMINI_CONCURRENCY: int = 5
DEFAULT_QUIET_VALUE: str = "no"
DEFAULT_VERBOSE_VALUE: str = "no"
DEFAULT_MARKETPLACE_PATH: Path = Path.home() / mp.core.constants.REPO_NAME
LOCAL_PACKAGES_PATH: str = "packages"


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


def get_custom_src() -> Path | None:
    """Get the custom source path if configured.

    Returns:
        The custom source path as a `pathlib.Path` object, or None if not set.

    """
    return _get_config_key(RUNTIME_SECTION_NAME, CUSTOM_SRC_KEY, Path)


def set_custom_src(p: Path, /) -> None:
    """Set the custom source path."""
    _set_config_key(
        RUNTIME_SECTION_NAME,
        CUSTOM_SRC_KEY,
        value=p.resolve().absolute().expanduser(),
    )


def clear_custom_src() -> None:
    """Clear the custom source path from the configuration."""
    _remove_config_key(RUNTIME_SECTION_NAME, CUSTOM_SRC_KEY)


def get_custom_dst() -> Path | None:
    """Get the custom destination path if configured.

    Returns:
        The custom destination path as a `pathlib.Path` object, or None if not set.

    """
    return _get_config_key(RUNTIME_SECTION_NAME, CUSTOM_DST_KEY, Path)


def set_custom_dst(p: Path, /) -> None:
    """Set the custom destination path."""
    _set_config_key(
        RUNTIME_SECTION_NAME,
        CUSTOM_DST_KEY,
        value=p.resolve().absolute().expanduser(),
    )


def clear_custom_dst() -> None:
    """Clear the custom destination path from the configuration."""
    _remove_config_key(RUNTIME_SECTION_NAME, CUSTOM_DST_KEY)


def get_local_packages_path() -> Path:
    """Get the local packages' path.

    Returns:
        The local packages path as a `pathlib.Path` object.

    """
    return get_marketplace_path() / LOCAL_PACKAGES_PATH


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


def get_gemini_api_key() -> str | None:
    """Get the API key configured for the project.

    Returns:
        The API key is configured for the project.

    """
    return _get_config_key(DEFAULT_SECTION_NAME, GEMINI_API_KEY_KEY, str)


def set_gemini_api_key(api_key: str, /) -> None:
    """Set the API key for the project."""
    _set_config_key(DEFAULT_SECTION_NAME, GEMINI_API_KEY_KEY, value=api_key)


def get_gemini_concurrency() -> int:
    """Get the maximum number of concurrent actions to describe using Gemini.

    Returns:
        The maximum number of concurrent actions.

    """
    c: int | None = _get_config_key(DEFAULT_SECTION_NAME, GEMINI_CONCURRENCY_KEY, int)
    return c if c is not None else DEFAULT_GEMINI_CONCURRENCY


def set_gemini_concurrency(n: int, /) -> None:
    """Set the maximum number of concurrent actions for Gemini."""
    _set_config_key(DEFAULT_SECTION_NAME, GEMINI_CONCURRENCY_KEY, value=n)


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


_T = TypeVar("_T", int, bool, float, Path, str)


@functools.lru_cache
def _get_config_key(section: str, key: str, val_type: type[_T], /) -> _T | None:
    config: configparser.ConfigParser = _read_config_if_exists_or_create_defaults()
    try:
        if val_type is bool:
            return typing.cast("_T | None", config[section].getboolean(key))

        if val_type is int:
            return typing.cast("_T | None", config[section].getint(key))

        if val_type is float:
            return typing.cast("_T | None", config[section].getfloat(key))

        if val_type is Path:
            val = config.get(section, key, fallback=None)
            return typing.cast("_T | None", val_type(val) if val else None)

    except (configparser.NoOptionError, configparser.NoSectionError, KeyError):
        return None

    if val_type is str:
        return typing.cast("_T | None", config.get(section, key, fallback=None))

    msg: str = f"Unsupported type {val_type}"
    raise ValueError(msg)


def _set_config_key(section: str, key: str, *, value: str | bool | int | Path) -> None:
    config: configparser.ConfigParser = _read_config_if_exists_or_create_defaults()
    if section not in config:
        config.add_section(section)
    config[section][key] = str(value)
    _write_config_to_file(config)
    _get_config_key.cache_clear()


def _remove_config_key(section: str, key: str) -> None:
    config: configparser.ConfigParser = _read_config_if_exists_or_create_defaults()
    if section in config and config.remove_option(section, key):
        _write_config_to_file(config)
        _get_config_key.cache_clear()


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
        GEMINI_CONCURRENCY_KEY: str(DEFAULT_GEMINI_CONCURRENCY),
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
        setup_logging(verbose=self.verbose, quiet=self.quiet)

    def validate(self) -> None:
        """Validate the runtime parameters.

        Raises:
            typer.BadParameter: If the runtime parameters are invalid.

        """
        if self.verbose and self.quiet:
            msg: str = "Cannot use --quiet and --verbose together"
            raise typer.BadParameter(msg)
