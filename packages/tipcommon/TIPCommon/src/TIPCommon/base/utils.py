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

from typing import Any, Coroutine, Iterable

import asyncio
import sys
import requests

import SiemplifyVaultUtils
from SiemplifyAction import SiemplifyAction
from SiemplifyConnectors import SiemplifyConnectorExecution
from SiemplifyJob import SiemplifyJob
from SiemplifyLogger import SiemplifyLogger
from SiemplifyUtils import my_stdout

from .interfaces.logger import Logger, ScriptLogger
from ..data_models import Container
from ..exceptions import ActionSetupError
from ..types import ChronicleSOAR, Entity, GeneralFunction, SingleJson


class CreateSession:
    @staticmethod
    def create_session() -> requests.Session:
        return requests.Session()


def create_soar_action() -> SiemplifyAction:
    return SiemplifyAction()


def create_soar_job() -> SiemplifyJob:
    return SiemplifyJob()


def create_soar_connector() -> SiemplifyConnectorExecution:
    return SiemplifyConnectorExecution()


def create_params_container() -> Container:
    return Container()


def create_logger(chronicle_soar: ChronicleSOAR) -> ScriptLogger:
    return NewLineLogger(chronicle_soar.LOGGER)


def nativemethod(method: GeneralFunction) -> GeneralFunction:
    """Decorator that marks a method as native.

    Args:
        method (function): The method to mark as native.

    Returns:
        function: The decorated method.
    """
    method.is_native = True
    return method


def is_native(method: GeneralFunction) -> bool:
    """Returns True if the method is marked as native, False otherwise.

    Args:
        method (function): The method to check.

    Returns:
        bool: True if the method is marked as native, False otherwise.
    """
    if hasattr(method, "is_native"):
        return method.is_native
    return False


def validate_manager(manager: Any) -> None:
    if manager is None:
        raise ActionSetupError(
            "Cannot run this action without a manager! (manager is None)\n"
        )


def validate_entity(entity: Entity) -> None:
    if entity is None:
        raise ActionSetupError(
            "Cannot run this action on null entity! (entity is None\n"
        )


class NewLineLogger(Logger):
    def __init__(self, logger: SiemplifyLogger) -> None:
        self.logger = logger

    def debug(self, msg: str, *args, **kwargs) -> None:
        self.logger.info(f"{msg}\n", *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        self.logger.info(f"{msg}\n", *args, **kwargs)

    def warn(self, warning_msg: str, *args, **kwargs) -> None:
        self.logger.warn(f"{warning_msg}\n", *args, **kwargs)

    def error(self, error_msg: str, *args, **kwargs) -> None:
        self.logger.error(f"{error_msg}\n", *args, **kwargs)

    def exception(self, ex: Exception, *args, **kwargs) -> None:
        self.logger.exception(ex, *args, **kwargs)


def coros_to_tasks_with_limit(
        coros: Iterable[Coroutine],
        limit: int
) -> list[asyncio.Task]:
    """Rate limit number of coroutines that can be executed simultaneously.

    Wrap all coroutines in tasks for easy scheduling / dismissing.

    Args:
        coros (Iterable[Coroutine]): iterable containing coroutines to be executed
        limit (int): maximum number of coroutines to be executed in parallel

    Returns:
        list[asyncio.Task]: list of wrapped coroutines enclosed into asyncio.Semaphore
    """
    sem = asyncio.Semaphore(limit)

    async def await_coro(coro: Coroutine):
        async with sem:
            return await coro

    return [
        asyncio.create_task(await_coro(coro)) for coro in coros
    ]


def async_output_handler(func):
    """Wrap script execution coroutine to catch exceptions and provide proper output."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception:
            sys.stderr.write("STDOUT:\n")
            sys.stderr.write(my_stdout.getvalue())
            sys.stderr.write("STDERR:\n")
            raise

    return wrapper


def get_param_value_from_vault(vault_settings: SingleJson, param_value: str) -> str:
    """Get parameter value from vault.

    Args:
        vault_settings (SingleJson): Vault settings JSON.
        param_value (str): Parameter value which may contain vault placeholder.

    Returns:
        str: Parameter value retrieved from vault.
    """
    return SiemplifyVaultUtils.extract_vault_param(param_value, vault_settings)
