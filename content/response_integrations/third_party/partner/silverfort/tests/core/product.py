"""Mock Silverfort product for testing."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from silverfort.tests.common import (
    MOCK_ENTITY_RISK,
    MOCK_POLICIES_LIST,
    MOCK_POLICY,
    MOCK_RULES_NAMES_IDS,
    MOCK_SA_POLICY,
    MOCK_SERVICE_ACCOUNT,
    MOCK_SERVICE_ACCOUNTS_LIST,
)

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson  # type: ignore[import-not-found]


@dataclasses.dataclass(slots=True)
class MockSilverfort:
    """Mock Silverfort API for testing."""

    # Risk API data
    entity_risks: dict[str, SingleJson] = dataclasses.field(default_factory=dict)

    # Service Account API data
    service_accounts: dict[str, SingleJson] = dataclasses.field(default_factory=dict)
    sa_policies: dict[str, SingleJson] = dataclasses.field(default_factory=dict)

    # Policy API data
    policies: dict[str, SingleJson] = dataclasses.field(default_factory=dict)
    rules_names_ids: list[dict] = dataclasses.field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize with default mock data."""
        # Set default entity risk
        self.entity_risks["test.user@example.com"] = MOCK_ENTITY_RISK

        # Set default service accounts
        self.service_accounts["82132169-b41b-8b47-ba4b-494814500785"] = MOCK_SERVICE_ACCOUNT

        # Set default SA policies
        self.sa_policies["82132169-b41b-8b47-ba4b-494814500785"] = MOCK_SA_POLICY

        # Set default policies
        self.policies["1"] = MOCK_POLICY

        # Set default rules names/ids
        self.rules_names_ids = MOCK_RULES_NAMES_IDS

    # Risk API methods
    def get_entity_risk(
        self,
        user_principal_name: str | None = None,
        resource_name: str | None = None,
    ) -> SingleJson:
        """Get entity risk."""
        identifier = user_principal_name or resource_name
        if identifier and identifier in self.entity_risks:
            return self.entity_risks[identifier]
        # Return empty risk for unknown entities
        return {
            "user_principal_name": user_principal_name,
            "resource_name": resource_name,
            "risk_score": 0,
            "severity": "low",
            "risk_factors": [],
        }

    def update_entity_risk(
        self,
        user_principal_name: str,
        risks: SingleJson,
    ) -> SingleJson:
        """Update entity risk."""
        if user_principal_name not in self.entity_risks:
            self.entity_risks[user_principal_name] = {
                "user_principal_name": user_principal_name,
                "risk_factors": [],
            }
        # Update risk factors
        for risk_type, risk_data in risks.items():
            factor = {
                "type": risk_type,
                "severity": risk_data.get("severity"),
                "description": risk_data.get("description"),
            }
            self.entity_risks[user_principal_name]["risk_factors"].append(factor)
        return {"status": "success"}

    # Service Account API methods
    def get_service_account(self, guid: str) -> SingleJson:
        """Get service account."""
        if guid in self.service_accounts:
            return self.service_accounts[guid]
        raise ValueError(f"Service account not found: {guid}")

    def list_service_accounts(
        self,
        page_size: int = 50,
        page_number: int = 1,
        fields: list[str] | None = None,
    ) -> SingleJson:
        """List service accounts."""
        return MOCK_SERVICE_ACCOUNTS_LIST

    def get_sa_policy(self, guid: str) -> SingleJson:
        """Get service account policy."""
        if guid in self.sa_policies:
            return self.sa_policies[guid]
        return MOCK_SA_POLICY

    def update_sa_policy(self, guid: str, policy_data: SingleJson) -> SingleJson:
        """Update service account policy."""
        if guid not in self.sa_policies:
            self.sa_policies[guid] = {}
        self.sa_policies[guid].update(policy_data)
        return {"status": "success"}

    # Policy API methods
    def get_policy(self, policy_id: str) -> SingleJson:
        """Get policy."""
        if policy_id in self.policies:
            return self.policies[policy_id]
        raise ValueError(f"Policy not found: {policy_id}")

    def list_policies(self, fields: list[str] | None = None) -> list[SingleJson]:
        """List policies."""
        return MOCK_POLICIES_LIST

    def update_policy(self, policy_id: str, policy_data: SingleJson) -> SingleJson:
        """Update policy."""
        if policy_id in self.policies:
            self.policies[policy_id].update(policy_data)
        return {"status": "success"}

    def change_policy_state(self, policy_id: str, state: bool) -> SingleJson:
        """Change policy state."""
        if policy_id in self.policies:
            self.policies[policy_id]["enabled"] = state
        return {"status": "success"}

    def get_rules_names_and_ids(self) -> list[dict]:
        """Get rules names and IDs."""
        return self.rules_names_ids
