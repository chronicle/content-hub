"""Data models for Silverfort integration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson  # type: ignore[import-not-found]


class IntegrationParameters(NamedTuple):
    """Integration configuration parameters."""

    api_root: str
    external_api_key: str
    verify_ssl: bool
    risk_app_user_id: str | None = None
    risk_app_user_secret: str | None = None
    service_accounts_app_user_id: str | None = None
    service_accounts_app_user_secret: str | None = None
    policies_app_user_id: str | None = None
    policies_app_user_secret: str | None = None


class AppCredentials(NamedTuple):
    """App User credentials for a specific API type."""

    app_user_id: str
    app_user_secret: str


@dataclass(frozen=True, slots=True)
class EntityRisk:
    """Risk information for an entity (user or resource)."""

    user_principal_name: str | None = None
    resource_name: str | None = None
    risk_score: float | None = None
    severity: str | None = None
    risk_factors: list[dict] = field(default_factory=list)
    last_updated: str | None = None

    def to_json(self) -> SingleJson:
        """Convert to JSON representation."""
        result: SingleJson = {}
        if self.user_principal_name:
            result["user_principal_name"] = self.user_principal_name
        if self.resource_name:
            result["resource_name"] = self.resource_name
        if self.risk_score is not None:
            result["risk_score"] = self.risk_score
        if self.severity:
            result["severity"] = self.severity
        if self.risk_factors:
            result["risk_factors"] = self.risk_factors
        if self.last_updated:
            result["last_updated"] = self.last_updated
        return result

    @classmethod
    def from_json(cls, data: SingleJson) -> EntityRisk:
        """Create from JSON response."""
        return cls(
            user_principal_name=data.get("user_principal_name"),
            resource_name=data.get("resource_name"),
            risk_score=data.get("risk_score"),
            severity=data.get("severity"),
            risk_factors=data.get("risk_factors", []),
            last_updated=data.get("last_updated"),
        )


@dataclass(frozen=True, slots=True)
class RiskUpdate:
    """Risk update information."""

    severity: str
    valid_for: int  # Hours
    description: str

    def to_json(self) -> SingleJson:
        """Convert to JSON representation."""
        return {
            "severity": self.severity,
            "valid_for": self.valid_for,
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class ServiceAccount:
    """Service account information."""

    guid: str
    display_name: str | None = None
    upn: str | None = None
    dn: str | None = None
    spn: str | None = None
    domain: str | None = None
    category: str | None = None
    risk: str | None = None
    predictability: str | None = None
    protected: bool | None = None
    owner: str | None = None
    comment: str | None = None
    sources_count: int | None = None
    destinations_count: int | None = None
    number_of_authentications: int | None = None
    creation_date: str | None = None
    highly_privileged: bool | None = None
    interactive_login: bool | None = None
    broadly_used: bool | None = None
    suspected_brute_force: bool | None = None
    repetitive_behavior: bool | None = None
    account_type: str | None = None

    def to_json(self) -> SingleJson:
        """Convert to JSON representation."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_json(cls, data: SingleJson) -> ServiceAccount:
        """Create from JSON response."""
        return cls(
            guid=data.get("guid", ""),
            display_name=data.get("display_name"),
            upn=data.get("upn"),
            dn=data.get("dn"),
            spn=data.get("spn"),
            domain=data.get("domain"),
            category=data.get("category"),
            risk=data.get("risk"),
            predictability=data.get("predictability"),
            protected=data.get("protected"),
            owner=data.get("owner"),
            comment=data.get("comment"),
            sources_count=data.get("sources_count"),
            destinations_count=data.get("destinations_count"),
            number_of_authentications=data.get("number_of_authentications"),
            creation_date=data.get("creation_date"),
            highly_privileged=data.get("highly_privileged"),
            interactive_login=data.get("interactive_login"),
            broadly_used=data.get("broadly_used"),
            suspected_brute_force=data.get("suspected_brute_force"),
            repetitive_behavior=data.get("repetitive_behavior"),
            account_type=data.get("type"),
        )


@dataclass(frozen=True, slots=True)
class AllowedEndpoint:
    """Allowed source or destination endpoint."""

    key: str
    key_type: str  # ip, hostname, dn, etc.

    def to_json(self) -> SingleJson:
        """Convert to JSON representation."""
        return {"key": self.key, "key_type": self.key_type}

    @classmethod
    def from_json(cls, data: SingleJson) -> AllowedEndpoint:
        """Create from JSON response."""
        return cls(key=data.get("key", ""), key_type=data.get("key_type", ""))


@dataclass(slots=True)
class ServiceAccountPolicy:
    """Service account policy configuration."""

    guid: str
    enabled: bool = False
    block: bool = False
    send_to_siem: bool = False
    risk_level: str | None = None
    allow_all_sources: bool = False
    allow_all_destinations: bool = False
    protocols: list[str] = field(default_factory=list)
    allowed_sources: list[AllowedEndpoint] = field(default_factory=list)
    allowed_destinations: list[AllowedEndpoint] = field(default_factory=list)

    def to_json(self) -> SingleJson:
        """Convert to JSON representation."""
        result: SingleJson = {
            "enabled": self.enabled,
            "block": self.block,
            "send_to_siem": self.send_to_siem,
            "allow_all_sources": self.allow_all_sources,
            "allow_all_destinations": self.allow_all_destinations,
        }
        if self.risk_level:
            result["risk_level"] = self.risk_level
        if self.protocols:
            result["protocols"] = self.protocols
        return result

    @classmethod
    def from_json(cls, data: SingleJson, guid: str = "") -> ServiceAccountPolicy:
        """Create from JSON response."""
        allowed_sources = [
            AllowedEndpoint.from_json(src) for src in data.get("allowed_sources", [])
        ]
        allowed_destinations = [
            AllowedEndpoint.from_json(dst) for dst in data.get("allowed_destinations", [])
        ]
        return cls(
            guid=guid,
            enabled=data.get("enabled", False),
            block=data.get("block", False),
            send_to_siem=data.get("send_to_siem", False),
            risk_level=data.get("risk_level"),
            allow_all_sources=data.get("allow_all_sources", False),
            allow_all_destinations=data.get("allow_all_destinations", False),
            protocols=data.get("protocols", []),
            allowed_sources=allowed_sources,
            allowed_destinations=allowed_destinations,
        )


@dataclass(frozen=True, slots=True)
class PolicyIdentifier:
    """Policy user or group identifier."""

    identifier_type: str
    identifier: str
    display_name: str | None = None
    domain: str | None = None

    def to_json(self) -> SingleJson:
        """Convert to JSON representation."""
        result: SingleJson = {
            "identifierType": self.identifier_type,
            "identifier": self.identifier,
        }
        if self.display_name:
            result["displayName"] = self.display_name
        if self.domain:
            result["domain"] = self.domain
        return result

    @classmethod
    def from_json(cls, data: SingleJson) -> PolicyIdentifier:
        """Create from JSON response."""
        return cls(
            identifier_type=data.get("identifierType", ""),
            identifier=data.get("identifier", ""),
            display_name=data.get("displayName"),
            domain=data.get("domain"),
        )


@dataclass(frozen=True, slots=True)
class PolicyDestination:
    """Policy destination configuration."""

    identifier_type: str
    identifier: str
    display_name: str | None = None
    domain: str | None = None
    services: list[str] = field(default_factory=list)

    def to_json(self) -> SingleJson:
        """Convert to JSON representation."""
        result: SingleJson = {
            "identifierType": self.identifier_type,
            "identifier": self.identifier,
        }
        if self.display_name:
            result["displayName"] = self.display_name
        if self.domain:
            result["domain"] = self.domain
        if self.services:
            result["services"] = self.services
        return result

    @classmethod
    def from_json(cls, data: SingleJson) -> PolicyDestination:
        """Create from JSON response."""
        return cls(
            identifier_type=data.get("identifierType", ""),
            identifier=data.get("identifier", ""),
            display_name=data.get("displayName"),
            domain=data.get("domain"),
            services=data.get("services", []),
        )


@dataclass(slots=True)
class Policy:
    """Authentication policy configuration."""

    policy_id: str
    policy_name: str | None = None
    enabled: bool = False
    policy_type: str | None = None
    auth_type: str | None = None
    protocols: list[str] = field(default_factory=list)
    action: str | None = None
    mfa_prompt: str | None = None
    all_users_and_groups: bool = False
    users_and_groups: list[PolicyIdentifier] = field(default_factory=list)
    all_devices: bool = False
    sources: list[PolicyIdentifier] = field(default_factory=list)
    all_destinations: bool = False
    destinations: list[PolicyDestination] = field(default_factory=list)
    bridge_type: str | None = None

    def to_json(self) -> SingleJson:
        """Convert to JSON representation."""
        result: SingleJson = {
            "policyId": self.policy_id,
            "enabled": self.enabled,
        }
        if self.policy_name:
            result["policyName"] = self.policy_name
        if self.policy_type:
            result["policyType"] = self.policy_type
        if self.auth_type:
            result["authType"] = self.auth_type
        if self.protocols:
            result["protocols"] = self.protocols
        if self.action:
            result["action"] = self.action
        if self.mfa_prompt:
            result["MFAPrompt"] = self.mfa_prompt
        result["allUsersAndGroups"] = self.all_users_and_groups
        if self.users_and_groups:
            result["usersAndGroups"] = [ug.to_json() for ug in self.users_and_groups]
        result["allDevices"] = self.all_devices
        if self.sources:
            result["sources"] = [src.to_json() for src in self.sources]
        result["allDestinations"] = self.all_destinations
        if self.destinations:
            result["destinations"] = [dst.to_json() for dst in self.destinations]
        if self.bridge_type:
            result["bridgeType"] = self.bridge_type
        return result

    @classmethod
    def from_json(cls, data: SingleJson) -> Policy:
        """Create from JSON response."""
        users_and_groups = [PolicyIdentifier.from_json(ug) for ug in data.get("usersAndGroups", [])]
        sources = [PolicyIdentifier.from_json(src) for src in data.get("sources", [])]
        destinations = [PolicyDestination.from_json(dst) for dst in data.get("destinations", [])]

        return cls(
            policy_id=str(data.get("policyId", data.get("id", ""))),
            policy_name=data.get("policyName"),
            enabled=data.get("enabled", False),
            policy_type=data.get("policyType"),
            auth_type=data.get("authType"),
            protocols=data.get("protocols", []),
            action=data.get("action"),
            mfa_prompt=data.get("MFAPrompt"),
            all_users_and_groups=data.get("allUsersAndGroups", False),
            users_and_groups=users_and_groups,
            all_devices=data.get("allDevices", False),
            sources=sources,
            all_destinations=data.get("allDestinations", False),
            destinations=destinations,
            bridge_type=data.get("bridgeType"),
        )


@dataclass(frozen=True, slots=True)
class ServiceAccountsListResult:
    """Result of listing service accounts."""

    service_accounts: list[ServiceAccount]
    total_count: int | None = None
    page_number: int | None = None
    page_size: int | None = None

    def to_json(self) -> SingleJson:
        """Convert to JSON representation."""
        result: SingleJson = {
            "service_accounts": [sa.to_json() for sa in self.service_accounts],
        }
        if self.total_count is not None:
            result["total_count"] = self.total_count
        if self.page_number is not None:
            result["page_number"] = self.page_number
        if self.page_size is not None:
            result["page_size"] = self.page_size
        return result


@dataclass(frozen=True, slots=True)
class PoliciesListResult:
    """Result of listing policies."""

    policies: list[Policy]

    def to_json(self) -> SingleJson:
        """Convert to JSON representation."""
        return {
            "policies": [policy.to_json() for policy in self.policies],
        }
