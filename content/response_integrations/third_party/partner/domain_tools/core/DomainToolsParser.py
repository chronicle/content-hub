from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

from .datamodels import (
    RDAPDNSSEC,
    Analytics,
    Contact,
    EnrichedDomainSummary,
    Hosting,
    Identity,
    IrisInvestigateModel,
    ParsedDomainRDAPModel,
    RDAPContact,
    RDAPRegistrar,
    Registration,
    RiskProfile,
    WhoisDetails,
    WhoisHistoryEntry,
    WhoisHistoryModel,
    WhoisRegistration,
)
from .UtilsManager import classify_domain_risk, get_domain_risk_score_details, parse_domain_age_days


class DomainToolsParser:
    @staticmethod
    def _safe_get_value(data: SingleJson, key: str) -> str:
        val = data.get(key)
        return val.get("value", "") if isinstance(val, dict) else (val or "")

    @staticmethod
    def _safe_get_dict(data: SingleJson, key: str) -> SingleJson | None:
        """Returns the full {value, count} dict if value is non-empty, else None."""
        val = data.get(key)
        if not isinstance(val, dict):
            return None
        return val if val.get("value") else None

    @staticmethod
    def _to_list_dict(data: SingleJson, key: str) -> list[SingleJson]:
        """Ensures tracking codes are always a list of dicts."""
        val = data.get(key)
        if not val:
            return []
        return val if isinstance(val, list) else [{"value": val}]

    @staticmethod
    def _to_single_json(val: Any) -> SingleJson | None:
        """Normalize a raw API value (str or {value, count} dict) to SingleJson or None.

        Handles APIs that return a field as either a plain string or a pivot dict
        depending on the endpoint (e.g. iris_enrich vs iris_investigate for registrar).
        """
        if isinstance(val, dict):
            return val if val.get("value") else None
        if isinstance(val, str) and val:
            return {"value": val, "count": 0}
        return None

    def _parse_iris_contact(self, contact_data: dict) -> Contact:
        if not contact_data:
            return Contact()

        return Contact(
            country=contact_data.get("country"),
            email=contact_data.get("email"),
            name=contact_data.get("name"),
            phone=contact_data.get("phone"),
            street=contact_data.get("street"),
            city=contact_data.get("city"),
            state=contact_data.get("state"),
            postal=contact_data.get("postal"),
            org=contact_data.get("org"),
        )

    def parse_iris_data(self, raw_data: dict[str, Any]) -> IrisInvestigateModel:
        risk_raw = raw_data.get("domain_risk") or {}
        risk_details = get_domain_risk_score_details(risk_raw)

        ips = raw_data.get("ip") or []
        first_ip = ips[0] if ips else {}
        ip_cc = self._safe_get_dict(first_ip, "country_code")
        isp = self._safe_get_dict(first_ip, "isp")

        registrant_contact = self._parse_iris_contact(raw_data.get("registrant_contact", {}))
        admin_contact = self._parse_iris_contact(raw_data.get("admin_contact", {}))
        technical_contact = self._parse_iris_contact(raw_data.get("technical_contact", {}))
        billing_contact = self._parse_iris_contact(raw_data.get("billing_contact", {}))

        return IrisInvestigateModel(
            domain=str(raw_data.get("domain", "")),
            last_enriched=datetime.now().strftime("%Y-%m-%d"),
            website_title=self._safe_get_dict(raw_data, "website_title"),
            first_seen=self._safe_get_dict(raw_data, "first_seen"),
            server_type=self._safe_get_dict(raw_data, "server_type"),
            analytics=Analytics(
                overall_risk_score=risk_details.get("overall_risk_score", 0),
                proximity_risk_score=risk_details.get("proximity_risk_score", 0),
                malware_risk_score=risk_details.get("threat_profile_malware_risk_score", 0),
                phishing_risk_score=risk_details.get("threat_profile_phishing_risk_score", 0),
                spam_risk_score=risk_details.get("threat_profile_spam_risk_score", 0),
                threat_profile_risk_score=RiskProfile(
                    risk_score=risk_details.get("threat_profile_risk_score", 0),
                    threats=risk_details.get("threat_profile_threats", []),
                    evidence=risk_details.get("threat_profile_evidence", []),
                ),
                website_response_code=raw_data.get("website_response"),
                google_adsense=self._to_list_dict(raw_data, "adsense"),
                google_analytics=self._to_list_dict(raw_data, "google_analytics"),
                ga4=self._to_list_dict(raw_data, "ga4"),
                gtm_codes=self._to_list_dict(raw_data, "gtm_codes"),
                fb_codes=self._to_list_dict(raw_data, "fb_codes"),
                hotjar_codes=self._to_list_dict(raw_data, "hotjar_codes"),
                baidu_codes=self._to_list_dict(raw_data, "baidu_codes"),
                yandex_codes=self._to_list_dict(raw_data, "yandex_codes"),
                matomo_codes=self._to_list_dict(raw_data, "matomo_codes"),
                statcounter_project_codes=self._to_list_dict(raw_data, "statcounter_project_codes"),
                statcounter_security_codes=self._to_list_dict(
                    raw_data, "statcounter_security_codes"
                ),
                tags=raw_data.get("tags") or [],
            ),
            identity=Identity(
                registrant_name=self._safe_get_dict(raw_data, "registrant_name"),
                registrant_org=self._safe_get_dict(raw_data, "registrant_org"),
                registrar=self._to_single_json(raw_data.get("registrar")),
                soa_email=raw_data.get("soa_email") or [],
                ssl_email=raw_data.get("ssl_email") or [],
                email_domains=[
                    e for e in (raw_data.get("email_domain") or []) if e.get("value")
                ],
                additional_whois_emails=raw_data.get("additional_whois_email") or [],
                registrant_contact=registrant_contact,
                admin_contact=admin_contact,
                technical_contact=technical_contact,
                billing_contact=billing_contact,
            ),
            registration=Registration(
                registrar_status=raw_data.get("registrar_status") or [],
                domain_status=raw_data.get("active") or False,
                create_date=self._safe_get_dict(raw_data, "create_date"),
                expiration_date=self._safe_get_dict(raw_data, "expiration_date"),
            ),
            hosting=Hosting(
                ip_addresses=ips,
                ip_country_code=ip_cc,
                isp=isp,
                mx_servers=raw_data.get("mx") or [],
                spf_info=raw_data.get("spf_info") or [],
                name_servers=raw_data.get("name_server") or [],
                ssl_certificates=raw_data.get("ssl_info") or [],
                redirects_to=self._safe_get_dict(raw_data, "redirect"),
                redirect_domain=self._safe_get_dict(raw_data, "redirect_domain"),
            ),
        )

    def _parse_iris_enrich_contact(self, contact_data: dict) -> Contact | None:
        """Parse an iris_enrich contact where each field is wrapped in {value: ...}."""
        if not contact_data:
            return None

        def _v(key: str) -> str | None:
            raw = contact_data.get(key, {})
            v = raw.get("value", "") if isinstance(raw, dict) else (raw or "")
            return v or None
        emails = contact_data.get("email") or []
        email_str = ", ".join(e.get("value", "") for e in emails if e.get("value")) or None
        return Contact(
            name=_v("name"),
            org=_v("org"),
            email=email_str,
            phone=_v("phone"),
            street=_v("street"),
            city=_v("city"),
            state=_v("state"),
            postal=_v("postal"),
            country=_v("country"),
        )

    @staticmethod
    def _parse_risk_components(risk_details: dict[str, Any]) -> dict[str, Any]:
        """Extract and normalize risk scores, threats, and evidence from risk_details."""
        threats_raw = risk_details.get("threat_profile_threats", "")
        evidence_raw = risk_details.get("threat_profile_evidence", "")
        return {
            "overall_risk_score": risk_details.get("overall_risk_score") or 0,
            "proximity_risk_score": risk_details.get("proximity_risk_score") or 0,
            "threat_profile_risk_score": risk_details.get("threat_profile_risk_score") or 0,
            "malware_risk_score": risk_details.get("threat_profile_malware_risk_score") or 0,
            "phishing_risk_score": risk_details.get("threat_profile_phishing_risk_score") or 0,
            "spam_risk_score": risk_details.get("threat_profile_spam_risk_score") or 0,
            "threats": (
                [t.strip() for t in threats_raw.split(",") if t.strip()]
                if isinstance(threats_raw, str) else (threats_raw or [])
            ),
            "evidence": (
                [e.strip() for e in evidence_raw.split(",") if e.strip()]
                if isinstance(evidence_raw, str) else (evidence_raw or [])
            ),
        }

    @staticmethod
    def _calculate_domain_age(raw_data: SingleJson) -> tuple[str | None, int | None]:
        """Return (create_date_str, domain_age_days) from raw API data."""
        create_date_raw = raw_data.get("create_date") or {}
        domain_age_days = parse_domain_age_days(create_date_raw)
        create_date = create_date_raw.get("value") or None if isinstance(create_date_raw, dict) else create_date_raw or None
        return create_date, domain_age_days

    def _extract_identity_fields(self, raw_data: SingleJson) -> dict[str, Any]:
        """Extract registrant, registrar, and contact fields."""
        registrant_org_raw = raw_data.get("registrant_org") or {}
        registrant_org = (
            registrant_org_raw.get("value") if isinstance(registrant_org_raw, dict) else registrant_org_raw or None
        )
        return {
            "registrant_name": self._safe_get_value(raw_data, "registrant_name") or None,
            "registrant_org": registrant_org,
            "registrar": self._safe_get_value(raw_data, "registrar") or None,
            "registrar_status": raw_data.get("registrar_status") or [],
            "registrant_contact": self._parse_iris_enrich_contact(raw_data.get("registrant_contact") or {}),
            "admin_contact": self._parse_iris_enrich_contact(raw_data.get("admin_contact") or {}),
            "technical_contact": self._parse_iris_enrich_contact(raw_data.get("technical_contact") or {}),
            "billing_contact": self._parse_iris_enrich_contact(raw_data.get("billing_contact") or {}),
        }

    def _extract_infrastructure_fields(self, raw_data: SingleJson) -> dict[str, Any]:
        """Extract hosting metadata, tracking codes, and infrastructure fields."""
        ips = raw_data.get("ip") or []
        ip_cc = ips[0].get("country_code", {}).get("value", "") if ips else ""
        pr_raw = raw_data.get("popularity_rank")
        return {
            "ip_country_code": ip_cc,
            "website_title": self._safe_get_value(raw_data, "website_title") or None,
            "server_type": self._safe_get_value(raw_data, "server_type") or None,
            "first_seen": self._safe_get_value(raw_data, "first_seen") or None,
            "redirect": self._safe_get_value(raw_data, "redirect") or None,
            "redirect_domain": self._safe_get_value(raw_data, "redirect_domain") or None,
            "expiration_date": self._safe_get_value(raw_data, "expiration_date") or None,
            "spf_info": raw_data.get("spf_info") or None,
            "ssl_info": raw_data.get("ssl_info") or [],
            "tld": raw_data.get("tld") or None,
            "active": bool(raw_data.get("active")),
            "whois_url": raw_data.get("whois_url") or None,
            "popularity_rank": int(pr_raw) if pr_raw and str(pr_raw).isdigit() else None,
            "alexa": str(raw_data.get("alexa")) if raw_data.get("alexa") else None,
            "adsense": self._safe_get_value(raw_data, "adsense") or None,
            "google_analytics": self._safe_get_value(raw_data, "google_analytics") or None,
            "ga4": raw_data.get("ga4") or [],
            "gtm_codes": raw_data.get("gtm_codes") or [],
            "fb_codes": raw_data.get("fb_codes") or [],
            "hotjar_codes": raw_data.get("hotjar_codes") or [],
            "baidu_codes": raw_data.get("baidu_codes") or [],
            "yandex_codes": raw_data.get("yandex_codes") or [],
            "matomo_codes": raw_data.get("matomo_codes") or [],
            "statcounter_project_codes": raw_data.get("statcounter_project_codes") or [],
            "statcounter_security_codes": raw_data.get("statcounter_security_codes") or [],
            "tags": raw_data.get("tags") or [],
        }

    def parse_iris_enrich_data(self, domain: str, raw_data: SingleJson) -> EnrichedDomainSummary:
        """Parse a single iris_enrich result into an EnrichedDomainSummary."""
        risk_details = get_domain_risk_score_details(raw_data.get("domain_risk") or {})
        risk = self._parse_risk_components(risk_details)
        create_date, domain_age_days = self._calculate_domain_age(raw_data)
        risk_category = classify_domain_risk(risk["overall_risk_score"], domain_age_days)
        identity = self._extract_identity_fields(raw_data)
        infra = self._extract_infrastructure_fields(raw_data)
        iris_link = f'https://iris.domaintools.com/investigate/search/?q=domain:"{domain}"'

        return EnrichedDomainSummary(
            domain=domain,
            risk_category=risk_category,
            overall_risk_score=risk["overall_risk_score"],
            proximity_risk_score=risk["proximity_risk_score"],
            threat_profile_risk_score=risk["threat_profile_risk_score"],
            malware_risk_score=risk["malware_risk_score"],
            phishing_risk_score=risk["phishing_risk_score"],
            spam_risk_score=risk["spam_risk_score"],
            threat_profile_threats=risk["threats"],
            threat_profile_evidence=risk["evidence"],
            create_date=create_date,
            domain_age_days=domain_age_days,
            is_young_domain=(risk_category == "young_domain"),
            iris_investigate_link=iris_link,
            registrant_name=identity["registrant_name"],
            registrant_org=identity["registrant_org"],
            registrar=identity["registrar"],
            registrar_status=identity["registrar_status"],
            registrant_contact=identity["registrant_contact"],
            admin_contact=identity["admin_contact"],
            technical_contact=identity["technical_contact"],
            billing_contact=identity["billing_contact"],
            ip_country_code=infra["ip_country_code"],
            website_title=infra["website_title"],
            server_type=infra["server_type"],
            first_seen=infra["first_seen"],
            redirect=infra["redirect"],
            redirect_domain=infra["redirect_domain"],
            expiration_date=infra["expiration_date"],
            spf_info=infra["spf_info"],
            ssl_info=infra["ssl_info"],
            tld=infra["tld"],
            active=infra["active"],
            whois_url=infra["whois_url"],
            popularity_rank=infra["popularity_rank"],
            alexa=infra["alexa"],
            adsense=infra["adsense"],
            google_analytics=infra["google_analytics"],
            ga4=infra["ga4"],
            gtm_codes=infra["gtm_codes"],
            fb_codes=infra["fb_codes"],
            hotjar_codes=infra["hotjar_codes"],
            baidu_codes=infra["baidu_codes"],
            yandex_codes=infra["yandex_codes"],
            matomo_codes=infra["matomo_codes"],
            statcounter_project_codes=infra["statcounter_project_codes"],
            statcounter_security_codes=infra["statcounter_security_codes"],
            tags=infra["tags"],
        )

    def parse_domain_rdap_data(self, raw_data: dict[str, Any]) -> ParsedDomainRDAPModel:
        reg_raw = raw_data.get("registrar", {})
        reg_contacts = [RDAPContact(**c) for c in reg_raw.get("contacts", [])]

        registrar = RDAPRegistrar(
            name=reg_raw.get("name", ""), iana_id=reg_raw.get("iana_id", ""), contacts=reg_contacts
        )

        return ParsedDomainRDAPModel(
            domain=raw_data.get("domain", ""),
            handle=raw_data.get("handle", ""),
            domain_statuses=raw_data.get("domain_statuses", []),
            creation_date=raw_data.get("creation_date", ""),
            last_changed_date=raw_data.get("last_changed_date", ""),
            expiration_date=raw_data.get("expiration_date", ""),
            registrar=registrar,
            contacts=[RDAPContact(**c) for c in raw_data.get("contacts", [])],
            dnssec=RDAPDNSSEC(**raw_data.get("dnssec", {})),
            nameservers=raw_data.get("nameservers", []),
            emails=raw_data.get("emails", []),
            email_domains=raw_data.get("email_domains", []),
        )

    def parse_whois_history(self, raw_data: dict) -> WhoisHistoryModel:
        history_entries = []
        for item in raw_data.get("history", []):
            whois_raw = item.get("whois", {})
            reg_raw = whois_raw.get("registration", {})

            whois_registration = WhoisRegistration(
                created=reg_raw.get("created", ""),
                expires=reg_raw.get("expires", ""),
                updated=reg_raw.get("updated", ""),
                registrar=reg_raw.get("registrar", ""),
                statuses=reg_raw.get("statuses", []),
            )

            whois_details = WhoisDetails(
                registrant=whois_raw.get("registrant", ""),
                registration=whois_registration,
                name_servers=whois_raw.get("name_servers", []),
                server=whois_raw.get("server", ""),
                record=whois_raw.get("record", ""),
            )

            history_entries.append(
                WhoisHistoryEntry(
                    date=item.get("date", ""),
                    is_private=item.get("is_private", 0),
                    whois=whois_details,
                )
            )

        return WhoisHistoryModel(
            record_count=raw_data.get("record_count", 0), history=history_entries
        )
