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

import functools
import importlib.metadata
import json
import sys
import time
import traceback
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import requests
import typer

from mp.core.utils import get_current_platform, is_ci_cd
from mp.telemetry.constants import (
    ALLOWED_COMMAND_ARGUMENTS,
    ENDPOINT,
    NAME_MAPPER,
    REQUEST_TIMEOUT,
    ConfigYaml,
)
from mp.telemetry.constants import (
    CONFIG_FILE_PATH as CONFIG_FILE_PATH,
)
from mp.telemetry.constants import (
    MP_CACHE_DIR as MP_CACHE_DIR,
)
from mp.telemetry.data_models import TelemetryPayload
from mp.telemetry.utils import get_install_id, is_report_enabled, load_config_yaml

if TYPE_CHECKING:
    from collections.abc import Callable


def track_command(mp_command_function: Callable) -> Callable:
    """A_Decorator function to wrap Typer commands for telemetry reporting.

    Args:
        mp_command_function (Callable): The Typer command function to be decorated.

    Returns:
        Callable: The wrapped function which includes the telemetry logic.

    """

    @functools.wraps(mp_command_function)
    def wrapper(*args: Any, **kwargs: Any) -> None:  # noqa: ANN401, PLR0914
        config_yaml: ConfigYaml = load_config_yaml()
        if is_ci_cd() or not is_report_enabled(config_yaml):
            return mp_command_function(*args, **kwargs)

        start_time: float = time.monotonic()
        error: Exception | None = None
        exit_code: int = 0
        unexpected_exit: bool = False
        stack: str | None = None

        try:
            mp_command_function(*args, **kwargs)
        except typer.Exit as e:
            exit_code = e.exit_code
        except Exception as e:  # noqa: BLE001
            unexpected_exit = True
            raw_stack = traceback.format_exc()
            stack: str = _sanitize_traceback(raw_stack)
            error = e
            exit_code = 1
        finally:
            end_time: float = time.monotonic()
            duration_ms: int = int((end_time - start_time) * 1000)

            tool_version: str = importlib.metadata.version("mp")
            platform_name, platform_version = get_current_platform()

            error_type = type(error).__name__ if error else None
            safe_args: dict[str, Any] = _filter_command_arguments(kwargs)
            command_args_str: str = json.dumps(safe_args) if safe_args else None

            payload = TelemetryPayload(
                install_id=get_install_id(config_yaml),
                tool="mp",
                tool_version=tool_version,
                python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                platform=platform_name,
                platform_version=platform_version,
                command=_determine_command_name(mp_command_function.__name__, **kwargs),
                command_args=command_args_str,
                duration_ms=duration_ms,
                success=bool(not unexpected_exit),
                exit_code=exit_code,
                error_type=error_type,
                stack=stack,
                timestamp=datetime.now(UTC),
            )

            send_telemetry_report(payload)

            if error:
                raise error
            if exit_code != 0:
                raise typer.Exit(code=exit_code)

    return wrapper


def send_telemetry_report(event_payload: TelemetryPayload) -> None:
    """Send a telemetry event to the cloud run endpoint."""
    try:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        requests.post(
            ENDPOINT,
            data=json.dumps(event_payload.to_dict()),
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

    except requests.RequestException:
        pass


def _filter_command_arguments(kwargs: dict[Any, Any]) -> dict[str, Any]:
    sanitized_args = {}
    for key, value in kwargs.items():
        if key in ALLOWED_COMMAND_ARGUMENTS:
            sanitized_value = _sanitize_argument_value(value)
            if sanitized_value is not None:
                sanitized_args[key] = sanitized_value
    return sanitized_args


def _sanitize_argument_value(value: Enum | list[Any] | tuple[Any] | Any) -> Any:  # noqa: ANN401
    if isinstance(value, Enum):
        return value.value

    if isinstance(value, (list, tuple)):
        if not value:
            return None
        if len(value) == 1:
            return _sanitize_argument_value(value[0])
        return [_sanitize_argument_value(item) for item in value]

    return value


def _sanitize_traceback(raw_stack: str) -> str:
    home = Path("~").expanduser()
    return raw_stack.replace(home, "<HOME>")


def _determine_command_name(command: str, **kwargs: dict[str, Any]) -> str:
    command = NAME_MAPPER[command]

    if command not in {"build", "validate"}:
        return command

    repo_values = {r.value for r in kwargs.get("repositories", [])}
    has_integrations = bool(kwargs.get("integrations"))
    has_playbooks = bool(kwargs.get("playbooks"))

    if has_integrations or "third_party" in repo_values or "commercial" in repo_values:
        return f"{command} integrations"

    if has_playbooks or "playbooks" in repo_values:
        return f"{command} playbooks"

    return command
