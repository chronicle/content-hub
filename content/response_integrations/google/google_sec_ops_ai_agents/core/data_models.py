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

import dataclasses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Self
    from TIPCommon.types import ChronicleSOAR


@dataclasses.dataclass(slots=True, frozen=True)
class IntegrationParameters:
    """Data model for integration parameters."""

    api_root: str
    verify_ssl: bool


@dataclasses.dataclass(slots=True, frozen=True)
class SessionAuthenticationParameters:
    """Data model for session authentication parameters."""

    api_root: str
    chronicle_soar: ChronicleSOAR
    verify_ssl: bool

    @classmethod
    def from_integration_params(
        cls,
        chronicle_soar: ChronicleSOAR,
        integration_params: IntegrationParameters,
    ) -> Self:
        """Create a new instance from integration parameters.

        Args:
            chronicle_soar: The Chronicle SOAR instance.
            integration_params: The integration parameters.

        Returns:
            A new instance of the class.
        """
        return cls(
            api_root=integration_params.api_root,
            verify_ssl=integration_params.verify_ssl,
            chronicle_soar=chronicle_soar,
        )


@dataclasses.dataclass(slots=True, frozen=True)
class ApiParameters:
    """Data model for API parameters."""

    api_root: str

    @classmethod
    def from_integration_params(cls, integration_params: IntegrationParameters) -> Self:
        """Create a new instance from integration parameters.

        Args:
            integration_params: The integration parameters.

        Returns:
            A new instance of the class.
        """
        return cls(
            api_root=integration_params.api_root,
        )
