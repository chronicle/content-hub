from __future__ import annotations

import copy
import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any


class SpyCloudUdmConverter:
    """
    Convert SpyCloud records into Google SecOps UDM-like event dictionaries.

    Design goals:
    - Work with the existing connector output without changing collection logic.
    - Keep event shaping deterministic and easy to test.
    - Avoid sending highly sensitive cleartext data such as passwords or cookie payloads.
    - Support optional breach catalog enrichment and optional Compass merge behavior.
    - Map SpyCloud severity into SecOps-friendly severity / criticality / risk fields.
    """

    VENDOR_NAME = "SpyCloud"
    PRODUCT_NAME = "SpyCloud Enterprise"
    LOG_TYPE = "SPYCLOUD"
    SOURCE_FIELD = "spycloud_collection_source"

    DEFAULT_EXPOSURE_EVENT_TYPE = "USER_RESOURCE_ACCESS"
    DEFAULT_MALWARE_EVENT_TYPE = "MALWARE_DETECTION"

    # Source severity -> SOAR numeric severity
    # low=40, medium=60, high=80, critical=100
    SOAR_SEVERITY_MAP = {
        "low": 40,
        "medium": 60,
        "high": 80,
        "critical": 100,
    }

    SENSITIVE_DROP_FIELDS = {
        "password",
        "password_plaintext",
        "password_value",
        "password_raw",
        "new_password",
        "old_password",
        "form_post_data",
        "form_cookies_data",
        "cookie_data",
        "cookies",
        "cc_number",
        "cc_code",
        "bank_number",
        "bank_routing_number",
        "taxid",
        "account_password",
        "credentials",
        "private_key_password",
        "account_secret",
        "account_secret_question",
        "api_token",
        "api_token_secret",
    }

    EXTENSION_ALLOWLIST = {
        "document_id",
        "source_id",
        "severity",
        "password_type",
        "email",
        "username",
        "email_domain",
        "domain",
        "subdomain",
        "target_domain",
        "target_subdomain",
        "target_url",
        "country_code",
        "timezone",
        "infected_machine_id",
        "log_id",
        "infected_path",
        "infected_time",
        "user_hostname",
        "user_os",
        "user_browser",
        "user_agent",
        "user_sys_domain",
        "system_model",
        "mac_address",
        "port",
        "av_softwares",
        "source_type",
        "record_type",
        "record_modification_date",
        "record_cracked_date",
        "record_addition_date",
        "spycloud_publish_date",
        "breach_date",
        "published_date",
        "malware_family",
        "breach_main_category",
        "breach_category",
        "title",
        "short_title",
        "site",
        "description",
        "confidence",
        "tlp",
        "service",
        "account_type",
        "account_status",
        "_merged_record_count",
        "spycloud_collection_source",
        "has_password",
        "has_plaintext_password",
        "spycloud_severity_label",
        "soar_severity",
        "risk_score",
        "criticality"
    }

    def __init__(
        self,
        event_type_exposure: str | None = None,
        event_type_malware: str | None = None,
        vendor_name: str | None = None,
        product_name: str | None = None,
        log_type: str | None = None,
        include_secrets: bool = False,
    ) -> None:
        self.event_type_exposure = event_type_exposure or self.DEFAULT_EXPOSURE_EVENT_TYPE
        self.event_type_malware = event_type_malware or self.DEFAULT_MALWARE_EVENT_TYPE
        self.vendor_name = vendor_name or self.VENDOR_NAME
        self.product_name = product_name or self.PRODUCT_NAME
        self.log_type = log_type or self.LOG_TYPE
        # When True, sensitive fields (plaintext passwords, cookies, tokens, ...) are
        # kept on the record and carried into the UDM extensions so they persist onto
        # the case event. Defaults to False so secrets are stripped as before.
        self.include_secrets = include_secrets

    def convert_records(
        self,
        records: Iterable[dict[str, Any]],
        breach_catalog: Iterable[dict[str, Any]] | None = None,
        breach_catalog_by_id: dict[str, dict[str, Any]] | None = None,
        merge_endpoint_by_log_id: bool = True,
    ) -> list[dict[str, Any]]:
        base_records = [copy.deepcopy(record) for record in records or []]

        if breach_catalog_by_id is None and breach_catalog is not None:
            breach_catalog_by_id = self.build_breach_catalog_index(breach_catalog)

        enriched_records = [
            self.enrich_with_breach_catalog(record, breach_catalog_by_id)
            for record in base_records
        ]

        if merge_endpoint_by_log_id:
            enriched_records = self.merge_records(enriched_records)

        return [self.convert_record(record) for record in enriched_records]

    def convert_record(self, record: dict[str, Any]) -> dict[str, Any]:
        clean_record = self.sanitize_sensitive_fields(record)

        source_severity = self.get_severity(clean_record)
        severity_label = self.map_spycloud_to_severity_label(source_severity, clean_record)
        soar_severity = self.map_label_to_soar_severity(severity_label)
        risk_score = self.calculate_risk_score(clean_record)
        criticality = self.map_severity_to_criticality(severity_label)
        event_timestamp = self.get_event_timestamp(clean_record)
        product_log_id = self.get_product_log_id(clean_record)
        event_type = self.select_event_type(clean_record)

        # Make debug / downstream handling easier
        clean_record["spycloud_severity_label"] = severity_label
        clean_record["soar_severity"] = soar_severity
        clean_record["risk_score"] = risk_score
        clean_record["criticality"] = criticality

        event: dict[str, Any] = {
            "metadata": {
                "event_timestamp": event_timestamp,
                "event_type": event_type,
                "vendor_name": self.vendor_name,
                "product_name": self.product_name,
                "product_event_type": self.get_product_event_type(clean_record),
                "product_log_id": product_log_id,
                "log_type": self.log_type,
                "description": self.build_metadata_description(clean_record),
            },
            "security_result": self.build_security_result(
                record=clean_record,
                source_severity=source_severity,
                severity_label=severity_label,
                soar_severity=soar_severity,
                risk_score=risk_score,
                criticality=criticality,
            ),
            "extensions": self.build_extensions(clean_record),
        }

        principal = self.build_principal(clean_record)
        if principal:
            event["principal"] = principal

        target = self.build_target(clean_record)
        if target:
            event["target"] = target

        network = self.build_network(clean_record)
        if network:
            event["network"] = network

        about = self.build_about(clean_record)
        if about:
            event["about"] = about

        additional = self.build_additional(clean_record)
        if additional:
            event["additional"] = additional

        return self._prune_empty(event)

    def build_breach_catalog_index(
        self,
        breach_catalog: Iterable[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        for item in breach_catalog or []:
            key = self.first_present(item, ["id", "source_id", "catalog_id"])
            if key not in (None, ""):
                index[str(key)] = dict(item)
        return index

    def enrich_with_breach_catalog(
        self,
        record: dict[str, Any],
        breach_catalog_by_id: dict[str, dict[str, Any]] | None,
    ) -> dict[str, Any]:
        if not breach_catalog_by_id:
            return record

        source_id = self.first_present(record, ["source_id"])
        if source_id in (None, ""):
            return record

        catalog_entry = breach_catalog_by_id.get(str(source_id))
        if not catalog_entry:
            return record

        merged = dict(catalog_entry)
        merged.update(record)
        return merged

    def merge_records(self, records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Merge likely-related botnet / compass records into a single endpoint-centric record.

        Grouping preference:
        1. log_id
        2. infected_machine_id
        3. no merge for other records
        """
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        passthrough: list[dict[str, Any]] = []

        for record in records:
            merge_key = self.first_present(record, ["log_id", "infected_machine_id"])
            if self.is_malware_record(record) and merge_key not in (None, ""):
                grouped[str(merge_key)].append(record)
            else:
                passthrough.append(record)

        merged_records = [self._merge_group(group) for group in grouped.values()]
        merged_records.extend(passthrough)
        return merged_records

    def _normalize_collection_sources(self, values: Iterable[Any]) -> list[Any]:
        sources: list[Any] = []
        for value in values:
            if value in (None, "", [], {}):
                continue
            if isinstance(value, list):
                sources.extend(value)
            else:
                sources.append(value)
        return self.unique_preserve_order(sources)

    def _merge_group(self, group: list[dict[str, Any]]) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        keys = set()
        for item in group:
            keys.update(item.keys())

        for key in keys:
            values = [item.get(key) for item in group if item.get(key) not in (None, "", [], {})]
            if not values:
                continue

            if key == self.SOURCE_FIELD:
                merged[key] = self._normalize_collection_sources(values)
                continue

            first_value = values[0]
            if isinstance(first_value, list):
                combined: list[Any] = []
                for value in values:
                    if isinstance(value, list):
                        combined.extend(value)
                    else:
                        combined.append(value)
                merged[key] = self.unique_preserve_order(combined)
            else:
                merged[key] = values[0]

        merged["_merged_record_count"] = len(group)
        return merged

    def sanitize_sensitive_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        clean = {}
        for key, value in record.items():
            # When secret retention is enabled, keep sensitive fields on the record
            # so they flow into the UDM extensions; otherwise drop them.
            if key in self.SENSITIVE_DROP_FIELDS and not self.include_secrets:
                continue
            clean[key] = value

        password_present = any(
            record.get(key) not in (None, "", [], {})
            for key in ["password", "password_plaintext", "password_value", "password_raw"]
        )
        if password_present:
            clean["has_password"] = True

        password_type = record.get("password_type")
        if isinstance(password_type, str) and password_type.strip().lower() in {"plaintext", "plain", "cleartext"}:
            clean["has_plaintext_password"] = True

        return clean

    def build_principal(self, record: dict[str, Any]) -> dict[str, Any]:
        principal: dict[str, Any] = {}

        user = self.build_user(record)
        if user:
            principal["user"] = user

        hostname = self.first_present(record, ["user_hostname", "hostname"])
        if hostname:
            principal["hostname"] = str(hostname)

        asset_id = self.first_present(record, ["infected_machine_id", "log_id", "device_id"])
        if asset_id:
            principal["asset_id"] = str(asset_id)

        platform = self.first_present(record, ["user_os", "os"])
        if platform:
            principal["platform"] = str(platform)

        mac_address = self.first_present(record, ["mac_address"])
        if mac_address:
            principal["mac"] = [str(mac_address)]

        ip_addresses = self.normalize_to_list(self.first_present(record, ["ip_addresses", "ip_address", "ip"]))
        if ip_addresses:
            principal["ip"] = [str(ip) for ip in ip_addresses]

        file_info = self.build_principal_file(record)
        if file_info:
            principal["file"] = file_info

        return self._prune_empty(principal)

    def build_principal_file(self, record: dict[str, Any]) -> dict[str, Any]:
        path_value = self.first_present(record, ["infected_path"])
        if not path_value:
            return {}

        return {
            "full_path": str(path_value),
        }

    def build_user(self, record: dict[str, Any]) -> dict[str, Any]:
        user: dict[str, Any] = {}

        userid = self.first_present(record, ["email", "email_address", "username", "account_id"])
        if userid:
            user["userid"] = str(userid)

        email = self.first_present(record, ["email", "email_address"])
        if email:
            user["email_addresses"] = [str(email)]

        username = self.first_present(record, ["username"])
        if username:
            user["user_display_name"] = str(username)

        domain = self.first_present(record, ["email_domain", "user_sys_domain", "domain"])
        if domain:
            user["domain"] = str(domain)

        return self._prune_empty(user)

    def build_target(self, record: dict[str, Any]) -> dict[str, Any]:
        target: dict[str, Any] = {}

        url_value = self.first_present(record, ["target_url"])
        if url_value:
            target["url"] = str(url_value)

        domain_value = self.first_present(record, ["target_domain", "domain"])
        if domain_value:
            target["domain"] = str(domain_value)

        subdomain_value = self.first_present(record, ["target_subdomain", "subdomain"])
        if subdomain_value:
            target["hostname"] = str(subdomain_value)

        return self._prune_empty(target)

    def build_network(self, record: dict[str, Any]) -> dict[str, Any]:
        network: dict[str, Any] = {}

        email_from_record = self.first_present(record, ["email", "email_address"])
        if email_from_record:
            network.setdefault("email", {})["from"] = [str(email_from_record)]

        user_agent = self.first_present(record, ["user_agent"])
        if user_agent:
            network.setdefault("http", {})["user_agent"] = str(user_agent)

        url_value = self.first_present(record, ["target_url"])
        if url_value:
            network.setdefault("http", {})["url"] = str(url_value)

        return self._prune_empty(network)

    def build_about(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        about_items: list[dict[str, Any]] = []

        if self.first_present(record, ["target_url"]):
            about_items.append({
                "url": {
                    "url_string": str(record["target_url"]),
                }
            })

        if self.first_present(record, ["infected_path"]):
            about_items.append({
                "file": {
                    "full_path": str(record["infected_path"]),
                }
            })

        return [self._prune_empty(item) for item in about_items if self._prune_empty(item)]

    def build_additional(self, record: dict[str, Any]) -> dict[str, Any]:
        fields = [
            "has_password",
            "has_plaintext_password",
            "_merged_record_count",
            "spycloud_collection_source",
            "spycloud_severity_label",
            "soar_severity",
            "risk_score",
            "criticality",
        ]
        additional: dict[str, Any] = {}
        for field in fields:
            value = record.get(field)
            if value not in (None, "", [], {}):
                additional[field] = value
        return additional

    def build_extensions(self, record: dict[str, Any]) -> dict[str, Any]:
        extensions: dict[str, Any] = {}
        allowlist = self.EXTENSION_ALLOWLIST
        if self.include_secrets:
            # Carry the sensitive fields through so the parser can flatten them onto
            # the case event. Only reachable when secret retention is enabled.
            allowlist = allowlist | self.SENSITIVE_DROP_FIELDS
        for key in allowlist:
            value = record.get(key)
            if value in (None, "", [], {}):
                continue
            extensions[key] = self.normalize_scalar(value)
        return extensions

    def build_security_result(
        self,
        record: dict[str, Any],
        source_severity: int | None,
        severity_label: str,
        soar_severity: int,
        risk_score: int,
        criticality: str,
    ) -> dict[str, Any]:
        summary = self.build_security_summary(record)
        category = self.get_security_categories(record)
        confidence = self.map_confidence(record.get("confidence"))

        security_result: dict[str, Any] = {
            # This is the SecOps/alert severity equivalent
            "severity": soar_severity,
            "summary": summary,
            "category": category,
            "category_details": self.normalize_to_list(
                self.first_present(record, ["breach_category", "breach_main_category", "source_type"])
            ),
            "product_severity": self.map_product_severity_label(severity_label),
            "product_priority": self.map_product_priority_label(severity_label),
            "risk_score": risk_score,
            "criticality": criticality,
            "detection_fields": [
                {"key": "source_id", "value": str(record.get("source_id", ""))},
                {"key": "document_id", "value": str(record.get("document_id", ""))},
                {"key": "spycloud_source_severity", "value": "" if source_severity is None else str(source_severity)},
                {"key": "spycloud_severity_label", "value": severity_label},
            ],
        }

        threat_name = self.first_present(record, ["malware_family", "title", "short_title"])
        if threat_name:
            security_result["threat_name"] = str(threat_name)

        if confidence:
            security_result["confidence"] = confidence

        cleaned = self._prune_empty(security_result)
        if "detection_fields" in cleaned:
            cleaned["detection_fields"] = [
                item for item in cleaned["detection_fields"]
                if item.get("value") not in (None, "")
            ]
            if not cleaned["detection_fields"]:
                cleaned.pop("detection_fields", None)

        return cleaned

    def build_security_summary(self, record: dict[str, Any]) -> str:
        severity = self.get_severity(record)
        identifier = self.first_present(
            record,
            ["email", "username", "infected_machine_id", "log_id", "target_url", "domain"],
        ) or "record"

        if severity == 30:
            return f"SpyCloud stolen session (identity + session cookie) detected for {identifier}"
        if severity == 25 or self.is_malware_record(record):
            return f"SpyCloud malware-related credential exposure detected for {identifier}"
        if severity == 20:
            return f"SpyCloud plaintext credential exposure detected for {identifier}"
        if severity == 5:
            return f"SpyCloud informational exposure detected for {identifier}"
        if severity == 2:
            return f"SpyCloud email-only exposure detected for {identifier}"
        return f"SpyCloud exposure detected for {identifier}"

    def build_metadata_description(self, record: dict[str, Any]) -> str:
        parts = [
            self.first_present(record, ["title", "short_title"]),
            self.first_present(record, ["description"]),
        ]
        rendered = [str(part) for part in parts if part not in (None, "")]
        if rendered:
            return " | ".join(rendered)
        return self.build_security_summary(record)

    def get_product_event_type(self, record: dict[str, Any]) -> str:
        severity = self.get_severity(record)
        if severity == 30:
            return "SpyCloud Session Cookie Theft"
        if severity == 25 or self.is_malware_record(record):
            return "SpyCloud Malware Infection"
        if severity == 20:
            return "SpyCloud Plaintext Credential Exposure"
        if severity == 5:
            return "SpyCloud Informational Exposure"
        if severity == 2:
            return "SpyCloud Email Exposure"
        return "SpyCloud Exposure Record"

    def select_event_type(self, record: dict[str, Any]) -> str:
        if self.is_malware_record(record):
            return self.event_type_malware
        return self.event_type_exposure

    def is_malware_record(self, record: dict[str, Any]) -> bool:
        severity = self.get_severity(record)
        if severity == 25:
            return True

        return any(
            self.first_present(record, [field]) not in (None, "", [], {})
            for field in [
                "infected_machine_id",
                "log_id",
                "infected_time",
                "infected_path",
                "target_url",
                "user_hostname",
                "user_os",
            ]
        )

    def get_security_categories(self, record: dict[str, Any]) -> list[str]:
        categories: list[str] = []
        if self.is_malware_record(record):
            categories.append("SOFTWARE_MALICIOUS")
        if self.first_present(record, ["target_url"]):
            categories.append("PHISHING")
        if self.first_present(record, ["password_type", "has_password", "has_plaintext_password"]):
            categories.append("DATA_AT_REST")
        if not categories:
            categories.append("UNKNOWN_CATEGORY")
        return self.unique_preserve_order(categories)

    def get_event_timestamp(self, record: dict[str, Any]) -> str:
        for key in [
            "infected_time",
            "record_modification_date",
            "record_cracked_date",
            "record_addition_date",
            "spycloud_publish_date",
            "event_timestamp",
            "breach_date",
            "published_date",
            "created_at",
            "updated_at",
            "timestamp",
            "time",
            "date",
        ]:
            value = record.get(key)
            parsed = self.parse_datetime(value)
            if parsed:
                return parsed

        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def get_product_log_id(self, record: dict[str, Any]) -> str:
        direct_id = self.first_present(
            record,
            ["document_id", "log_id", "infected_machine_id", "id", "_id", "record_id"],
        )
        if direct_id not in (None, ""):
            return str(direct_id)

        identity_record = dict(record)
        identity_record.pop(self.SOURCE_FIELD, None)
        material = json.dumps(identity_record, sort_keys=True, default=str)
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    @staticmethod
    def get_severity(record: dict[str, Any]) -> int | None:
        value = record.get("severity")
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def map_spycloud_to_severity_label(
        self,
        severity: int | None,
        record: dict[str, Any] | None = None,
    ) -> str:
        if severity == 30:
            return "critical"
        if severity == 25:
            return "critical"
        if severity == 20:
            return "high"
        if severity == 5:
            return "medium"
        if severity == 2:
            return "low"

        if record and self.is_malware_record(record):
            return "critical"

        return "low"

    def map_label_to_soar_severity(self, label: str) -> int:
        return self.SOAR_SEVERITY_MAP.get(label, 40)

    def map_severity_to_criticality(self, label: str) -> str:
        mapping = {
            "low": "LOW",
            "medium": "MEDIUM",
            "high": "HIGH",
            "critical": "CRITICAL",
        }
        return mapping.get(label, "LOW")

    def calculate_risk_score(self, record: dict[str, Any]) -> int:
        """
        Smarter risk scoring:
        - Base from SpyCloud severity
        - Boost for infected-machine context
        - Boost for plaintext password
        - Boost for merged multi-record exposure
        - Boost slightly for targeted URLs/domains
        - Clamp to 100
        """
        severity = self.get_severity(record)
        score = {
            2: 30,
            5: 50,
            20: 80,
            25: 100,
            30: 100,
        }.get(severity, 30)

        if self.first_present(record, ["infected_machine_id", "log_id"]):
            score += 10

        if record.get("has_plaintext_password"):
            score += 10

        merged_count = record.get("_merged_record_count")
        try:
            if merged_count is not None and int(merged_count) > 1:
                score += 5
        except (TypeError, ValueError):
            pass

        if self.first_present(record, ["target_url", "target_domain", "target_subdomain"]):
            score += 5

        if self.first_present(record, ["malware_family"]):
            score += 5

        return min(100, score)

    @staticmethod
    def map_product_severity_label(label: str) -> str:
        mapping = {
            "low": "LOW",
            "medium": "MEDIUM",
            "high": "HIGH",
            "critical": "CRITICAL",
        }
        return mapping.get(label, "UNKNOWN_SEVERITY")

    @staticmethod
    def map_product_priority_label(label: str) -> str:
        mapping = {
            "low": "LOW_PRIORITY",
            "medium": "MEDIUM_PRIORITY",
            "high": "HIGH_PRIORITY",
            "critical": "HIGH_PRIORITY",
        }
        return mapping.get(label, "UNKNOWN_PRIORITY")

    @staticmethod
    def map_confidence(value: Any) -> str | None:
        """
        SpyCloud catalog confidence values are documented as:
        1 = High Confidence
        2 = Medium Confidence
        3 = Low Confidence
        """
        if value in (None, ""):
            return None

        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "high", "high_confidence"}:
                return "HIGH_CONFIDENCE"
            if lowered in {"2", "medium", "med", "medium_confidence"}:
                return "MEDIUM_CONFIDENCE"
            if lowered in {"3", "low", "low_confidence"}:
                return "LOW_CONFIDENCE"
            return None

        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return None

        if numeric == 1:
            return "HIGH_CONFIDENCE"
        if numeric == 2:
            return "MEDIUM_CONFIDENCE"
        if numeric == 3:
            return "LOW_CONFIDENCE"
        return None

    @staticmethod
    def parse_datetime(value: Any) -> str | None:
        if value in (None, ""):
            return None

        if isinstance(value, (int, float)):
            seconds = float(value)
            if seconds > 10_000_000_000:
                seconds = seconds / 1000.0
            return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if not isinstance(value, str):
            return None

        text = value.strip()
        if not text:
            return None

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        try:
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return None

    @staticmethod
    def first_present(record: dict[str, Any], keys: Iterable[str]) -> Any:
        for key in keys:
            value = record.get(key)
            if value not in (None, "", [], {}):
                return value
        return None

    @staticmethod
    def normalize_to_list(value: Any) -> list[Any]:
        if value in (None, "", [], {}):
            return []
        if isinstance(value, list):
            return value
        return [value]

    @staticmethod
    def normalize_scalar(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, list):
            return [SpyCloudUdmConverter.normalize_scalar(item) for item in value]
        if isinstance(value, dict):
            return {str(k): SpyCloudUdmConverter.normalize_scalar(v) for k, v in value.items()}
        return str(value)

    @staticmethod
    def unique_preserve_order(values: Iterable[Any]) -> list[Any]:
        result: list[Any] = []
        seen = set()
        for value in values:
            marker = json.dumps(value, sort_keys=True, default=str) if isinstance(value, (dict, list)) else str(value)
            if marker in seen:
                continue
            seen.add(marker)
            result.append(value)
        return result

    def _prune_empty(self, value: Any) -> Any:
        if isinstance(value, dict):
            cleaned = {
                key: self._prune_empty(val)
                for key, val in value.items()
                if val not in (None, "", [], {})
            }
            return {key: val for key, val in cleaned.items() if val not in (None, "", [], {})}

        if isinstance(value, list):
            cleaned_list = [self._prune_empty(item) for item in value]
            return [item for item in cleaned_list if item not in (None, "", [], {})]

        return value


__all__ = ["SpyCloudUdmConverter"]