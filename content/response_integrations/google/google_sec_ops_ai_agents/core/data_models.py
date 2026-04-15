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
