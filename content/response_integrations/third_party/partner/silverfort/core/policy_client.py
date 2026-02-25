"""Policy API client for Silverfort integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from TIPCommon.base.interfaces import Apiable  # type: ignore[import-not-found]

from .api_utils import get_full_url, validate_response
from .constants import POLICY_INDEX_FIELDS, REQUEST_TIMEOUT
from .data_models import (
    PoliciesListResult,
    Policy,
    PolicyDestination,
    PolicyIdentifier,
)

if TYPE_CHECKING:
    from requests import Response, Session
    from TIPCommon.base.interfaces.logger import ScriptLogger  # type: ignore[import-not-found]
    from TIPCommon.types import SingleJson  # type: ignore[import-not-found]


class PolicyApiParameters(NamedTuple):
    """Parameters for Policy API client."""

    api_root: str


class PolicyApiClient(Apiable):
    """Client for Silverfort Policy API."""

    def __init__(
        self,
        authenticated_session: Session,
        configuration: PolicyApiParameters,
        logger: ScriptLogger,
    ) -> None:
        """Initialize the Policy API client.

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
        """Test connectivity to the Policy API.

        Returns:
            True if connectivity test succeeds.
        """
        # Try to get rules names and IDs - lightweight operation
        url: str = get_full_url(self.api_root, "get_rules_names_and_ids")
        response: Response = self.session.get(url, timeout=REQUEST_TIMEOUT)
        validate_response(response, "Policy API connectivity test failed")
        return True

    def get_policy(self, policy_id: str) -> Policy:
        """Get policy details by ID.

        Args:
            policy_id: The ID of the policy.

        Returns:
            Policy object with policy configuration.
        """
        url: str = get_full_url(self.api_root, "get_policy", policy_id=policy_id)

        self.logger.info(f"Getting policy: {policy_id}")
        response: Response = self.session.get(url, timeout=REQUEST_TIMEOUT)
        validate_response(response, f"Failed to get policy: {policy_id}")

        data: SingleJson = response.json()
        self.logger.info(f"Successfully retrieved policy: {policy_id}")

        return Policy.from_json(data)

    def list_policies(
        self,
        fields: list[str] | None = None,
    ) -> PoliciesListResult:
        """List all policies.

        Args:
            fields: List of fields to include in response. If None, includes all fields.

        Returns:
            PoliciesListResult with list of policies.
        """
        url: str = get_full_url(self.api_root, "list_policies")

        # Use all fields if not specified
        if fields is None:
            fields = POLICY_INDEX_FIELDS

        payload: SingleJson = {"fields": fields}

        self.logger.info("Listing policies")
        response: Response = self.session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        validate_response(response, "Failed to list policies")

        data: SingleJson = response.json()
        self.logger.info("Successfully retrieved policies list")

        # Parse the response - may be a list or dict with policies key
        if isinstance(data, list):
            policies_data = data
        else:
            policies_data = data.get("policies", data.get("data", []))

        policies = [Policy.from_json(p) for p in policies_data]

        return PoliciesListResult(policies=policies)

    def update_policy(
        self,
        policy_id: str,
        enabled: bool | None = None,
        add_users_and_groups: list[PolicyIdentifier] | None = None,
        remove_users_and_groups: list[PolicyIdentifier] | None = None,
        add_sources: list[PolicyIdentifier] | None = None,
        remove_sources: list[PolicyIdentifier] | None = None,
        add_destinations: list[PolicyDestination] | None = None,
        remove_destinations: list[PolicyDestination] | None = None,
    ) -> bool:
        """Update a policy.

        Args:
            policy_id: The ID of the policy to update.
            enabled: Enable or disable the policy.
            add_users_and_groups: Users/groups to add to the policy.
            remove_users_and_groups: Users/groups to remove from the policy.
            add_sources: Sources to add to the policy.
            remove_sources: Sources to remove from the policy.
            add_destinations: Destinations to add to the policy.
            remove_destinations: Destinations to remove from the policy.

        Returns:
            True if the policy was successfully updated.
        """
        url: str = get_full_url(self.api_root, "update_policy", policy_id=policy_id)

        payload: SingleJson = {}

        if enabled is not None:
            payload["enabled"] = enabled
        if add_users_and_groups:
            payload["addUsersAndGroups"] = [ug.to_json() for ug in add_users_and_groups]
        if remove_users_and_groups:
            payload["removeUsersAndGroups"] = [ug.to_json() for ug in remove_users_and_groups]
        if add_sources:
            payload["addSources"] = [src.to_json() for src in add_sources]
        if remove_sources:
            payload["removeSources"] = [src.to_json() for src in remove_sources]
        if add_destinations:
            payload["addDestinations"] = [dst.to_json() for dst in add_destinations]
        if remove_destinations:
            payload["removeDestinations"] = [dst.to_json() for dst in remove_destinations]

        self.logger.info(f"Updating policy: {policy_id}")
        response: Response = self.session.patch(url, json=payload, timeout=REQUEST_TIMEOUT)
        validate_response(response, f"Failed to update policy: {policy_id}")

        self.logger.info(f"Successfully updated policy: {policy_id}")
        return True

    def change_policy_state(self, policy_id: str, state: bool) -> bool:
        """Change the state (enabled/disabled) of a policy.

        Args:
            policy_id: The ID of the policy.
            state: True to enable, False to disable.

        Returns:
            True if the state was successfully changed.
        """
        url: str = get_full_url(self.api_root, "change_policy_state")

        payload: SingleJson = {
            "policy_id": str(policy_id),
            "state": str(state).lower(),
        }

        self.logger.info(f"Changing policy state: {policy_id} -> {state}")
        response: Response = self.session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        validate_response(response, f"Failed to change policy state: {policy_id}")

        self.logger.info(f"Successfully changed policy state: {policy_id} -> {state}")
        return True

    def get_rules_names_and_ids(self) -> list[dict]:
        """Get all policy rules names and IDs.

        Returns:
            List of dictionaries with policy names and IDs.
        """
        url: str = get_full_url(self.api_root, "get_rules_names_and_ids")

        self.logger.info("Getting policy rules names and IDs")
        response: Response = self.session.get(url, timeout=REQUEST_TIMEOUT)
        validate_response(response, "Failed to get policy rules names and IDs")

        data = response.json()
        self.logger.info("Successfully retrieved policy rules names and IDs")

        return data if isinstance(data, list) else []
