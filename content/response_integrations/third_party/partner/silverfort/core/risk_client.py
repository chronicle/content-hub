"""Risk API client for Silverfort integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from TIPCommon.base.interfaces import Apiable  # type: ignore[import-not-found]

from .api_utils import get_full_url, validate_response
from .constants import REQUEST_TIMEOUT
from .data_models import EntityRisk, RiskUpdate

if TYPE_CHECKING:
    from requests import Response, Session
    from TIPCommon.base.interfaces.logger import ScriptLogger  # type: ignore[import-not-found]
    from TIPCommon.types import SingleJson  # type: ignore[import-not-found]


class RiskApiParameters(NamedTuple):
    """Parameters for Risk API client."""

    api_root: str


class RiskApiClient(Apiable):
    """Client for Silverfort Risk API."""

    def __init__(
        self,
        authenticated_session: Session,
        configuration: RiskApiParameters,
        logger: ScriptLogger,
    ) -> None:
        """Initialize the Risk API client.

        Args:
            authenticated_session: Authenticated requests session.
            configuration: API configuration parameters.
            logger: Logger instance.
        """
        super().__init__(
            authenticated_session=authenticated_session,
            configuration=configuration,
        )
        self.logger: ScriptLogger = logger
        self.api_root: str = configuration.api_root

    def test_connectivity(self) -> bool:
        """Test connectivity to the Risk API.

        Returns:
            True if connectivity test succeeds.
        """
        # Try to get risk for a test entity - this will fail if auth is incorrect
        # We don't care about the result, just that the API responds
        url: str = get_full_url(self.api_root, "get_entity_risk")
        params: dict[str, str] = {"user_principal_name": "test@test.com"}
        response: Response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        # Accept both success (200) and not found (404/400) as valid connectivity
        if response.status_code in (200, 400, 404):
            return True
        validate_response(response, "Risk API connectivity test failed")
        return True

    def get_entity_risk(
        self,
        user_principal_name: str | None = None,
        resource_name: str | None = None,
    ) -> EntityRisk:
        """Get risk information for a user or resource.

        Args:
            user_principal_name: The user principal name (e.g., user@domain.com).
            resource_name: The resource name (for non-user entities).

        Returns:
            EntityRisk object with risk information.

        Raises:
            ValueError: If neither user_principal_name nor resource_name is provided.
        """
        if not user_principal_name and not resource_name:
            raise ValueError("Either user_principal_name or resource_name must be provided")

        url: str = get_full_url(self.api_root, "get_entity_risk")
        params: dict[str, str] = {}

        if user_principal_name:
            params["user_principal_name"] = user_principal_name
        if resource_name:
            params["resource_name"] = resource_name

        self.logger.info(f"Getting entity risk for: {params}")
        response: Response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        validate_response(response, "Failed to get entity risk")

        data: SingleJson = response.json()
        self.logger.info(f"Successfully retrieved entity risk: {data}")

        return EntityRisk.from_json(data)

    def update_entity_risk(
        self,
        user_principal_name: str,
        risks: dict[str, RiskUpdate],
    ) -> bool:
        """Update risk information for a user entity.

        Args:
            user_principal_name: The user principal name to update.
            risks: Dictionary mapping risk types to RiskUpdate objects.

        Returns:
            True if update was successful.

        Example:
            risks = {
                "activity_risk": RiskUpdate(
                    severity="medium",
                    valid_for=24,
                    description="Suspicious activity detected"
                ),
                "malware_risk": RiskUpdate(
                    severity="high",
                    valid_for=48,
                    description="Malware indicator found"
                )
            }
            client.update_entity_risk("user@domain.com", risks)
        """
        url: str = get_full_url(self.api_root, "update_entity_risk")

        payload: SingleJson = {
            "user_principal_name": user_principal_name,
            "risks": {risk_type: risk.to_json() for risk_type, risk in risks.items()},
        }

        self.logger.info(f"Updating entity risk for: {user_principal_name}")
        response: Response = self.session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        validate_response(response, "Failed to update entity risk")

        self.logger.info(f"Successfully updated entity risk for: {user_principal_name}")
        return True
