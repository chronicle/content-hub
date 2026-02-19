from __future__ import annotations

import json
import urllib.parse
from datetime import datetime
from dataclasses import dataclass, field, asdict
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
    registrant_name: str | None = None
    registrant_org: str | None = None
    registrar: str | None = None
    soa_email: list[str] = field(default_factory=list)
    ssl_email: list[str] = field(default_factory=list)
    email_domains: list[str] = field(default_factory=list)
    additional_whois_emails: list[str] = field(default_factory=list)
    registrant_contact: Contact | None = None
    admin_contact: Contact | None = None
    technical_contact: Contact | None = None
    billing_contact: Contact | None = None


@dataclass(slots=True)
class Registration:
    registrar_status: list[str] = field(default_factory=list)
    domain_status: bool = False
    create_date: str | None = None
    expiration_date: str | None = None


@dataclass(slots=True)
class Hosting:
    ip_addresses: list[dict] = field(default_factory=list)
    ip_country_code: str = ""
    mx_servers: list[dict] = field(default_factory=list)
    spf_info: list[str] = field(default_factory=list)
    name_servers: list[dict] = field(default_factory=list)
    ssl_certificates: list[dict] = field(default_factory=list)
    redirects_to: list[str] = field(default_factory=list)
    redirect_domain: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class IrisInvestigateModel(DTBaseModel):
    name: str
    last_enriched: str
    analytics: Analytics
    identity: Identity
    registration: Registration
    hosting: Hosting
    website_title: str = ""
    first_seen: str = ""
    server_type: str = ""


    def to_table_data(self) -> dict[str, Any]:
        """ Returns a simplified summary dict for UI tables (csv). """
        return {
            "Name": self.name,
            "Last Enriched": datetime.now().strftime("%Y-%m-%d"),
            "Overall Risk Score": self.analytics.overall_risk_score,
            "Proximity Risk Score": self.analytics.proximity_risk_score,
            "Threat Profile Risk Score": self.analytics.threat_profile_risk_score.risk_score,
            "Threat Profile Threats": ", ".join(self.analytics.threat_profile_risk_score.threats),
            "Threat Profile Evidence": ", ".join(self.analytics.threat_profile_risk_score.evidence),
            # tracking codes
            "Google Adsense Tracking Code": self._format_list_value("ad", self.analytics.google_adsense),
            "Google Analytic Tracking Code": self._format_list_value("ga", self.analytics.google_analytics),
            "Website Response Code": self.analytics.website_response_code,
            "Tags": ", ".join(self.analytics.tags) if self.analytics.tags else "N/A",
            # Identity
            "Registrant Name": self.identity.registrant_name,
            "Registrant Org": self.identity.registrant_org,
            "Registrar": self.identity.registrar,
            "SOA Email": self._format_list_value("ema", [{"value": e} for e in self.identity.soa_email]),
            "SSL Certificate Email": self._format_list_value("ssl.em", [{"value": e} for e in self.identity.ssl_email]),
            # Registration
            "Create Date": self.registration.create_date,
            "Expiration Date": self.registration.expiration_date,
            "Domain Status": self.registration.domain_status,
            # hosting
            "IP Addresses": self._format_ips(self.hosting.ip_addresses),
            "IP Country Code": self.hosting.ip_country_code,
            "Website Title": self.website_title,
            "Server Type": self.server_type,
            "Popularity": self.analytics.popularity_rank
        }

    def _format_guided_pivot_link(self, link_type: str | None, item: dict, domain: str | None = None) -> str | int:
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

    def _format_list_value(self, link_type: str, items: list[dict], domain: str | None = None) -> str:
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
            contact_info = f"{c.name} ({roles_str}) <{c.email}>" if c.email else f"{c.name} ({roles_str})"
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
            "Conformance": ", ".join(self.conformance) if self.conformance else "N/A"
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
                "Privacy": "Private" if entry.is_private else "Public"
            })
        return table_rows