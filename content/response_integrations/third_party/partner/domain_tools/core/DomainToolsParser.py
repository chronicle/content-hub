from __future__ import annotations

from .datamodels import *
from .UtilsManager import get_domain_risk_score_details
from datetime import datetime


class DomainToolsParser:
    def _safe_get_value(self, data: dict, key: str) -> str:
        val = data.get(key)
        return val.get("value", "") if isinstance(val, dict) else (val or "")

    def _to_list_dict(self, data: dict, key: str) -> list[dict]:
        """ Ensures tracking codes are always a list of dicts. """
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
            org=contact_data.get("org")
        )

    def parse_iris_data(self, raw_data: dict[str, Any]) -> IrisInvestigateModel:
        risk_raw = raw_data.get("domain_risk") or {}
        risk_details = get_domain_risk_score_details(risk_raw)

        ips = raw_data.get("ip") or []
        ip_cc = ips[0].get("country_code", {}).get("value", "") if ips else ""

        registrant_contact = self._parse_iris_contact(raw_data.get("registrant_contact", {}))
        admin_contact = self._parse_iris_contact(raw_data.get("admin_contact", {}))
        technical_contact = self._parse_iris_contact(raw_data.get("technical_contact", {}))
        billing_contact = self._parse_iris_contact(raw_data.get("billing_contact", {}))

        return IrisInvestigateModel(
            name=str(raw_data.get("domain", "")),
            last_enriched=datetime.now().strftime("%Y-%m-%d"),
            website_title=self._safe_get_value(raw_data, "website_title"),
            first_seen=self._safe_get_value(raw_data, "first_seen"),
            server_type=self._safe_get_value(raw_data, "server_type"),
            analytics=Analytics(
                overall_risk_score=risk_details.get("overall_risk_score", 0),
                proximity_risk_score=risk_details.get("proximity_risk_score", 0),
                malware_risk_score=risk_details.get("threat_profile_malware_risk_score", 0),
                phishing_risk_score=risk_details.get("threat_profile_phishing_risk_score", 0),
                spam_risk_score=risk_details.get("threat_profile_spam_risk_score", 0),
                threat_profile_risk_score=RiskProfile(
                    risk_score=risk_details.get("threat_profile_risk_score", 0),
                    threats=risk_details.get("threat_profile_threats", []),
                    evidence=risk_details.get("threat_profile_evidence", [])
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
                statcounter_security_codes=self._to_list_dict(raw_data, "statcounter_security_codes"),
                tags=raw_data.get("tags") or []
            ),
            identity=Identity(
                registrant_name=self._safe_get_value(raw_data, "registrant_name"),
                registrant_org=self._safe_get_value(raw_data, "registrant_org"),
                registrar=raw_data.get("registrar"),
                soa_email=raw_data.get("soa_email") or [],
                ssl_email=raw_data.get("ssl_email") or [],
                email_domains=[e.get("value") for e in (raw_data.get("email_domain") or []) if e.get("value")],
                additional_whois_emails=raw_data.get("additional_whois_email") or [],
                registrant_contact=registrant_contact,
                admin_contact=admin_contact,
                technical_contact=technical_contact,
                billing_contact=billing_contact
            ),
            registration=Registration(
                registrar_status=raw_data.get("registrar_status") or [],
                domain_status=raw_data.get("active") or False,
                create_date=self._safe_get_value(raw_data, "create_date"),
                expiration_date=self._safe_get_value(raw_data, "expiration_date")
            ),
            hosting=Hosting(
                ip_addresses=ips,
                ip_country_code=ip_cc,
                mx_servers=raw_data.get("mx") or [],
                spf_info=raw_data.get("spf_info") or [],
                name_servers=raw_data.get("name_server") or [],
                ssl_certificates=raw_data.get("ssl_info") or [],
                redirects_to=raw_data.get("redirect") or [],
                redirect_domain=raw_data.get("redirect_domain") or []
            )
        )


    def parse_domain_rdap_data(self, raw_data: dict[str, Any]) -> ParsedDomainRDAPModel:
        reg_raw = raw_data.get("registrar", {})
        reg_contacts = [
            RDAPContact(**c) for c in reg_raw.get("contacts", [])
        ]

        registrar = RDAPRegistrar(
            name=reg_raw.get("name", ""),
            iana_id=reg_raw.get("iana_id", ""),
            contacts=reg_contacts
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
            email_domains=raw_data.get("email_domains", [])
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
                statuses=reg_raw.get("statuses", [])
            )

            whois_details = WhoisDetails(
                registrant=whois_raw.get("registrant", ""),
                registration=whois_registration,
                name_servers=whois_raw.get("name_servers", []),
                server=whois_raw.get("server", ""),
                record=whois_raw.get("record", "")
            )

            history_entries.append(
                WhoisHistoryEntry(
                    date=item.get("date", ""),
                    is_private=item.get("is_private", 0),
                    whois=whois_details
                )
            )

        return WhoisHistoryModel(
            record_count=raw_data.get("record_count", 0),
            history=history_entries
        )