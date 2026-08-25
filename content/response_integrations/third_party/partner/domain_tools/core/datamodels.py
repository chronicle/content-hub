from __future__ import annotations

import json
import urllib.parse
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


class DTBaseModel:
    IRIS_LINK = "https://iris.domaintools.com/investigate/search/"
    GUIDED_PIVOT_THRESHOLD = 500

    def to_dict(self):
        return asdict(self)

    def to_json(self):
        return json.dumps(self.to_dict())


@dataclass(slots=True)
class RiskProfile:
    risk_score: int
    threats: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Analytics:
    overall_risk_score: int = 0
    proximity_risk_score: int = 0
    malware_risk_score: int = 0
    phishing_risk_score: int = 0
    spam_risk_score: int = 0
    threat_profile_risk_score: RiskProfile = field(default_factory=lambda: RiskProfile)
    website_response_code: int | None = None
    google_adsense: list[dict] = field(default_factory=list)
    google_analytics: list[dict] = field(default_factory=list)
    ga4: list[dict] = field(default_factory=list)
    gtm_codes: list[dict] = field(default_factory=list)
    fb_codes: list[dict] = field(default_factory=list)
    hotjar_codes: list[dict] = field(default_factory=list)
    baidu_codes: list[dict] = field(default_factory=list)
    yandex_codes: list[dict] = field(default_factory=list)
    matomo_codes: list[dict] = field(default_factory=list)
    statcounter_project_codes: list[dict] = field(default_factory=list)
    statcounter_security_codes: list[dict] = field(default_factory=list)
    popularity_rank: int | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class Contact:
    country: str | None = None
    email: str | None = None
    name: str | None = None
    phone: str | None = None
    street: str | None = None
    city: str | None = None
    state: str | None = None
    postal: str | None = None
    org: str | None = None


@dataclass(slots=True)
class Identity:
    registrant_name: dict | None = None
    registrant_org: dict | None = None
    registrar: dict | None = None
    soa_email: list[str] = field(default_factory=list)
    ssl_email: list[str] = field(default_factory=list)
    email_domains: list[dict] = field(default_factory=list)
    additional_whois_emails: list[str] = field(default_factory=list)
    registrant_contact: Contact | None = None
    admin_contact: Contact | None = None
    technical_contact: Contact | None = None
    billing_contact: Contact | None = None


@dataclass(slots=True)
class Registration:
    registrar_status: list[str] = field(default_factory=list)
    domain_status: bool = False
    create_date: dict | None = None
    expiration_date: dict | None = None


@dataclass(slots=True)
class Hosting:
    ip_addresses: list[dict] = field(default_factory=list)
    ip_country_code: dict | None = None
    isp: dict | None = None
    mx_servers: list[dict] = field(default_factory=list)
    spf_info: list[str] = field(default_factory=list)
    name_servers: list[dict] = field(default_factory=list)
    ssl_certificates: list[dict] = field(default_factory=list)
    redirects_to: dict | None = None
    redirect_domain: dict | None = None


@dataclass(frozen=True, slots=True)
class IrisInvestigateModel(DTBaseModel):
    name: str
    last_enriched: str
    analytics: Analytics
    identity: Identity
    registration: Registration
    hosting: Hosting
    website_title: dict | None = None
    first_seen: dict | None = None
    server_type: dict | None = None

    @staticmethod
    def _v(d: dict | None) -> str | None:
        return d.get("value") if isinstance(d, dict) else d

    def to_table_data(self) -> dict[str, Any]:
        """Returns a simplified summary dict for UI tables (csv)."""
        return {
            "Name": self.name,
            "Last Enriched": datetime.now().strftime("%Y-%m-%d"),
            "Overall Risk Score": self.analytics.overall_risk_score,
            "Proximity Risk Score": self.analytics.proximity_risk_score,
            "Threat Profile Risk Score": self.analytics.threat_profile_risk_score.risk_score,
            "Threat Profile Threats": ", ".join(self.analytics.threat_profile_risk_score.threats),
            "Threat Profile Evidence": ", ".join(self.analytics.threat_profile_risk_score.evidence),
            # tracking codes
            "Google Adsense Tracking Code": self._format_list_value(
                "ad", self.analytics.google_adsense
            ),
            "Google Analytic Tracking Code": self._format_list_value(
                "ga", self.analytics.google_analytics
            ),
            "Website Response Code": self.analytics.website_response_code,
            "Tags": ", ".join(
                t if isinstance(t, str) else t.get("value", str(t))
                for t in self.analytics.tags
            ) if self.analytics.tags else "N/A",
            # Identity
            "Registrant Name": self._v(self.identity.registrant_name),
            "Registrant Org": self._v(self.identity.registrant_org),
            "Registrar": self._v(self.identity.registrar),
            "SOA Email": self._format_list_value(
                "ema", [{"value": e} for e in self.identity.soa_email]
            ),
            "SSL Certificate Email": self._format_list_value(
                "ssl.em", [{"value": e} for e in self.identity.ssl_email]
            ),
            # Registration
            "Create Date": self._v(self.registration.create_date),
            "Expiration Date": self._v(self.registration.expiration_date),
            "Domain Status": self.registration.domain_status,
            # hosting
            "IP Addresses": self._format_ips(self.hosting.ip_addresses),
            "IP Country Code": self._v(self.hosting.ip_country_code),
            "Website Title": self._v(self.website_title),
            "Server Type": self._v(self.server_type),
            "Popularity": self.analytics.popularity_rank,
        }

    def _format_guided_pivot_link(
        self, link_type: str | None, item: dict, domain: str | None = None
    ) -> str | int:
        query = item.get("value", "")
        count = item.get("count", 0)

        if isinstance(count, str) and "[" in count and "](" in count:
            return count

        if domain:
            link_type = "domain"
            query = domain

        try:
            numeric_count = int(count)
        except (ValueError, TypeError):
            return count

        if 1 < numeric_count < self.GUIDED_PIVOT_THRESHOLD:
            encoded_query = urllib.parse.quote(str(query), safe="")
            return f'[{count}]({self.IRIS_LINK}?q={link_type}:"{encoded_query}")'

        return count

    def _format_list_value(
        self, link_type: str, items: list[dict], domain: str | None = None
    ) -> str:
        """
        Returns a comma-separated string of pivot links
        e.g. admin@domaintools.com [5](iris url)
        """
        if not items:
            return "N/A"

        formatted_items = []
        for item in items:
            val = item.get("value")
            pivot_link = self._format_guided_pivot_link(link_type, item, domain=domain)

            if val:
                formatted_items.append(f"{val} {pivot_link}")
            else:
                formatted_items.append(f"{pivot_link}")

        return ", ".join(formatted_items)

    def _format_ips(self, ips: list[dict], domain: str | None = None) -> str:
        """
        Returns a human-readable string of IPs and their pivots.

        e.g. 8.8.8.8 [23](iris url)
        """
        ip_strings = []
        for ip in ips:
            addr_dict = ip.get("address", {})
            addr_val = addr_dict.get("value", "N/A")
            pivot = self._format_guided_pivot_link("ip.ip", addr_dict, domain=domain)
            ip_strings.append(f"{addr_val} {pivot}")

        return " | ".join(ip_strings) if ip_strings else "N/A"


@dataclass
class RDAPContact:
    name: str = ""
    org: str = ""
    email: str = ""
    phone: str = ""
    street: str = ""
    city: str = ""
    postal: str = ""
    region: str = ""
    country: str = ""
    handle: str = ""
    roles: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RDAPRegistrar:
    name: str = ""
    iana_id: str = ""
    contacts: list[RDAPContact] = field(default_factory=list)


@dataclass
class RDAPDNSSEC:
    signed: bool = False


@dataclass(frozen=True, slots=True)
class ParsedDomainRDAPModel(DTBaseModel):
    domain: str = ""
    handle: str = ""
    domain_statuses: list[str] = field(default_factory=list)
    creation_date: str = ""
    last_changed_date: str = ""
    expiration_date: str = ""
    registrar: RDAPRegistrar = field(default_factory=RDAPRegistrar)
    contacts: list[RDAPContact] = field(default_factory=list)
    dnssec: RDAPDNSSEC = field(default_factory=RDAPDNSSEC)
    nameservers: list[str] = field(default_factory=list)
    conformance: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    email_domains: list[str] = field(default_factory=list)
    has_found: bool = True

    def to_table_data(self) -> dict:
        """Returns a simplified summary dict for UI tables (csv)."""

        contact_list = []
        for c in self.contacts:
            roles_str = "/".join(c.roles) if c.roles else "no-role"
            # Confirm formatting as: "Name (admin/tech) <email@domain.com>"
            contact_info = (
                f"{c.name} ({roles_str}) <{c.email}>" if c.email else f"{c.name} ({roles_str})"
            )
            contact_list.append(contact_info)

        all_contacts = " | ".join(contact_list) if contact_list else "N/A"

        return {
            "Domain": self.domain,
            "Registrar": self.registrar.name if self.registrar.name else "N/A",
            "Created": self.creation_date[:10] if self.creation_date else "N/A",
            "Expires": self.expiration_date[:10] if self.expiration_date else "N/A",
            "Status": ", ".join(self.domain_statuses) if self.domain_statuses else "N/A",
            "All Contacts": all_contacts,
            "Nameservers": ", ".join(self.nameservers) if self.nameservers else "N/A",
            "DNSSEC": "Signed" if self.dnssec.signed else "Unsigned",
            "Emails": ", ".join(self.emails) if self.emails else "N/A",
            "EmailDomains": ", ".join(self.email_domains) if self.email_domains else "N/A",
            "Conformance": ", ".join(self.conformance) if self.conformance else "N/A",
        }


@dataclass(frozen=True, slots=True)
class WhoisRegistration:
    created: str = ""
    expires: str = ""
    updated: str = ""
    registrar: str = ""
    statuses: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class WhoisDetails:
    registrant: str = ""
    registration: WhoisRegistration = field(default_factory=WhoisRegistration)
    name_servers: list[str] = field(default_factory=list)
    server: str = ""
    record: str = ""


@dataclass(frozen=True, slots=True)
class WhoisHistoryEntry:
    date: str = ""
    is_private: int = 0
    whois: WhoisDetails = field(default_factory=WhoisDetails)


@dataclass
class EnrichedDomainSummary(DTBaseModel):
    """Lightweight enrichment result from iris_enrich, used for bulk risk scoring."""

    domain: str = ""
    risk_category: str = ""
    overall_risk_score: int = 0
    proximity_risk_score: int = 0
    threat_profile_risk_score: int = 0
    malware_risk_score: int = 0
    phishing_risk_score: int = 0
    spam_risk_score: int = 0
    threat_profile_threats: list[str] = field(default_factory=list)
    threat_profile_evidence: list[str] = field(default_factory=list)
    create_date: str | None = None
    domain_age_days: int | None = None
    is_young_domain: bool = False
    is_suspicious: bool = False
    registrant_org: str | None = None
    registrant_name: str | None = None
    registrar: str | None = None
    registrar_status: list[str] = field(default_factory=list)
    ip_country_code: str = ""
    iris_investigate_link: str = ""
    website_title: str | None = None
    server_type: str | None = None
    first_seen: str | None = None
    expiration_date: str | None = None
    active: bool = False
    whois_url: str | None = None
    popularity_rank: int | None = None
    alexa: str | None = None
    redirect: str | None = None
    redirect_domain: str | None = None
    spf_info: str | None = None
    ssl_info: list[dict] = field(default_factory=list)
    tld: str | None = None
    adsense: str | None = None
    google_analytics: str | None = None
    ga4: list[dict] = field(default_factory=list)
    gtm_codes: list[dict] = field(default_factory=list)
    fb_codes: list[dict] = field(default_factory=list)
    hotjar_codes: list[dict] = field(default_factory=list)
    baidu_codes: list[dict] = field(default_factory=list)
    yandex_codes: list[dict] = field(default_factory=list)
    matomo_codes: list[dict] = field(default_factory=list)
    statcounter_project_codes: list[dict] = field(default_factory=list)
    statcounter_security_codes: list[dict] = field(default_factory=list)
    registrant_contact: Contact | None = None
    admin_contact: Contact | None = None
    technical_contact: Contact | None = None
    billing_contact: Contact | None = None
    tags: list[dict] = field(default_factory=list)

    def to_table_data(self) -> dict[str, Any]:
        return {
            "Domain": self.domain,
            "TLD": self.tld or "N/A",
            "Active": self.active,
            "Risk Category": self.risk_category,
            "Is Suspicious": self.is_suspicious,
            "Overall Risk Score": self.overall_risk_score,
            "Proximity Risk Score": self.proximity_risk_score,
            "Threat Profile Score": self.threat_profile_risk_score,
            "Threats": ", ".join(self.threat_profile_threats) if self.threat_profile_threats else "N/A",
            "Evidence": ", ".join(self.threat_profile_evidence) if self.threat_profile_evidence else "N/A",
            "Create Date": self.create_date or "N/A",
            "Expiration Date": self.expiration_date or "N/A",
            "Domain Age (days)": self.domain_age_days if self.domain_age_days is not None else "N/A",
            "Young Domain": self.is_young_domain,
            "Registrant Name": self.registrant_name or "N/A",
            "Registrant Org": self.registrant_org or "N/A",
            "Registrar": self.registrar or "N/A",
            "Registrar Status": ", ".join(self.registrar_status) if self.registrar_status else "N/A",
            "IP Country": self.ip_country_code or "N/A",
            "Website Title": self.website_title or "N/A",
            "Server Type": self.server_type or "N/A",
            "First Seen": self.first_seen or "N/A",
            "Redirect": self.redirect or "N/A",
            "Redirect Domain": self.redirect_domain or "N/A",
            "Popularity Rank": self.popularity_rank if self.popularity_rank is not None else "N/A",
            "SPF Info": self.spf_info or "N/A",
            "WHOIS URL": self.whois_url or "N/A",
            "Tags": ", ".join(t.get("label", "") for t in self.tags if t.get("label")) or "N/A",
            "Iris Link": self.iris_investigate_link,
        }


@dataclass(frozen=True, slots=True)
class WhoisHistoryModel(DTBaseModel):
    record_count: int = 0
    history: list[WhoisHistoryEntry] = field(default_factory=list)
    has_found: bool = True

    def to_table_data(self) -> list[dict]:
        """
        Returns a list of rows for the summary data table.
        whois history is displayed as a multi-row table.
        """
        table_rows = []
        for entry in self.history:
            reg = entry.whois.registration
            table_rows.append({
                "History Date": entry.date,
                "Registrar": reg.registrar,
                "Created": reg.created,
                "Expires": reg.expires,
                "Registrant": entry.whois.registrant,
                "Privacy": "Private" if entry.is_private else "Public",
            })
        return table_rows
