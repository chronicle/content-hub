"""Service Account API client for Silverfort integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from TIPCommon.base.interfaces import Apiable  # type: ignore[import-not-found]

from .api_utils import get_full_url, validate_response
from .constants import DEFAULT_PAGE_NUMBER, DEFAULT_PAGE_SIZE, REQUEST_TIMEOUT, SA_INDEX_FIELDS
from .data_models import (
    AllowedEndpoint,
    ServiceAccount,
    ServiceAccountPolicy,
    ServiceAccountsListResult,
)

if TYPE_CHECKING:
    from requests import Response, Session
    from TIPCommon.base.interfaces.logger import ScriptLogger  # type: ignore[import-not-found]
    from TIPCommon.types import SingleJson  # type: ignore[import-not-found]


class ServiceAccountApiParameters(NamedTuple):
    """Parameters for Service Account API client."""

    api_root: str


class ServiceAccountApiClient(Apiable):
    """Client for Silverfort Service Accounts API."""

    def __init__(
        self,
        authenticated_session: Session,
        configuration: ServiceAccountApiParameters,
        logger: ScriptLogger,
    ) -> None:
        """Initialize the Service Account API client.

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
        """Test connectivity to the Service Accounts API.

        Returns:
            True if connectivity test succeeds.
        """
        # Try to list service accounts with minimal data
        url: str = get_full_url(self.api_root, "list_service_accounts")
        payload: SingleJson = {
            "page_size": 1,
            "page_number": 1,
            "fields": ["guid"],
        }
        response: Response = self.session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        validate_response(response, "Service Accounts API connectivity test failed")
        return True

    def get_service_account(self, guid: str) -> ServiceAccount:
        """Get service account details by GUID.

        Args:
            guid: The GUID of the service account.

        Returns:
            ServiceAccount object with account details.
        """
        url: str = get_full_url(self.api_root, "get_service_account", guid=guid)

        self.logger.info(f"Getting service account: {guid}")
        response: Response = self.session.get(url, timeout=REQUEST_TIMEOUT)
        validate_response(response, f"Failed to get service account: {guid}")

        data: SingleJson = response.json()
        self.logger.info(f"Successfully retrieved service account: {guid}")

        return ServiceAccount.from_json(data)

    def list_service_accounts(
        self,
        page_size: int = DEFAULT_PAGE_SIZE,
        page_number: int = DEFAULT_PAGE_NUMBER,
        fields: list[str] | None = None,
    ) -> ServiceAccountsListResult:
        """List service accounts with pagination.

        Args:
            page_size: Number of results per page (default: 50).
            page_number: Page number to retrieve (default: 1).
            fields: List of fields to include in response. If None, includes all fields.

        Returns:
            ServiceAccountsListResult with list of service accounts.
        """
        url: str = get_full_url(self.api_root, "list_service_accounts")

        # Use all fields if not specified
        if fields is None:
            fields = SA_INDEX_FIELDS

        payload: SingleJson = {
            "page_size": page_size,
            "page_number": page_number,
            "fields": fields,
        }

        self.logger.info(f"Listing service accounts: page={page_number}, size={page_size}")
        response: Response = self.session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        validate_response(response, "Failed to list service accounts")

        data: SingleJson = response.json()
        self.logger.info("Successfully retrieved service accounts list")

        # Parse the response
        accounts_data = data.get("service_accounts", data.get("data", []))
        service_accounts = [ServiceAccount.from_json(sa) for sa in accounts_data]

        return ServiceAccountsListResult(
            service_accounts=service_accounts,
            total_count=data.get("total_count"),
            page_number=page_number,
            page_size=page_size,
        )

    def add_service_account(
        self,
        guid: str,
        category: str = "machine_to_machine",
    ) -> bool:
        """Add a service account to protection.

        Args:
            guid: The GUID of the service account.
            category: The category (machine_to_machine, interactive, unknown).

        Returns:
            True if the account was successfully added.
        """
        url: str = get_full_url(self.api_root, "add_service_account", guid=guid)
        payload: SingleJson = {"category": category}

        self.logger.info(f"Adding service account to protection: {guid}")
        response: Response = self.session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        validate_response(response, f"Failed to add service account: {guid}")

        self.logger.info(f"Successfully added service account: {guid}")
        return True

    def get_service_account_policy(self, guid: str) -> ServiceAccountPolicy:
        """Get the policy for a service account.

        Args:
            guid: The GUID of the service account.

        Returns:
            ServiceAccountPolicy object with policy configuration.
        """
        url: str = get_full_url(self.api_root, "get_sa_policy", guid=guid)

        self.logger.info(f"Getting service account policy: {guid}")
        response: Response = self.session.get(url, timeout=REQUEST_TIMEOUT)
        validate_response(response, f"Failed to get service account policy: {guid}")

        data: SingleJson = response.json()
        self.logger.info(f"Successfully retrieved service account policy: {guid}")

        return ServiceAccountPolicy.from_json(data, guid=guid)

    def update_service_account_policy(
        self,
        guid: str,
        enabled: bool | None = None,
        block: bool | None = None,
        send_to_siem: bool | None = None,
        risk_level: str | None = None,
        allow_all_sources: bool | None = None,
        allow_all_destinations: bool | None = None,
        protocols: list[str] | None = None,
        add_allowed_sources: list[AllowedEndpoint] | None = None,
        remove_allowed_sources: list[AllowedEndpoint] | None = None,
        add_allowed_destinations: list[AllowedEndpoint] | None = None,
        remove_allowed_destinations: list[AllowedEndpoint] | None = None,
    ) -> bool:
        """Update the policy for a service account.

        Args:
            guid: The GUID of the service account.
            enabled: Enable or disable the policy.
            block: Enable or disable blocking.
            send_to_siem: Enable or disable SIEM logging.
            risk_level: Risk level threshold (low, medium, high).
            allow_all_sources: Allow all sources.
            allow_all_destinations: Allow all destinations.
            protocols: List of protocols (Kerberos, ldap, ntlm).
            add_allowed_sources: Sources to add to allowlist.
            remove_allowed_sources: Sources to remove from allowlist.
            add_allowed_destinations: Destinations to add to allowlist.
            remove_allowed_destinations: Destinations to remove from allowlist.

        Returns:
            True if the policy was successfully updated.
        """
        url: str = get_full_url(self.api_root, "update_sa_policy", guid=guid)

        payload: SingleJson = {}

        if enabled is not None:
            payload["enabled"] = enabled
        if block is not None:
            payload["block"] = block
        if send_to_siem is not None:
            payload["send_to_siem"] = send_to_siem
        if risk_level is not None:
            payload["risk_level"] = risk_level
        if allow_all_sources is not None:
            payload["allow_all_sources"] = allow_all_sources
        if allow_all_destinations is not None:
            payload["allow_all_destinations"] = allow_all_destinations
        if protocols is not None:
            payload["protocols"] = protocols
        if add_allowed_sources:
            payload["add_allowed_sources"] = [src.to_json() for src in add_allowed_sources]
        if remove_allowed_sources:
            payload["remove_allowed_sources"] = [src.to_json() for src in remove_allowed_sources]
        if add_allowed_destinations:
            payload["add_allowed_destinations"] = [
                dst.to_json() for dst in add_allowed_destinations
            ]
        if remove_allowed_destinations:
            payload["remove_allowed_destinations"] = [
                dst.to_json() for dst in remove_allowed_destinations
            ]

        self.logger.info(f"Updating service account policy: {guid}")
        response: Response = self.session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        validate_response(response, f"Failed to update service account policy: {guid}")

        self.logger.info(f"Successfully updated service account policy: {guid}")
        return True

    def update_service_account(
        self,
        guid: str,
        category: str | None = None,
        owner: str | None = None,
        comment: str | None = None,
    ) -> bool:
        """Update service account attributes.

        Args:
            guid: The GUID of the service account.
            category: The category (machine_to_machine, interactive, unknown).
            owner: The owner GUID.
            comment: Comment for the service account.

        Returns:
            True if the account was successfully updated.
        """
        url: str = get_full_url(self.api_root, "update_service_account", guid=guid)

        payload: SingleJson = {}
        if category is not None:
            payload["category"] = category
        if owner is not None:
            payload["owner"] = owner
        if comment is not None:
            payload["comment"] = comment

        self.logger.info(f"Updating service account: {guid}")
        response: Response = self.session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        validate_response(response, f"Failed to update service account: {guid}")

        self.logger.info(f"Successfully updated service account: {guid}")
        return True
