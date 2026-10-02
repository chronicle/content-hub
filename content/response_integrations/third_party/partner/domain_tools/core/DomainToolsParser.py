from __future__ import annotations

from datetime import datetime
from typing import Any

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
from .UtilsManager import classify_domain_risk, get_domain_risk_score_details


class DomainToolsParser:
    def _safe_get_value(self, data: dict, key: str) -> str:
        val = data.get(key)
        return val.get("value", "") if isinstance(val, dict) else (val or "")

    def _safe_get_dict(self, data: dict, key: str) -> dict | None:
        """Returns the full {value, count} dict if value is non-empty, else None."""
        val = data.get(key)
        if not isinstance(val, dict):
            return None
        return val if val.get("value") else None

    def _to_list_dict(self, data: dict, key: str) -> list[dict]:
        """Ensures tracking codes are always a list of dicts."""
        val = data.get(key)
        if not val:
            return []
        return val if isinstance(val, list) else [{"value": val}]

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
            name=str(raw_data.get("domain", "")),
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
                registrar=self._safe_get_dict(raw_data, "registrar"),
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

    def parse_iris_enrich_data(self, domain: str, raw_data: dict[str, Any]) -> EnrichedDomainSummary:
        """Parse a single iris_enrich result into an EnrichedDomainSummary."""
        risk_raw = raw_data.get("domain_risk") or {}
        risk_details = get_domain_risk_score_details(risk_raw)

        overall_score = risk_details.get("overall_risk_score") or 0
        create_date_raw = raw_data.get("create_date") or {}
        create_date = create_date_raw.get("value") if isinstance(create_date_raw, dict) else create_date_raw or None

        domain_age_days: int | None = None
        if create_date:
            try:
                created = datetime.strptime(create_date[:10], "%Y-%m-%d")
                domain_age_days = (datetime.now() - created).days
            except ValueError:
                pass

        risk_category = classify_domain_risk(overall_score, domain_age_days)

        ips = raw_data.get("ip") or []
        ip_cc = ips[0].get("country_code", {}).get("value", "") if ips else ""

        registrant_org_raw = raw_data.get("registrant_org") or {}
        registrant_org = (
            registrant_org_raw.get("value") if isinstance(registrant_org_raw, dict) else registrant_org_raw or None
        )

        iris_link = f'https://iris.domaintools.com/investigate/search/?q=domain:"{domain}"'

        website_title = self._safe_get_value(raw_data, "website_title") or None
        server_type = self._safe_get_value(raw_data, "server_type") or None
        first_seen = self._safe_get_value(raw_data, "first_seen") or None
        redirect = self._safe_get_value(raw_data, "redirect") or None
        redirect_domain = self._safe_get_value(raw_data, "redirect_domain") or None
        registrant_name = self._safe_get_value(raw_data, "registrant_name") or None
        registrar = self._safe_get_value(raw_data, "registrar") or None
        registrar_status = raw_data.get("registrar_status") or []
        spf_info = raw_data.get("spf_info") or None
        ssl_info = raw_data.get("ssl_info") or []
        tld = raw_data.get("tld") or None
        expiration_date = self._safe_get_value(raw_data, "expiration_date") or None
        active = bool(raw_data.get("active"))
        whois_url = raw_data.get("whois_url") or None
        pr_raw = raw_data.get("popularity_rank")
        popularity_rank = int(pr_raw) if pr_raw and str(pr_raw).isdigit() else None
        alexa = str(raw_data.get("alexa")) if raw_data.get("alexa") else None
        adsense = self._safe_get_value(raw_data, "adsense") or None
        google_analytics = self._safe_get_value(raw_data, "google_analytics") or None
        ga4 = raw_data.get("ga4") or []
        gtm_codes = raw_data.get("gtm_codes") or []
        fb_codes = raw_data.get("fb_codes") or []
        hotjar_codes = raw_data.get("hotjar_codes") or []
        baidu_codes = raw_data.get("baidu_codes") or []
        yandex_codes = raw_data.get("yandex_codes") or []
        matomo_codes = raw_data.get("matomo_codes") or []
        statcounter_project_codes = raw_data.get("statcounter_project_codes") or []
        statcounter_security_codes = raw_data.get("statcounter_security_codes") or []
        registrant_contact = self._parse_iris_enrich_contact(raw_data.get("registrant_contact") or {})
        admin_contact = self._parse_iris_enrich_contact(raw_data.get("admin_contact") or {})
        technical_contact = self._parse_iris_enrich_contact(raw_data.get("technical_contact") or {})
        billing_contact = self._parse_iris_enrich_contact(raw_data.get("billing_contact") or {})
        tags = raw_data.get("tags") or []

        threats_raw = risk_details.get("threat_profile_threats", "")
        evidence_raw = risk_details.get("threat_profile_evidence", "")
        threats = (
            [t.strip() for t in threats_raw.split(",") if t.strip()]
            if isinstance(threats_raw, str)
            else (threats_raw or [])
        )
        evidence = (
            [e.strip() for e in evidence_raw.split(",") if e.strip()]
            if isinstance(evidence_raw, str)
            else (evidence_raw or [])
        )

        return EnrichedDomainSummary(
            domain=domain,
            risk_category=risk_category,
            overall_risk_score=overall_score,
            proximity_risk_score=risk_details.get("proximity_risk_score") or 0,
            threat_profile_risk_score=risk_details.get("threat_profile_risk_score") or 0,
            malware_risk_score=risk_details.get("threat_profile_malware_risk_score") or 0,
            phishing_risk_score=risk_details.get("threat_profile_phishing_risk_score") or 0,
            spam_risk_score=risk_details.get("threat_profile_spam_risk_score") or 0,
            threat_profile_threats=threats,
            threat_profile_evidence=evidence,
            create_date=create_date,
            domain_age_days=domain_age_days,
            is_young_domain=(risk_category == "young_domain"),
            registrant_org=registrant_org,
            registrant_name=registrant_name,
            registrar=registrar,
            registrar_status=registrar_status,
            ip_country_code=ip_cc,
            iris_investigate_link=iris_link,
            website_title=website_title,
            server_type=server_type,
            first_seen=first_seen,
            redirect=redirect,
            redirect_domain=redirect_domain,
            expiration_date=expiration_date,
            active=active,
            whois_url=whois_url,
            popularity_rank=popularity_rank,
            alexa=alexa,
            spf_info=spf_info,
            ssl_info=ssl_info,
            tld=tld,
            adsense=adsense,
            google_analytics=google_analytics,
            ga4=ga4,
            gtm_codes=gtm_codes,
            fb_codes=fb_codes,
            hotjar_codes=hotjar_codes,
            baidu_codes=baidu_codes,
            yandex_codes=yandex_codes,
            matomo_codes=matomo_codes,
            statcounter_project_codes=statcounter_project_codes,
            statcounter_security_codes=statcounter_security_codes,
            registrant_contact=registrant_contact,
            admin_contact=admin_contact,
            technical_contact=technical_contact,
            billing_contact=billing_contact,
            tags=tags,
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
