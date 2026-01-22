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

"""
context
==========

Module that provides a common interface to read / write context values using any of
existing base classes Action / BaseConnector / Job.

Module provides a factory to get a context object depending on SDK object type.

Example usage:
.. code-block:: python

    from TIPCommon.base.connector import Connector
    from TIPCommon.context import get_context_factory

    chronicle_soar = Connector("Test Connector")
    context_handler = get_context_factory(chronicle_soar)

    context_handler.set_context("test_key", "Test Context")
    val = context_handler.get_context("test_key")
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .base.action import Action
from .base.connector import BaseConnector
from .base.job import Job

from .consts import GLOBAL_CONTEXT_SCOPE
from .types import JsonString


class Context(ABC):
    """Context protocol to have a standard signature across different SDK
    implementations.
    """

    @abstractmethod
    def set_context(self, key: str, value: JsonString) -> None:
        """Set context in the database. It must be a string."""

    @abstractmethod
    def get_context(self, key: str) -> JsonString | None:
        """Get context from the database. The content will be a string"""


def get_context_factory(chronicle_soar: Action | BaseConnector | Job) -> Context:
    """Factory to get a context object depending on SDK object type."""
    if isinstance(chronicle_soar, Job):
        return SiemplifyJobContext(chronicle_soar)

    if isinstance(chronicle_soar, Action):
        return SiemplifyActionContext(chronicle_soar)

    if isinstance(chronicle_soar, BaseConnector):
        return SiemplifyConnectorContext(chronicle_soar)

    raise RuntimeError(
        f"Unsupported SDK object {chronicle_soar} of type {type(chronicle_soar)}"
    )


class SiemplifyJobContext(Context):
    """Context implementations for SiemplifyJob."""

    def __init__(self, _s: Job) -> None:
        self._s: Job = _s

    def get_context(self, key: str) -> JsonString | None:
        return self._s.soar_job.get_scoped_job_context_property(key)

    def set_context(self, key: str, value: JsonString) -> None:
        self._s.soar_job.set_scoped_job_context_property(key, value)


class SiemplifyActionContext(Context):
    """Context implementations for SiemplifyAction."""

    def __init__(self, _s: Action) -> None:
        self._s: Action = _s

    def get_context(self, key: str) -> str | JsonString | None:
        return self._s.soar_action.get_context_property(
            context_type=GLOBAL_CONTEXT_SCOPE,
            identifier=self._s.soar_action.integration_identifier,
            property_key=key,
        )

    def set_context(self, key: str, value: JsonString) -> None:
        self._s.soar_action.set_context_property(
            context_type=GLOBAL_CONTEXT_SCOPE,
            identifier=self._s.soar_action.integration_identifier,
            property_key=key,
            property_value=value,
        )


class SiemplifyConnectorContext(Context):
    """Context implementations for SiemplifyConnectorExecution."""

    def __init__(self, _s: BaseConnector) -> None:
        self._s: BaseConnector = _s

    def get_context(self, key: str) -> str | JsonString | None:
        return self._s.siemplify.get_connector_context_property(
            identifier=self._s.siemplify.context.connector_info.identifier,
            property_key=key,
        )

    def set_context(self, key: str, value: JsonString) -> None:
        self._s.siemplify.set_connector_context_property(
            identifier=self._s.siemplify.context.connector_info.identifier,
            property_key=key,
            property_value=value,
        )
