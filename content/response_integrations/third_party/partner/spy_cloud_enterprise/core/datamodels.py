"""
Data models for presenting SpyCloud Enterprise breach data in the case wall.

These models wrap raw SpyCloud Watchlist records (optionally enriched with the
breach catalog) and expose safe, presentation-oriented views:

- ``to_json``       -> structured record with all sensitive values removed.
- ``to_table``      -> a curated, ordered row for a case-wall data table.
- ``summarize``     -> a per-entity aggregate (counts, worst severity, dates).
- ``build_insight`` -> a short HTML summary for an entity insight.

Guiding principle (mirrors the connector/converter): never surface plaintext
passwords, cookies, tokens, or other secrets. We only ever report metadata and
booleans such as "plaintext password exposed: Yes".
"""
from __future__ import annotations

import html
from typing import Any, Iterable

from .spycloud_udm_converter import SpyCloudUdmConverter

# Reuse the converter's single source of truth for secret field names, then add a
# fragment-based guard for defense in depth so unexpected sensitive keys are also
# dropped.
SENSITIVE_DROP_FIELDS = set(SpyCloudUdmConverter.SENSITIVE_DROP_FIELDS)
SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "cookie",
    "token",
    "secret",
    "credential",
    "private_key",
    "cc_",
    "bank_",
    "taxid",
    "ssn",
    "national_id",
)

_CONVERTER = SpyCloudUdmConverter()

# Source severity -> malware/session-theft classification. Records at or above the
# credential-exposure tier (20) are treated as high risk for entity flagging.
HIGH_RISK_SEVERITY_THRESHOLD = 20
MALWARE_SEVERITY_THRESHOLD = 25


def _is_sensitive_key(key: Any) -> bool:
    key_lower = str(key).lower()
    if key_lower in SENSITIVE_DROP_FIELDS:
        return True
    return any(fragment in key_lower for fragment in SENSITIVE_KEY_FRAGMENTS)


def _clean_str(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    return str(value).strip()


def _as_list(value: Any) -> list[str]:
    if value in (None, "", [], {}):
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def _yes_no(flag: bool) -> str:
    return "Yes" if flag else "No"


class SpyCloudExposure:
    """A single SpyCloud Watchlist exposure record, presented safely."""

    def __init__(
        self,
        raw_record: dict[str, Any],
        catalog_by_source_id: dict[Any, dict[str, Any]] | None = None,
    ) -> None:
        self.raw: dict[str, Any] = raw_record if isinstance(raw_record, dict) else {}
        catalog_by_source_id = catalog_by_source_id or {}
        self.catalog: dict[str, Any] = {}

        source_id = self.raw.get("source_id")
        if source_id is not None:
            entry = catalog_by_source_id.get(source_id) or catalog_by_source_id.get(str(source_id))
            if isinstance(entry, dict):
                self.catalog = entry

    # -- severity / risk -------------------------------------------------

    @property
    def severity(self) -> int | None:
        try:
            return int(self.raw.get("severity"))
        except (TypeError, ValueError):
            return None

    @property
    def severity_label(self) -> str:
        severity = self.severity
        if severity is None:
            return ""
        return _CONVERTER.map_spycloud_to_severity_label(severity) or ""

    @property
    def risk_score(self) -> int | None:
        try:
            return int(_CONVERTER.calculate_risk_score(self.raw))
        except (TypeError, ValueError):
            return None

    # -- identity --------------------------------------------------------

    @property
    def emails(self) -> list[str]:
        return _as_list(self.raw.get("email"))

    @property
    def usernames(self) -> list[str]:
        return _as_list(self.raw.get("username"))

    @property
    def ips(self) -> list[str]:
        return _as_list(self.raw.get("ip_addresses"))

    @property
    def domains(self) -> list[str]:
        domains: list[str] = []
        for key in ("domain", "email_domain", "target_domain", "target_subdomain"):
            domains.extend(_as_list(self.raw.get(key)))
        # Preserve order while de-duplicating.
        return list(dict.fromkeys(domains))

    @property
    def hostnames(self) -> list[str]:
        return _as_list(self.raw.get("user_hostname"))

    def identity_values(self) -> set[str]:
        """All lower-cased identifiers this record could match a case entity on."""
        values: set[str] = set()
        for group in (self.emails, self.usernames, self.ips, self.domains, self.hostnames):
            for value in group:
                values.add(value.lower())
        return values

    def matches(self, identifier: str) -> bool:
        if not identifier:
            return False
        return identifier.strip().lower() in self.identity_values()

    # -- breach metadata -------------------------------------------------

    @property
    def breach_title(self) -> str:
        for source in (self.catalog, self.raw):
            for key in ("title", "short_title"):
                value = _clean_str(source.get(key))
                if value:
                    return value
        return ""

    @property
    def breach_site(self) -> str:
        return _clean_str(self.catalog.get("site") or self.raw.get("site"))

    @property
    def publish_date(self) -> str:
        for key in ("spycloud_publish_date", "record_addition_date", "published_date", "breach_date"):
            value = _clean_str(self.raw.get(key))
            if value:
                return value
        return _clean_str(self.catalog.get("spycloud_publish_date"))

    # -- secret presence (never the values) ------------------------------

    @property
    def has_plaintext_password(self) -> bool:
        if bool(self.raw.get("has_plaintext_password")):
            return True
        if _clean_str(self.raw.get("password_plaintext")):
            return True
        return _clean_str(self.raw.get("password_type")).lower() == "plaintext"

    @property
    def has_password(self) -> bool:
        if bool(self.raw.get("has_password")):
            return True
        return self.has_plaintext_password or bool(_clean_str(self.raw.get("password")))

    @property
    def has_cookies(self) -> bool:
        return any(
            _clean_str(self.raw.get(key))
            for key in ("cookies", "cookie_data", "form_cookies_data")
        )

    @property
    def is_malware(self) -> bool:
        severity = self.severity
        if severity is not None and severity >= MALWARE_SEVERITY_THRESHOLD:
            return True
        return bool(_clean_str(self.raw.get("infected_machine_id")))

    @property
    def is_high_risk(self) -> bool:
        severity = self.severity
        if severity is not None and severity >= HIGH_RISK_SEVERITY_THRESHOLD:
            return True
        return self.has_plaintext_password

    # -- presentation views ----------------------------------------------

    def to_json(self) -> dict[str, Any]:
        """Structured record with every sensitive field stripped out."""
        safe = {
            key: value
            for key, value in self.raw.items()
            if not _is_sensitive_key(key)
        }
        safe.update(
            {
                "breach_title": self.breach_title,
                "breach_site": self.breach_site,
                "severity_label": self.severity_label,
                "risk_score": self.risk_score,
                "has_password": self.has_password,
                "has_plaintext_password": self.has_plaintext_password,
                "has_cookies": self.has_cookies,
            }
        )
        return safe

    def to_table(self) -> dict[str, Any]:
        """A curated, ordered row for a case-wall data table."""
        return {
            "Severity": self.severity if self.severity is not None else "",
            "Severity Label": self.severity_label,
            "Risk Score": self.risk_score if self.risk_score is not None else "",
            "Breach Title": self.breach_title,
            "Breach Site": self.breach_site,
            "Source ID": _clean_str(self.raw.get("source_id")),
            "Email": ", ".join(self.emails),
            "Username": ", ".join(self.usernames),
            "Domain": ", ".join(self.domains),
            "IP Addresses": ", ".join(self.ips),
            "Infected Machine ID": _clean_str(self.raw.get("infected_machine_id")),
            "Malware Family": _clean_str(self.raw.get("malware_family")),
            "Publish Date": self.publish_date,
            "Infected Time": _clean_str(self.raw.get("infected_time")),
            "Plaintext Password Exposed": _yes_no(self.has_plaintext_password),
            "Password Present": _yes_no(self.has_password),
            "Cookies Present": _yes_no(self.has_cookies),
            "Document ID": _clean_str(self.raw.get("document_id")),
        }


def summarize(exposures: Iterable[SpyCloudExposure]) -> dict[str, Any]:
    """Aggregate a list of exposures (typically for one entity) into a flat summary."""
    exposures = list(exposures)

    severities = [exp.severity for exp in exposures if exp.severity is not None]
    risk_scores = [exp.risk_score for exp in exposures if exp.risk_score is not None]
    source_ids = {
        _clean_str(exp.raw.get("source_id"))
        for exp in exposures
        if _clean_str(exp.raw.get("source_id"))
    }
    publish_dates = sorted(exp.publish_date for exp in exposures if exp.publish_date)
    titles = list(
        dict.fromkeys(exp.breach_title for exp in exposures if exp.breach_title)
    )

    max_severity = max(severities) if severities else None
    max_label = ""
    if max_severity is not None:
        max_label = _CONVERTER.map_spycloud_to_severity_label(max_severity) or ""

    return {
        "Exposure Count": len(exposures),
        "Breach Count": len(source_ids),
        "Max Severity": max_severity if max_severity is not None else "",
        "Max Severity Label": max_label,
        "Max Risk Score": max(risk_scores) if risk_scores else "",
        "Latest Publish Date": publish_dates[-1] if publish_dates else "",
        "Plaintext Password Exposed": _yes_no(any(exp.has_plaintext_password for exp in exposures)),
        "Malware Infection": _yes_no(any(exp.is_malware for exp in exposures)),
        "High Risk": _yes_no(any(exp.is_high_risk for exp in exposures)),
        "Breach Titles": ", ".join(titles[:10]),
    }


def is_high_risk(exposures: Iterable[SpyCloudExposure]) -> bool:
    return any(exp.is_high_risk for exp in exposures)


def build_insight(identifier: str, exposures: Iterable[SpyCloudExposure]) -> str:
    """A short HTML insight summarizing exposures for a single entity."""
    exposures = list(exposures)
    summary = summarize(exposures)

    color = "#d9363e" if is_high_risk(exposures) else "#f5a623"
    rows = "".join(
        f"<tr><td style='padding:2px 8px;'><strong>{key}</strong></td>"
        f"<td style='padding:2px 8px;'>{value}</td></tr>"
        for key, value in summary.items()
    )
    return (
        f"<h2 style='color:{color};'>SpyCloud Exposures &mdash; {identifier}</h2>"
        f"<table style='border-collapse:collapse;'>{rows}</table>"
    )


# ---------------------------------------------------------------------------
# In-case alert presentation
#
# The connector/parser already fetched, normalized, and (crucially) stripped
# secrets from every SpyCloud record, flattening the safe fields onto each
# alert's security event under ``additional_properties`` with a ``spycloud_``
# prefix. These helpers present that in-case data as a case-wall table without
# any additional API calls. See core/Parser.flatten_udm_event_for_alert.
# ---------------------------------------------------------------------------

SPYCLOUD_EVENT_PREFIX = "spycloud_"

# Sensitive breach values surfaced in the table when the connector's "Include
# Plaintext Secrets" option is enabled. These flattened event keys carry the raw
# secret; each is empty unless secret retention was on at collection time. Order
# is (event-property key, human column label).
SECRET_DISPLAY_FIELDS = (
    ("spycloud_password_plaintext", "Plaintext Password"),
    ("spycloud_password", "Password (as stored)"),
    ("spycloud_password_value", "Password Value"),
    ("spycloud_password_raw", "Password (raw)"),
    ("spycloud_new_password", "New Password"),
    ("spycloud_old_password", "Old Password"),
    ("spycloud_account_password", "Account Password"),
    ("spycloud_credentials", "Credentials"),
    ("spycloud_private_key_password", "Private Key Password"),
    ("spycloud_account_secret", "Account Secret"),
    ("spycloud_account_secret_question", "Account Secret Question"),
    ("spycloud_api_token", "API Token"),
    ("spycloud_api_token_secret", "API Token Secret"),
    ("spycloud_cookies", "Cookies"),
    ("spycloud_cookie_data", "Cookie Data"),
    ("spycloud_form_cookies_data", "Form Cookies Data"),
    ("spycloud_form_post_data", "Form Post Data"),
    ("spycloud_cc_number", "Credit Card Number"),
    ("spycloud_cc_code", "Credit Card Code"),
    ("spycloud_bank_number", "Bank Number"),
    ("spycloud_bank_routing_number", "Bank Routing Number"),
    ("spycloud_taxid", "Tax ID"),
)

# Non-secret metadata columns appended after the curated columns so the data table
# carries the full flattened record, not just a curated subset.
EXTRA_METADATA_FIELDS = (
    ("spycloud_password_type", "Password Type"),
    ("spycloud_infected_time", "Infected Time"),
    ("spycloud_infected_path", "Infected Path"),
    ("spycloud_record_modification_date", "Record Modification Date"),
    ("spycloud_record_cracked_date", "Record Cracked Date"),
    ("spycloud_target_url", "Target URL"),
    ("spycloud_target_domain", "Target Domain"),
    ("spycloud_target_subdomain", "Target Subdomain"),
    ("spycloud_user_hostname", "User Hostname"),
    ("spycloud_user_os", "User OS"),
    ("spycloud_user_browser", "User Browser"),
    ("spycloud_user_agent", "User Agent"),
    ("spycloud_country_code", "Country Code"),
    ("spycloud_timezone", "Timezone"),
    ("spycloud_log_id", "Log ID"),
    ("spycloud_breach_main_category", "Breach Main Category"),
    ("spycloud_breach_category", "Breach Category"),
    ("spycloud_confidence", "Confidence"),
    ("spycloud_tlp", "TLP"),
    ("spycloud_criticality", "Criticality"),
    ("spycloud_mapped_soar_severity", "Mapped SOAR Severity"),
    ("spycloud_merged_record_count", "Merged Record Count"),
)


def _truthy(value: Any) -> bool:
    """Interpret a flattened event value (often a string) as a boolean.

    SecOps stores security-event ``additional_properties`` as strings, so a
    boolean written by the connector comes back as ``"true"`` / ``"false"``.
    """
    if isinstance(value, bool):
        return value
    if value in (None, "", 0, "0"):
        return False
    return str(value).strip().lower() in ("true", "yes", "1", "t")


def is_spycloud_event(props: dict[str, Any] | None) -> bool:
    """True when a security event's properties came from the SpyCloud parser."""
    if not isinstance(props, dict):
        return False
    if str(props.get("device_vendor", "")).strip().lower() == "spycloud":
        return True
    return any(str(key).startswith(SPYCLOUD_EVENT_PREFIX) for key in props)


def event_row(alert_name: str, props: dict[str, Any]) -> dict[str, Any]:
    """A curated, ordered case-wall row for one in-case SpyCloud exposure event."""
    has_plaintext = _truthy(props.get("spycloud_has_plaintext_password"))
    has_password = _truthy(props.get("spycloud_has_password")) or has_plaintext
    publish_date = (
        _clean_str(props.get("spycloud_record_addition_date"))
        or _clean_str(props.get("spycloud_record_modification_date"))
        or _clean_str(props.get("spycloud_infected_time"))
    )
    row = {
        "Alert": _clean_str(alert_name),
        "SpyCloud Severity": _clean_str(props.get("spycloud_source_severity")),
        "Severity Label": _clean_str(props.get("spycloud_severity_label")),
        "Risk Score": _clean_str(props.get("spycloud_risk_score") or props.get("risk_score")),
        "Breach Title": _clean_str(props.get("spycloud_breach_title")),
        "Breach Site": _clean_str(props.get("spycloud_breach_site")),
        "Source ID": _clean_str(props.get("spycloud_source_id")),
        "Email": _clean_str(props.get("spycloud_email")),
        "Username": _clean_str(props.get("spycloud_username")),
        "Domain": _clean_str(props.get("spycloud_domain")),
        "Infected Machine ID": _clean_str(props.get("spycloud_infected_machine_id")),
        "Malware Family": _clean_str(props.get("spycloud_malware_family")),
        "Publish Date": publish_date,
        "Plaintext Password Exposed": _yes_no(has_plaintext),
        "Password Present": _yes_no(has_password),
        "Collection Source": _clean_str(props.get("spycloud_collection_source")),
        "Document ID": _clean_str(props.get("spycloud_document_id")),
    }
    # Append the remaining metadata columns so the table carries the full record.
    for key, label in EXTRA_METADATA_FIELDS:
        row[label] = _clean_str(props.get(key))
    # Append the raw secret values. These are empty unless the connector persisted
    # them (Include Plaintext Secrets); when present they are shown verbatim.
    for key, label in SECRET_DISPLAY_FIELDS:
        row[label] = _clean_str(props.get(key))
    return row


def event_json(props: dict[str, Any]) -> dict[str, Any]:
    """A structured view of one in-case SpyCloud exposure event.

    Every flattened ``spycloud_`` field is included. When the connector persisted
    plaintext secrets (Include Plaintext Secrets), those values are present here as
    well; otherwise the secret keys are simply empty.
    """
    return {
        key: value
        for key, value in props.items()
        if str(key).startswith(SPYCLOUD_EVENT_PREFIX)
    }


# Columns shown in the case-wall insight panel. The insight is a compact,
# at-a-glance summary; the full column set stays in the case-wall data table.
_INSIGHT_COLUMNS = (
    "Severity Label",
    "Breach Title",
    "Email",
    "Username",
    "Plaintext Password Exposed",
    "Malware Family",
)

# Cap the rows rendered inline so a large case does not produce an unwieldy
# panel. The data table and JSON result still carry every row.
INSIGHT_MAX_ROWS = 25


def _row_is_high_risk(row: dict[str, Any]) -> bool:
    """A rendered ``event_row`` represents a high-risk exposure."""
    return (
        str(row.get("Plaintext Password Exposed", "")).strip().lower() == "yes"
        or bool(_clean_str(row.get("Malware Family")))
    )


def insight_severity(rows: Iterable[dict[str, Any]]) -> int:
    """Pick an ``InsightSeverity`` value for the case insight from the rows.

    Returns the raw int (ERROR=2, WARN=1) so callers need not import the enum;
    the values match ``soar_sdk.SiemplifyDataModel.InsightSeverity``.
    """
    return 2 if any(_row_is_high_risk(row) for row in rows) else 1


def build_case_insight_html(rows: list[dict[str, Any]]) -> str:
    """Render in-case SpyCloud exposure rows as a compact case-wall insight.

    Values are HTML-escaped and no secret values are ever included (the rows
    come from ``event_row``, which only carries metadata and Yes/No booleans).
    """
    total = len(rows)
    high_risk = sum(1 for row in rows if _row_is_high_risk(row))
    with_password = sum(
        1 for row in rows
        if str(row.get("Plaintext Password Exposed", "")).strip().lower() == "yes"
    )

    # Convey risk with a labelled badge, not title color alone: the word plus a
    # symbol stays legible for colorblind users and on any theme. The badge sets
    # both its own foreground and background, so contrast holds on light or dark.
    if high_risk:
        badge = (
            "<span style='display:inline-block;padding:1px 8px;border-radius:3px;"
            "background:#b3261e;color:#ffffff;font-size:0.8em;font-weight:bold;"
            "vertical-align:middle;'>&#9888; HIGH RISK</span>"
        )
    else:
        badge = (
            "<span style='display:inline-block;padding:1px 8px;border-radius:3px;"
            "background:#1a5fb4;color:#ffffff;font-size:0.8em;font-weight:bold;"
            "vertical-align:middle;'>REVIEW</span>"
        )

    header = (
        "<th style='padding:4px 8px;text-align:left;border-bottom:1px solid #ccc;'>"
        + "</th><th style='padding:4px 8px;text-align:left;border-bottom:1px solid #ccc;'>".join(
            html.escape(column) for column in _INSIGHT_COLUMNS
        )
        + "</th>"
    )

    body_rows: list[str] = []
    for row in rows[:INSIGHT_MAX_ROWS]:
        cells = "".join(
            f"<td style='padding:2px 8px;border-bottom:1px solid #eee;'>"
            f"{html.escape(_clean_str(row.get(column)))}</td>"
            for column in _INSIGHT_COLUMNS
        )
        body_rows.append(f"<tr>{cells}</tr>")

    more = ""
    if total > INSIGHT_MAX_ROWS:
        more = (
            f"<p style='margin:6px 0 0;font-style:italic;'>"
            f"Showing {INSIGHT_MAX_ROWS} of {total} exposures &mdash; "
            f"expand &ldquo;Show all fields&rdquo; below or see the "
            f"&ldquo;{html.escape('SpyCloud Watchlist Exposures')}&rdquo; "
            f"table for the rest.</p>"
        )

    return (
        f"<h2 style='margin:0 0 4px;'>SpyCloud Watchlist Exposures &nbsp;{badge}</h2>"
        f"<p style='margin:0 0 8px;'>{total} exposure(s) on this case &mdash; "
        f"{high_risk} high risk, {with_password} with a plaintext password.</p>"
        f"<table style='border-collapse:collapse;width:100%;'>"
        f"<thead><tr>{header}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody></table>"
        f"{more}"
        f"{build_full_detail_html(rows)}"
    )


def _rows_contain_secrets(rows: list[dict[str, Any]]) -> bool:
    """True if any row carries a non-empty value in a secret column."""
    secret_labels = [label for _key, label in SECRET_DISPLAY_FIELDS]
    return any(
        _clean_str(row.get(label)) for row in rows for label in secret_labels
    )


def build_full_detail_html(rows: list[dict[str, Any]]) -> str:
    """A collapsible ``<details>`` block rendering every column for every row.

    Rendered collapsed by default so the compact summary stays readable; clicking
    the disclosure triangle expands the full-width table with all fields. When
    plaintext secrets are present a warning banner is shown inside the block.
    """
    if not rows:
        return ""

    # event_row emits a stable key set, so the first row defines the columns.
    columns = list(rows[0].keys())

    header = "".join(
        f"<th style='padding:4px 8px;text-align:left;border-bottom:1px solid #ccc;"
        f"white-space:nowrap;'>{html.escape(column)}</th>"
        for column in columns
    )

    body_rows: list[str] = []
    for row in rows:
        cells = "".join(
            f"<td style='padding:2px 8px;border-bottom:1px solid #eee;"
            f"vertical-align:top;'>{html.escape(_clean_str(row.get(column)))}</td>"
            for column in columns
        )
        body_rows.append(f"<tr>{cells}</tr>")

    warning = ""
    if _rows_contain_secrets(rows):
        warning = (
            "<p style='margin:6px 0;padding:4px 8px;background:#fbe9e7;color:#b3261e;"
            "border-left:3px solid #b3261e;font-weight:bold;'>"
            "&#9888; This table contains plaintext secrets (passwords / cookies / "
            "tokens). Handle and share accordingly.</p>"
        )

    return (
        "<details style='margin-top:10px;'>"
        "<summary style='cursor:pointer;font-weight:bold;'>"
        f"Show all fields ({len(columns)} columns &times; {len(rows)} rows)</summary>"
        f"{warning}"
        "<div style='overflow-x:auto;'>"
        "<table style='border-collapse:collapse;width:100%;font-size:0.85em;'>"
        f"<thead><tr>{header}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody></table></div></details>"
    )
