"""
CybleAlertMapper — transforms raw Cyble alert records into SecOps-compatible
alert objects and back.

Two emission guarantees that drive the design:
  1. **Vendor-neutral field names.** Custom fields never carry a "Cyble" prefix
     — they're plain semantic names (Url, Username, MalwareFamily, …) so the
     integration can be re-skinned for any customer without renaming SOAR-side
     Custom Field registrations.
  2. **Every defined field is always emitted.** When the upstream payload has
     a missing or null value the field is still written to the SOAR alert with
     an empty string. Analysts see a consistent set of columns on every alert,
     regardless of which service produced it or how complete the record is.

Responsibilities:
  - Field normalization and safe .get() access (schema-change resilience)
  - Severity / status mapping
  - Common top-level field extraction (every service)
  - Service-specific field extraction (ssl_expiry, github, stealer_logs, …)
  - Idempotency key construction
  - SecOps → Cyble reverse mapping for bidirectional updates
"""
from __future__ import annotations

import json
import logging
from datetime import timezone
from typing import Optional, Dict, Any

from .constants import (
    CYBLE_TO_SECOPS_SEVERITY,
    SECOPS_TO_CYBLE_SEVERITY,
    CYBLE_TO_SECOPS_STATUS,
    SECOPS_TO_CYBLE_STATUS,
    SECOPS_INT_TO_CYBLE_SEVERITY,
    CYBLE_STATUSES,
    HIGH_PRIORITY_SERVICES,
    COMMON_FIELDS,
    # Common / generic
    FIELD_ALERT_ID,
    FIELD_DATA_ID,
    FIELD_SERVICE,
    FIELD_KEYWORD,
    FIELD_BUCKET,
    FIELD_TAGS,
    FIELD_RISK_SCORE,
    FIELD_LAST_SYNC_AT,
    FIELD_LLM_EXPLANATION,
    FIELD_URL,
    FIELD_USERNAME,
    FIELD_DOMAIN,
    # Code-analysis shared
    FIELD_REPO,
    FIELD_FILENAME,
    FIELD_OWNER,
    # Asset-discovery shared
    FIELD_ASSET,
    FIELD_LAST_DETECTED_AT,
    FIELD_KEYWORD_ID,
    # ssl_expiry
    FIELD_EXPIRY_DATE,
    FIELD_DAYS_TO_EXPIRY,
    FIELD_SSL_PORT,
    FIELD_SSL_IS_VALID,
    FIELD_SSL_ISSUED,
    FIELD_SSL_HASH,
    FIELD_SSL_AGE_DAYS,
    FIELD_SSL_DETAIL,
    FIELD_SSL_VERSION,
    FIELD_SSL_TITLE,
    FIELD_COUNTRY_CODE,
    # github
    FIELD_FILE_URL,
    FIELD_FILE_PATH,
    FIELD_GIT_URL,
    FIELD_FILE_API_URL,
    FIELD_COMMIT_SHA,
    FIELD_MATCH_SCORE,
    FIELD_REPO_URL,
    FIELD_REPO_DESCRIPTION,
    FIELD_REPO_FULL_NAME,
    FIELD_REPO_LANGUAGE,
    FIELD_REPO_PRIVATE,
    FIELD_REPO_STARS,
    FIELD_REPO_FORKS,
    FIELD_REPO_OWNER_LOGIN,
    FIELD_MATCH_FRAGMENT,
    FIELD_MATCHED_TEXT,
    # cloud_storage
    FIELD_STORAGE_BUCKET,
    FIELD_STORAGE_BUCKET_ID,
    FIELD_STORAGE_OBJECT_ID,
    # Title-group services
    FIELD_TITLE,
    # postman
    FIELD_DEVELOPER_URL,
    FIELD_IS_PUBLIC,
    FIELD_CATEGORY,
    FIELD_VIEWS,
    FIELD_FORKS,
    FIELD_WATCHERS,
    FIELD_APIS_COUNT,
    FIELD_COLLECTIONS_COUNT,
    FIELD_WORKSPACES_COUNT,
    FIELD_ICON_URL,
    FIELD_POSTMAN_KEY,
    FIELD_SOURCE_NAME,
    FIELD_SCRAP_TIME,
    FIELD_LAST_UPDATED_AT,
    FIELD_METADATA,
    # Cross-service reusable
    FIELD_CONTENT,
    FIELD_DETAILS,
    FIELD_EXTENSION,
    FIELD_UPDATED_FIELDS,
    FIELD_S3_KEY,
    FIELD_TYPE,
    FIELD_TIMESTAMP,
    FIELD_VERSION,
    FIELD_HOST,
    FIELD_PORT,
    FIELD_PROTOCOL,
    FIELD_SOURCE,
    FIELD_CVE,
    FIELD_AUTHOR,
    FIELD_CONTENT_ADDED_ON,
    FIELD_INDUSTRY,
    FIELD_HASH,
    FIELD_VICTIM,
    FIELD_THREAT_ACTOR,
    FIELD_UPDATED_DATE,
    FIELD_CREATED_DATE,
    FIELD_SENTIMENT,
    FIELD_NAME,
    FIELD_LANGUAGE,
    FIELD_MESSAGE,
    FIELD_SCORE,
    # compromised_endpoints_cookies
    FIELD_COOKIE_DATA,
    FIELD_IS_UPDATED_ES,
    FIELD_SOURCE_ID,
    # compromised_files
    FIELD_FILE_OBJ_PATH,
    FIELD_LOG_NAME,
    FIELD_LOG_OBJ_PATH,
    FIELD_RELATIVE_PATH,
    # advisory
    FIELD_ADVISORY_ID,
    # darkweb_marketplaces
    FIELD_MARKETPLACE,
    FIELD_CONTENT_UPDATED_ON,
    FIELD_VENDOR,
    FIELD_PRICE,
    FIELD_DATA_SIZE,
    FIELD_REGION,
    FIELD_INFO,
    FIELD_OUTLOOK,
    FIELD_BROWSER,
    FIELD_OS,
    FIELD_USER_AGENT,
    FIELD_IP,
    FIELD_INSTALLED_DATE,
    FIELD_COOKIES,
    FIELD_COOKIES_DATE,
    FIELD_COMPANY_LEAKED,
    FIELD_CONFIG_UPDATE,
    FIELD_DATA_STRUCT,
    FIELD_LINKS,
    FIELD_EVENT_DATE,
    FIELD_EVENT_DATE_TIMESTAMP,
    FIELD_BANK_BIN,
    FIELD_BANK_COUNTRY,
    FIELD_BANK_PHONE,
    FIELD_BANK_REAL_NAME,
    FIELD_BANK_REF_NAME,
    FIELD_BANK_SITE,
    FIELD_CARD_BRAND,
    FIELD_CARD_NUMBER,
    FIELD_CARD_TYPE,
    FIELD_CARD_CVR,
    FIELD_CARD_CVV,
    FIELD_CARD_EXPIRY,
    FIELD_CARD_LEVEL,
    # darkweb_data_breaches
    FIELD_BREACH_SOURCE,
    FIELD_BREACH_DATE,
    # domain_watchlist
    FIELD_NEW_DNS_RECORD,
    FIELD_OLD_DNS_RECORD,
    FIELD_SCREENSHOT_OBJECT_KEY,
    FIELD_SCREENSHOT_TIMESTAMP,
    # hacktivism
    FIELD_CHANNEL_NAME,
    FIELD_ATTACKER,
    FIELD_MIRROR,
    FIELD_SERVER,
    FIELD_SOURCE_WEBSITE,
    FIELD_TEAM,
    FIELD_UNIQUE_KEY,
    # i2p
    FIELD_SEARCH_ENGINE,
    FIELD_SEARCH_KEYWORD,
    # ip_risk_score
    FIELD_OLD_RISK_SCORE,
    FIELD_NEW_RISK_SCORE,
    # vulnerability
    FIELD_CONFIDENCE,
    FIELD_FIRST_SEEN_ON,
    FIELD_LAST_SEEN_ON,
    FIELD_VULNERABILITY_ID,
    FIELD_VULNERABILITY_TYPE,
    # new_port
    FIELD_LAST_DETECTED_AT,
    # flash_report
    FIELD_FOR_COMPANY,
    FIELD_REPORT_ID,
    # ot_ics
    FIELD_ASN,
    FIELD_SOURCE_IP,
    FIELD_DATA_TYPE,
    FIELD_DEST_PORT,
    FIELD_IP_REPUTATION,
    # pastebin
    FIELD_PASTE_TYPE,
    # phishing
    FIELD_BRAND,
    FIELD_BRAND_INDUSTRY,
    FIELD_BRAND_WEBSITE,
    FIELD_AWS_OBJECT_NAME,
    FIELD_CONTENT_MATCH,
    FIELD_DETECTED_AT,
    FIELD_DO_OBJECT_NAME,
    FIELD_DOMAIN_RANKING,
    FIELD_HOST_NAME,
    FIELD_IS_DELETED,
    FIELD_IS_LIVE,
    FIELD_IS_TAKEDOWN,
    FIELD_LAST_LIVE_ON,
    FIELD_LOGO_MATCH,
    FIELD_PHISHING_KEYWORD_NAME,
    FIELD_PHISHING_STATUS,
    FIELD_SCREENSHOT_URL,
    FIELD_STATUS_CODE,
    FIELD_WATERMARKING_DATA,
    # product_vulnerability (overrides common Description with the richer
    # nested description string from data.description)
    FIELD_DESCRIPTION,
    FIELD_COMPANY,
    FIELD_PRODUCT,
    FIELD_LAST_MODIFIED_DATE,
    FIELD_PUBLISHED_DATE,
    FIELD_NEW_CVE_DETAILS,
    FIELD_OLD_CVE_DETAILS,
    FIELD_SEVERITY_DATA,
    FIELD_SOFTWARE_DETAILS,
    # ransomware_updates
    FIELD_ADDED_BY,
    FIELD_IS_PUBLISHED,
    FIELD_SCREENSHOTS_PATH,
    FIELD_TA_LINK,
    FIELD_TM_LINK,
    FIELD_UPDATED_BY,
    # darkweb_ransomware
    FIELD_DOCUMENT_CREATED_YEAR,
    FIELD_ORIGINAL_FILENAME,
    # social_media_monitoring
    FIELD_CONFIDENCE_SCORE,
    FIELD_FINDING_ID,
    FIELD_LOCATION,
    FIELD_WEIGHTAGE,
    FIELD_FOLLOWERS,
    FIELD_FOLLOWING,
    FIELD_IS_VERIFIED,
    FIELD_CREATOR_URL,
    FIELD_CREATOR_TYPE,
    FIELD_HASHTAGS,
    FIELD_POSTED_AT,
    FIELD_MEDIA,
    FIELD_EXCERPTS,
    FIELD_EXTRACTED_DOMAINS,
    FIELD_EXTRACTED_URLS,
    FIELD_EXTRACTED_SUBDOMAINS,
    FIELD_EXTRACTED_IPS,
    FIELD_SUSPICIOUS_URLS,
    FIELD_MENTIONS,
    FIELD_RULES,
    # subdomains
    FIELD_SUBDOMAIN,
    # suspicious_domains
    FIELD_REGISTRATION_DATE,
    FIELD_DETECTED_TECHNOLOGIES,
    FIELD_DNS_RECORDS,
    FIELD_FUZZER,
    FIELD_LAST_LIVE_CHECK,
    FIELD_RAW_REGISTRATION_DATE,
    FIELD_DETECTION_SERVICE,
    FIELD_WHOIS_ENRICHED,
    FIELD_WHOIS_ENRICHED_TRIES,
    # telegram_mentions
    FIELD_CHAT_TITLE,
    FIELD_CHAT_ID,
    FIELD_USER_ID,
    # web_applications
    FIELD_APP_ID,
    FIELD_FAVICON,
    FIELD_IS_BEHIND_WAF,
    FIELD_IS_CDN,
    FIELD_IS_VHOST,
    FIELD_PATH,
    # physical_threats
    FIELD_PIN_NAME,
    FIELD_CITY,
    FIELD_THREAT_TYPE,
    FIELD_ADDRESS,
    FIELD_BASE_SOURCE,
    FIELD_COMPANY_UUID,
    FIELD_LATITUDE,
    FIELD_LLM_SEVERITY_DESCRIPTION,
    FIELD_LOCATION_NAME,
    FIELD_LOCATION_TYPE,
    FIELD_LONGITUDE,
    FIELD_PIN_ID,
    FIELD_SOURCE_COUNT,
    FIELD_SOURCES,
    FIELD_STATE,
    # leaked_credentials
    FIELD_PASSWORD,
    # osint
    FIELD_UPLOADED_AT,
    FIELD_MENTION_DATE,
    FIELD_REACH,
    FIELD_STARRED,
    # malicious_ads
    FIELD_IP_DETAIL,
    FIELD_SPONSORED,
    FIELD_URLS,
    # bit_bucket
    FIELD_FINDINGS_COUNT,
    FIELD_DETECTOR_NAME,
    FIELD_VERIFIED,
    FIELD_RAW_SECRET,
    FIELD_REPOSITORY,
    FIELD_FILES,
    FIELD_COMMITS,
    FIELD_COMMIT_LINKS,
    FIELD_AUTHORS,
    FIELD_ROTATION_GUIDE,
    FIELD_FINDINGS,
    # docker (FIELD_OWNER / DEVELOPER_URL / ICON_URL / SOURCE_NAME /
    # SCRAP_TIME / LAST_UPDATED_AT / METADATA already imported above for postman)
    FIELD_DOWNLOADS,
    FIELD_STARS,
    FIELD_TRUSTED_CONTENT,
    FIELD_IMAGE_TAGS,
    # defacement_content / defacement_keyword
    FIELD_KEYWORDS,
    FIELD_MATCHED_KEYWORD,
    FIELD_WEBSITE_ADDED_ON,
    FIELD_WEBSITE_ID,
    FIELD_FREQUENCY,
    # discord
    FIELD_SERVER_NAME,
    FIELD_AUTHOR_ID,
    FIELD_AVATAR,
    FIELD_AUTHOR_DATA,
    FIELD_ATTACHMENTS,
    FIELD_EMBEDS,
    # iocs
    FIELD_IOC,
    FIELD_BEHAVIOUR_TAGS,
    FIELD_CONFIDENT_RATING,
    FIELD_HOSTING_IP,
    FIELD_IOC_ATTACK_NAME,
    FIELD_IOC_TYPE,
    FIELD_REFERENCE_LINK,
    FIELD_RISK_RATING,
    FIELD_SOURCE_NAME_ID,
    FIELD_UUID,
    # mobile_apps
    FIELD_APPLICATION_NAME,
    FIELD_MARKET_SOURCE,
    FIELD_INDEX,
    FIELD_APP_AVAILABILITY,
    FIELD_CAT_KEY,
    FIELD_DEEP_LINK,
    FIELD_EMAIL,
    FIELD_IDENTIFIED_AT,
    FIELD_MARKET_STATUS,
    FIELD_MARKET_UPDATE,
    FIELD_PACKAGE_NAME,
    FIELD_PRIVACY_POLICY,
    FIELD_RATINGS,
    FIELD_SCREENSHOTS,
    FIELD_SHORT_DESCRIPTION,
    FIELD_WEBSITE,
    FIELD_WHAT_IS_NEW,
    # news_feed
    FIELD_ARTICLE_NAME,
    FIELD_AI_SUMMARY,
    FIELD_COUNTRIES,
    FIELD_CVES,
    FIELD_INDUSTRIES,
    FIELD_IOC_DETAILS,
    FIELD_IOC_TYPES,
    FIELD_IOCS,
    FIELD_IS_NOTIFIED,
    FIELD_MALWARES,
    FIELD_MALWARES_NEW,
    FIELD_NEWS_FEED_TYPE,
    FIELD_POST_DATE,
    FIELD_POST_IMG,
    FIELD_POST_SOURCE,
    FIELD_REGIONS,
    FIELD_SOURCE_COUNTRIES,
    FIELD_TACTICS,
    FIELD_TARGET_COUNTRIES,
    FIELD_THREAT_ACTORS,
    FIELD_THREAT_ACTORS_NEW,
    FIELD_TTPS,
    # cyber_crime_forums
    FIELD_DISCUSSION_DATE,
    FIELD_DISCUSSION_BY,
    FIELD_TOPIC_NAME,
    FIELD_CATEGORY_ID,
    FIELD_DISCUSSION_ID,
    FIELD_JOINED_DATE,
    FIELD_LIKES,
    FIELD_NUMBER_OF_POSTS,
    FIELD_REPUTATION,
    FIELD_TOPIC_CREATED_BY,
    FIELD_TOPIC_ID,
    # stealer_logs
    FIELD_COMPROMISED_DATE,
    FIELD_MALWARE_FAMILY,
    FIELD_APPLICATION,
    FIELD_PASSWORD,
    FIELD_USER_HASH,
    FIELD_DOC_ID,
    FIELD_COUNTRY_NAME,
    FIELD_FILE_CREATED_DATE,
    FIELD_FILE_MODIFIED_DATE,
    FIELD_FILE_C_DATE,
    FIELD_FILE_M_DATE,
    FIELD_FILE_FULL_PATH,
    FIELD_FILE_SIZE,
    FIELD_FILE_TYPE,
    FIELD_PARENT_FOLDER_ID,
    FIELD_DOC_CREATED_ON,
    ALERT_NAME_TEMPLATE,
    TITLE_FIELD_BY_SERVICE,
    TITLE_FIELD_DEFAULT,
)

logger = logging.getLogger("CybleAlertMapper")


# ── Field-size caps ──────────────────────────────────────────────────────────
# SecOps enforces 25_000 chars per event field and 1_024 per registered
# custom field. We cap large free-text fields well under both ceilings so the
# field never gets truncated by SOAR itself (which would surprise the analyst).
# Google SecOps SOAR caps a Free Text custom field at 1,024 characters
# (per https://cloud.google.com/chronicle/docs/soar/admin-tasks/advanced/service-limits
# and the Custom Fields documentation). Cap below that ceiling so SOAR's
# first-observation auto-registration never rejects an alert payload, and
# so the analyst doesn't see a hard truncation mid-paragraph.
_LONG_TEXT_MAX        = 1_024   # llm_explanation, ai_summary, ssl detail, content, …
_REPO_DESC_MAX        = 500
_MATCH_FRAGMENT_MAX   = 1_024


# ── Helpers ──────────────────────────────────────────────────────────────────


def _safe_data_data(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Return raw['data']['data'] safely as a dict, or {} when absent/malformed."""
    outer = raw.get("data")
    if not isinstance(outer, dict):
        return {}
    inner = outer.get("data")
    return inner if isinstance(inner, dict) else {}


def _lookup_field(raw: Dict[str, Any], field: str) -> str:
    """
    Find `field` first at the top level of `raw`, then under `raw.data.data.*`,
    then `raw.data.*`. Returns the first non-empty stringified value, or "" if
    nothing is found. Used by both title resolution and (in future) other
    cross-location lookups.
    """
    v = raw.get(field)
    if v not in (None, ""):
        return str(v).strip()
    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    inner = outer.get("data") if isinstance(outer.get("data"), dict) else {}
    v = inner.get(field) if isinstance(inner, dict) else None
    if v not in (None, ""):
        return str(v).strip()
    v = outer.get(field) if isinstance(outer, dict) else None
    if v not in (None, ""):
        return str(v).strip()
    return ""


def _emit(fields: Dict[str, str], key: str, value: Any, max_len: Optional[int] = None) -> None:
    """
    Always set `key` in `fields`. Converts the value to a stringified form
    (empty string for None / missing), stringifies lists by joining with ", ",
    and applies an optional length cap.

    Why this exists: the integration's contract is that every defined custom
    field is present on every alert, even when the upstream payload omits it.
    This keeps the SOAR event-blade column layout consistent across services
    and across alerts within the same service. Callers should NEVER use
    `if value: fields[key] = value` — that pattern is what this helper exists
    to eliminate.
    """
    if value is None:
        out = ""
    elif isinstance(value, (list, tuple)):
        out = ", ".join(str(x).strip() for x in value if x not in (None, ""))
    elif isinstance(value, dict):
        # We don't want a custom-field cell containing serialized JSON by
        # default; the connector already emits the full record as
        # raw_alert_json. Use _emit_json explicitly for the rare cases where
        # a structured sub-tree should be carried as JSON (e.g. DNS records).
        out = ""
    else:
        # Strip leading/trailing whitespace — Cyble occasionally pads values
        # with newlines and spaces (most visibly on darkweb_marketplaces),
        # which renders badly in the SOAR UI. Internal whitespace is kept.
        out = str(value).strip()
    if max_len is not None and len(out) > max_len:
        out = out[:max_len]
    fields[key] = out


def _emit_json(fields: Dict[str, str], key: str, value: Any,
               max_len: int = 2_000) -> None:
    """
    Serialize a dict/list to compact JSON and write it as a Custom Field.

    Used for structured sub-trees that are too rich to flatten into individual
    fields (e.g. domain_watchlist's `new_dns_record` / `old_dns_record`). The
    JSON form lets playbooks parse the value with the standard SOAR JSON
    helpers; the analyst still gets a readable cell in the UI.

    Always emits — empty string when value is None or unserializable so the
    column is consistent across alerts.
    """
    if value is None or value == "":
        fields[key] = ""
        return
    try:
        out = json.dumps(value, separators=(",", ":"), default=str)
    except (TypeError, ValueError):
        fields[key] = ""
        return
    if len(out) > max_len:
        out = out[:max_len]
    fields[key] = out


# ── Common-field extractor (runs for every service) ──────────────────────────


def _extract_common_fields(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    Emit every entry in COMMON_FIELDS as a custom field — even when the raw
    alert is missing the key or its value is null. The output set is identical
    in shape on every alert, so SOAR-side custom-field registration only needs
    to happen once and every alert renders the same column layout.

    Special handling:
      - `tags` is rendered as a CSV string rather than a list.
      - `llm_explanation` is capped at _LONG_TEXT_MAX since it can be
        paragraph-length and would otherwise risk truncation by SOAR.
    """
    for field_key, source_key in COMMON_FIELDS:
        max_len = _LONG_TEXT_MAX if field_key == FIELD_LLM_EXPLANATION else None
        _emit(fields, field_key, raw.get(source_key), max_len=max_len)


# ── Per-service nested extractors ────────────────────────────────────────────
# These walk the nested subtree of a Cyble alert and copy useful fields into
# the SecOps custom-field dict. They are intentionally tolerant of missing /
# unexpected types: every key access goes through .get(), and structural
# checks (isinstance(..., dict)) guard nested lookups. ALL declared fields are
# emitted on every call — never short-circuited on falsy values — to satisfy
# the always-emit contract.


def _extract_assets(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    assets / Assets — asset-discovery records.

    The Cyble payload duplicates the asset value (top-level `asset` =
    `data.data.value`) and the detection time (top-level `last_detected_at`
    = `data.data.last_detected_at`). We pick the top-level copies — they're
    the canonical fields used by the rest of the Cyble UI — and only reach
    into `data.data` for `keyword_id`, which doesn't appear elsewhere.
    """
    dd = _safe_data_data(raw)
    _emit(fields, FIELD_ASSET,            raw.get("asset"))
    _emit(fields, FIELD_LAST_DETECTED_AT, raw.get("last_detected_at"))
    _emit(fields, FIELD_KEYWORD_ID,       dd.get("keyword_id"))


def _extract_cloud_storage(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    cloud_storage / Cloud Storage — public S3/GCS/Azure object discovery.

    Duplicates we deliberately skip:
      - data.data.bucket   ⇄ top-level `bucket`
      - data.data.filename ⇄ top-level `filename`

    The top-level `bucket` is a *cloud-storage* bucket (e.g.
    "uplead-images.s3.amazonaws.com") and is intentionally distinct from
    the common `Bucket` custom field, which carries Cyble's internal
    bucket-of-alerts label (`bucket_name`).
    """
    dd = _safe_data_data(raw)
    _emit(fields, FIELD_STORAGE_BUCKET,    raw.get("bucket"))
    _emit(fields, FIELD_FILENAME,          raw.get("filename"))
    _emit(fields, FIELD_STORAGE_BUCKET_ID, dd.get("bucketId"))
    _emit(fields, FIELD_STORAGE_OBJECT_ID, dd.get("id"))
    _emit(fields, FIELD_FILE_FULL_PATH,    dd.get("fullPath"))
    _emit(fields, FIELD_FILE_SIZE,         dd.get("size"))
    _emit(fields, FIELD_URL,               dd.get("url"))


def _extract_compromised_endpoints_cookies(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    compromised_endpoints_cookies / Compromised Cookies — leaked browser
    cookie records from a stealer log.

    Duplicates skipped:
      - data.content.URL    ⇄ top-level `url`
      - data.content.Expiry ⇄ top-level `expiry_date`
      - data.meta-data.file_name ⇄ data.filename
      - data.updated_at / data.updated_on ⇄ common UpdatedAt
    """
    _emit(fields, FIELD_URL,         raw.get("url"))
    _emit(fields, FIELD_EXPIRY_DATE, raw.get("expiry_date"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}

    content = outer.get("content") if isinstance(outer.get("content"), dict) else {}
    # Cyble uses literal "Cookie Data" with a space and capital letters here.
    _emit(fields, FIELD_COOKIE_DATA, content.get("Cookie Data"))

    _emit(fields, FIELD_FILENAME,         outer.get("filename"))
    _emit(fields, FIELD_DOC_CREATED_ON,   outer.get("created_on"))
    _emit(fields, FIELD_IS_UPDATED_ES,    outer.get("is_updated_es"))
    _emit(fields, FIELD_S3_KEY,           outer.get("s3_key"))
    _emit(fields, FIELD_SOURCE_ID,        outer.get("source_id"))
    _emit(fields, FIELD_MALWARE_FAMILY,   outer.get("ta"))
    _emit(fields, FIELD_PARENT_FOLDER_ID, outer.get("parent_folder_path_id"))

    # The Cyble payload uses "meta-data" (hyphenated) for this service, unlike
    # stealer_logs which uses "file_metadata". Same logical fields though.
    md = outer.get("meta-data") if isinstance(outer.get("meta-data"), dict) else {}
    _emit(fields, FIELD_FILE_C_DATE,    md.get("c_date"))
    _emit(fields, FIELD_FILE_M_DATE,    md.get("m_date"))
    _emit(fields, FIELD_FILE_FULL_PATH, md.get("file_path"))
    _emit(fields, FIELD_FILE_SIZE,      md.get("file_size"))


def _extract_compromised_files(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    compromised_files / Compromised Files — leaked file mentions from a
    stealer-log archive.

    Duplicates skipped:
      - data.compromised_on        ⇄ top-level `compromised_date`
      - data.meta_data.file_name   ⇄ top-level `filename`
    """
    _emit(fields, FIELD_FILENAME,         raw.get("filename"))
    _emit(fields, FIELD_EXTENSION,        raw.get("extension"))
    _emit(fields, FIELD_COMPROMISED_DATE, raw.get("compromised_date"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    _emit(fields, FIELD_CONTENT,          outer.get("content"), max_len=_LONG_TEXT_MAX)
    _emit(fields, FIELD_DOC_CREATED_ON,   outer.get("created_on"))
    _emit(fields, FIELD_DOC_ID,           outer.get("doc_id"))
    _emit(fields, FIELD_FILE_OBJ_PATH,    outer.get("file_obj_path"))
    _emit(fields, FIELD_LOG_NAME,         outer.get("log_name"))
    _emit(fields, FIELD_LOG_OBJ_PATH,     outer.get("log_obj_path"))
    _emit(fields, FIELD_PARENT_FOLDER_ID, outer.get("parent_folder_path_id"))
    _emit(fields, FIELD_RELATIVE_PATH,    outer.get("relative_path"))

    md = outer.get("meta_data") if isinstance(outer.get("meta_data"), dict) else {}
    _emit(fields, FIELD_FILE_C_DATE,    md.get("c_date"))
    _emit(fields, FIELD_FILE_M_DATE,    md.get("m_date"))
    _emit(fields, FIELD_FILE_FULL_PATH, md.get("file_path"))
    _emit(fields, FIELD_FILE_SIZE,      md.get("file_size"))


def _extract_cyble_research_labs(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    cyble_research_labs / Cyble Research Labs — analyst-authored research
    notes. Title + free-form details.

    Duplicates skipped:
      - data.title ⇄ top-level `title`
    """
    _emit(fields, FIELD_TITLE, raw.get("title"))
    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    _emit(fields, FIELD_DETAILS, outer.get("details"), max_len=_LONG_TEXT_MAX)


def _extract_advisory(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    advisory / Cyble Research Labs Advisory — internal advisory record.
    The payload occasionally returns `data.data` as a scalar (the advisory ID)
    rather than the usual nested dict — `_safe_data_data` discards scalars,
    so we reach into the structure directly here.
    """
    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    inner = outer.get("data") if isinstance(outer, dict) else None
    _emit(fields, FIELD_ADVISORY_ID, inner)


def _extract_darkweb_marketplaces(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    darkweb_marketplaces / Darkweb Marketplaces — listings of compromised
    accounts / cards / endpoints for sale on darkweb marketplaces.

    The payload often pads string values with leading/trailing whitespace
    (newlines, tab indentation). `_emit` strips outer whitespace so SOAR
    renders clean values.

    Duplicates skipped:
      - data.marketplace   ⇄ top-level `marketplace`
      - data.stealer       ⇄ top-level `stealer`  (we emit as `MalwareFamily`)
      - data.updated_date  ⇄ common UpdatedAt
    """
    _emit(fields, FIELD_MARKETPLACE,         raw.get("marketplace"))
    _emit(fields, FIELD_MALWARE_FAMILY,      raw.get("stealer"))
    _emit(fields, FIELD_CONTENT_UPDATED_ON,  raw.get("content_updated_on"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}

    # Top-level marketplace metadata
    _emit(fields, FIELD_VENDOR,              outer.get("vendor"))
    _emit(fields, FIELD_PRICE,               outer.get("price"))
    _emit(fields, FIELD_DATA_SIZE,           outer.get("size"))
    _emit(fields, FIELD_COUNTRY_NAME,        outer.get("country"))
    _emit(fields, FIELD_REGION,              outer.get("region"))
    _emit(fields, FIELD_INFO,                outer.get("info"))
    _emit(fields, FIELD_OUTLOOK,             outer.get("outlook"))
    _emit(fields, FIELD_BROWSER,             outer.get("browser"))
    _emit(fields, FIELD_OS,                  outer.get("os"))
    _emit(fields, FIELD_USER_AGENT,          outer.get("userAgent"))
    _emit(fields, FIELD_IP,                  outer.get("ip"))
    _emit(fields, FIELD_INSTALLED_DATE,      outer.get("installed_date"))
    _emit(fields, FIELD_COOKIES,             outer.get("cookies"), max_len=_LONG_TEXT_MAX)
    _emit(fields, FIELD_COOKIES_DATE,        outer.get("cookies_date"))
    _emit(fields, FIELD_COMPANY_LEAKED,      outer.get("company_leaked"))
    _emit(fields, FIELD_CONFIG_UPDATE,       outer.get("config_update"))
    _emit(fields, FIELD_DATA_STRUCT,         outer.get("data_struct"))
    _emit(fields, FIELD_LINKS,               outer.get("links"))
    _emit(fields, FIELD_EVENT_DATE,          outer.get("date"))
    _emit(fields, FIELD_EVENT_DATE_TIMESTAMP, outer.get("date_timestamp"))

    # Bank / card sub-tree (compromised payment data)
    bank = outer.get("bank") if isinstance(outer.get("bank"), dict) else {}
    _emit(fields, FIELD_BANK_BIN,       bank.get("bin"))
    _emit(fields, FIELD_BANK_COUNTRY,   bank.get("isocountry"))
    _emit(fields, FIELD_BANK_PHONE,     bank.get("phone"))
    _emit(fields, FIELD_BANK_REAL_NAME, bank.get("real_name"))
    _emit(fields, FIELD_BANK_REF_NAME,  bank.get("ref_name"))
    _emit(fields, FIELD_BANK_SITE,      bank.get("site"))

    card = bank.get("card") if isinstance(bank.get("card"), dict) else {}
    _emit(fields, FIELD_CARD_BRAND,  card.get("brand"))
    _emit(fields, FIELD_CARD_NUMBER, card.get("card_no"))
    _emit(fields, FIELD_CARD_TYPE,   card.get("card_type"))
    _emit(fields, FIELD_CARD_CVR,    card.get("cvr"))
    _emit(fields, FIELD_CARD_CVV,    card.get("cvv"))
    _emit(fields, FIELD_CARD_EXPIRY, card.get("expiry"))
    _emit(fields, FIELD_CARD_LEVEL,  card.get("level"))


def _extract_darkweb_data_breaches(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    darkweb_data_breaches / Data Exposures — bulk credential / data dumps.

    For this service Cyble returns `data.data` as a STRING (the credential
    blob), not the usual nested dict. We read it directly and cap to the
    long-text limit.

    Duplicates skipped:
      - data.date ⇄ top-level `breach_date`
    """
    _emit(fields, FIELD_BREACH_SOURCE, raw.get("breach_source"))
    _emit(fields, FIELD_BREACH_DATE,   raw.get("breach_date"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    _emit(fields, FIELD_CONTENT, outer.get("data"), max_len=_LONG_TEXT_MAX)
    _emit(fields, FIELD_S3_KEY,  outer.get("s3_key"))


def _extract_domain_expiry(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    domain_expiry / Domain Expiry — domain registration expiry monitoring.

    The Cyble payload occasionally leaves the top-level `domain` /
    `expiry_date` blank and only populates them under `data.*`. We pick the
    top-level copy first and fall back to the nested one, so a single Custom
    Field column carries the value regardless of which side Cyble fills.

    Duplicates skipped:
      - data.severity ⇄ common Severity
      - data.domain / data.expiry_date are the fallback source above, never a
        second column.
    """
    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    _emit(fields, FIELD_DOMAIN,         raw.get("domain") or outer.get("domain"))
    _emit(fields, FIELD_EXPIRY_DATE,    raw.get("expiry_date") or outer.get("expiry_date"))
    _emit(fields, FIELD_DAYS_TO_EXPIRY, outer.get("due_days"))
    # `type_text` is a human-readable summary ("Domain Expires in 7 days") —
    # reuse the generic Title column so analysts get it as the at-a-glance
    # label on the event blade.
    _emit(fields, FIELD_TITLE,          outer.get("type_text"))


def _extract_domain_watchlist(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    domain_watchlist / Domain Watchlist — DNS diff alerts. The interesting
    payload is two big DNS-record subtrees (`old_dns_record`, `new_dns_record`)
    plus a flat list of which record types changed.

    The DNS subtrees are too rich to flatten into individual fields without
    drowning the SOAR event blade in noise. We emit them as compact JSON
    blobs (capped at the long-text limit) so playbooks can parse them and
    analysts can inspect them inline.

    Duplicates skipped:
      - data.data.updated_fields ⇄ top-level `updated_fields`
    """
    _emit(fields, FIELD_UPDATED_FIELDS, raw.get("updated_fields"))

    dd = _safe_data_data(raw)
    _emit_json(fields, FIELD_NEW_DNS_RECORD, dd.get("new_dns_record"))
    _emit_json(fields, FIELD_OLD_DNS_RECORD, dd.get("old_dns_record"))

    ss = dd.get("screenshot_data") if isinstance(dd.get("screenshot_data"), dict) else {}
    _emit(fields, FIELD_SCREENSHOT_OBJECT_KEY, ss.get("object_key"))
    _emit(fields, FIELD_SCREENSHOT_TIMESTAMP,  ss.get("timestamp"))


def _extract_hacktivism(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    hacktivism / Hacktivism — defacement / leak claims posted by hacktivist
    groups on public mirror sites.

    Duplicates skipped:
      - data.domain      ⇄ data.website_url (same value, emit once as Url)
      - data.created_at  ⇄ common CreatedAt
      - data.updated_at  ⇄ common UpdatedAt
      - data.country_name ⇄ shared CountryName
      - data.type        ⇄ top-level `type`
    """
    _emit(fields, FIELD_CHANNEL_NAME,    raw.get("channel_name"))
    _emit(fields, FIELD_SOURCE,          raw.get("source"))
    _emit(fields, FIELD_TYPE,            raw.get("type"))
    _emit(fields, FIELD_CONTENT_ADDED_ON, raw.get("content_added_on"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    _emit(fields, FIELD_ATTACKER,        outer.get("attacker"))
    _emit(fields, FIELD_COUNTRY_CODE,    outer.get("country_code"))
    _emit(fields, FIELD_COUNTRY_NAME,    outer.get("country_name"))
    _emit(fields, FIELD_IP,              outer.get("ip"))
    _emit(fields, FIELD_MIRROR,          outer.get("mirror"))
    _emit(fields, FIELD_SERVER,          outer.get("server"))
    _emit(fields, FIELD_SOURCE_WEBSITE,  outer.get("source_website"))
    _emit(fields, FIELD_TEAM,            outer.get("team"))
    _emit(fields, FIELD_TIMESTAMP,       outer.get("timestamp"))
    _emit(fields, FIELD_UNIQUE_KEY,      outer.get("unique_key"))
    _emit(fields, FIELD_URL,             outer.get("website_url"))


def _extract_i2p(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    i2p / I2P Links — keyword mentions on I2P-hosted pages.

    Duplicates skipped:
      - data.i2p_url     ⇄ top-level `url`
      - data.id / data._id ⇄ same hash, emit once as DocId
      - data.updated_on  ⇄ top-level `content_updated_on`
    """
    _emit(fields, FIELD_URL,                raw.get("url"))
    _emit(fields, FIELD_CONTENT_UPDATED_ON, raw.get("content_updated_on"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    # _id and id are duplicates of each other; pick _id (Cyble's internal name)
    _emit(fields, FIELD_DOC_ID,         outer.get("_id") or outer.get("id"))
    _emit(fields, FIELD_CONTENT,        outer.get("data"), max_len=_LONG_TEXT_MAX)
    _emit(fields, FIELD_SEARCH_ENGINE,  outer.get("search_engine"))
    _emit(fields, FIELD_SEARCH_KEYWORD, outer.get("search_keyword"))


def _extract_ip_risk_score(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    ip_risk_score / IP Risk Score — flagged change in an IP's reputation score.

    Cyble also returns `data.data` as a 3-element list of [old, new, ip]; all
    three values are already exposed as top-level fields, so we read only
    the top-level ones to avoid duplicate emission.
    """
    _emit(fields, FIELD_OLD_RISK_SCORE, raw.get("old_risk_score"))
    _emit(fields, FIELD_NEW_RISK_SCORE, raw.get("new_risk_score"))
    _emit(fields, FIELD_IP,             raw.get("ip"))


def _extract_vulnerability(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    vulnerability / Issues Catalog — web-application security findings.

    Duplicates skipped:
      - data.data.host, data.data.ip, data.data.port, data.data.title,
        data.data.severity — all already on the top-level record.
    """
    _emit(fields, FIELD_TITLE, raw.get("title"))
    _emit(fields, FIELD_HOST,  raw.get("host"))
    _emit(fields, FIELD_PORT,  raw.get("port"))
    _emit(fields, FIELD_IP,    raw.get("ip"))

    dd = _safe_data_data(raw)
    _emit(fields, FIELD_CONFIDENCE,         dd.get("confidence"))
    _emit(fields, FIELD_FIRST_SEEN_ON,      dd.get("first_seen_on"))
    _emit(fields, FIELD_LAST_SEEN_ON,       dd.get("last_seen_on"))
    _emit(fields, FIELD_VULNERABILITY_ID,   dd.get("vulnerability_id"))
    _emit(fields, FIELD_VULNERABILITY_TYPE, dd.get("vulnerability_type"))


def _extract_new_vulnerability(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    new_vulnerability / Network Vulnerabilities - CVEs — a new CVE detected
    against a watched IP. Payload is sparse; `data.data` is a plain string
    (the CVE id), which duplicates the top-level `cve` so we skip it.
    """
    _emit(fields, FIELD_CVE, raw.get("cve"))


def _extract_new_port(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    new_port / New Ports — newly observed open port on a watched asset.

    The top-level fields (`ip`, `port`, `protocol`, `last_detected_at`)
    occasionally come back null while the canonical value is on
    `data.data.*`. We pick top-level first and fall back to the nested
    copy so a single Custom Field column always carries the value.

    Duplicates skipped:
      - data.data.{ip, port, protocol, last_detected_at} — fallback source,
        not a second column.
    """
    dd = _safe_data_data(raw)
    _emit(fields, FIELD_IP,               raw.get("ip")               or dd.get("ip"))
    _emit(fields, FIELD_PORT,             raw.get("port")             if raw.get("port") not in (None, "") else dd.get("port"))
    _emit(fields, FIELD_PROTOCOL,         raw.get("protocol")         or dd.get("protocol"))
    _emit(fields, FIELD_LAST_DETECTED_AT, raw.get("last_detected_at") or dd.get("last_detected_at"))
    _emit(fields, FIELD_TYPE,             dd.get("type"))


def _extract_flash_report(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    flash_report / News Flash — analyst-curated threat brief reference.
    `keyword_name` already carries the report headline, so service-specific
    extraction is limited to the report bookkeeping fields.
    """
    dd = _safe_data_data(raw)
    _emit(fields, FIELD_FOR_COMPANY, dd.get("for_company"))
    _emit(fields, FIELD_REPORT_ID,   dd.get("report_id"))


def _extract_ot_ics(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    ot_ics / OT-ICS — operational-technology / industrial control system
    network observations (Shodan-style enrichment).

    Duplicates skipped:
      - data.asn          ⇄ top-level `asn`
      - data.country_name ⇄ top-level `country`
      - data.industry     ⇄ top-level `industry`
      - data.src_ip       ⇄ top-level `source_ip`
    """
    _emit(fields, FIELD_ASN,              raw.get("asn"))
    _emit(fields, FIELD_COUNTRY_NAME,     raw.get("country"))
    _emit(fields, FIELD_SOURCE_IP,        raw.get("source_ip"))
    _emit(fields, FIELD_CONTENT_ADDED_ON, raw.get("content_added_on"))
    _emit(fields, FIELD_INDUSTRY,         raw.get("industry"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    _emit(fields, FIELD_COUNTRY_CODE,     outer.get("country_code"))
    _emit(fields, FIELD_DATA_TYPE,        outer.get("data_type"))
    _emit(fields, FIELD_DEST_PORT,        outer.get("dest_port"))
    _emit(fields, FIELD_IP_REPUTATION,    outer.get("ip_rep"))
    _emit(fields, FIELD_TIMESTAMP,        outer.get("timestamp"))


def _extract_pastebin(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    pastebin / Pastesite — keyword mention in a public paste.

    Top-level `url` is often null while the actual paste URL lives at
    `data.url`; we pick top-level first and fall back.

    Duplicates skipped:
      - data.author       ⇄ top-level `author`
      - data.pastebin_id  ⇄ data.id (same hash)
      - data.updated_on   ⇄ top-level `content_updated_on`
    """
    _emit(fields, FIELD_AUTHOR,             raw.get("author"))
    _emit(fields, FIELD_CONTENT_UPDATED_ON, raw.get("content_updated_on"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    _emit(fields, FIELD_URL,         raw.get("url") or outer.get("url"))
    _emit(fields, FIELD_CONTENT,     outer.get("content"), max_len=_LONG_TEXT_MAX)
    _emit(fields, FIELD_EVENT_DATE,  outer.get("date"))
    _emit(fields, FIELD_DOC_ID,      outer.get("id") or outer.get("pastebin_id"))
    _emit(fields, FIELD_PASTE_TYPE,  outer.get("paste_type"))
    _emit(fields, FIELD_DATA_SIZE,   outer.get("size"))
    _emit(fields, FIELD_SOURCE_ID,   outer.get("source_id"))
    _emit(fields, FIELD_SOURCE_NAME, outer.get("source_name"))
    _emit(fields, FIELD_VIEWS,       outer.get("views"))


def _extract_phishing(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    phishing / Phishing Monitoring — suspected phishing domain / page.

    Rich nested payload with takedown bookkeeping plus a watermarking sub-tree
    used by the brand-protection workflow. The watermarking dict is too
    structured to flatten cleanly, so we emit it as a compact JSON blob.

    Duplicates skipped:
      - data.domain_name ⇄ top-level `domain`
      - data.created_at  ⇄ common CreatedAt
      - data.updated_at  ⇄ common UpdatedAt
      - data.score       ⇄ top-level `risk_score` (already in common fields)
    """
    _emit(fields, FIELD_DOMAIN,             raw.get("domain"))
    _emit(fields, FIELD_CONTENT_UPDATED_ON, raw.get("content_updated_on"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    _emit(fields, FIELD_AWS_OBJECT_NAME,       outer.get("aws_object_name"))
    _emit(fields, FIELD_BRAND,                 outer.get("brand"))
    _emit(fields, FIELD_BRAND_INDUSTRY,        outer.get("brand_industry"))
    _emit(fields, FIELD_BRAND_WEBSITE,         outer.get("brand_website"))
    _emit(fields, FIELD_CONTENT_MATCH,         outer.get("content_match"))
    _emit(fields, FIELD_DETECTED_AT,           outer.get("detected_at"))
    _emit(fields, FIELD_DO_OBJECT_NAME,        outer.get("do_object_name"))
    _emit(fields, FIELD_DOMAIN_RANKING,        outer.get("domain_ranking"))
    _emit(fields, FIELD_HOST_NAME,             outer.get("host_name"))
    _emit(fields, FIELD_DOC_ID,                outer.get("id"))
    _emit(fields, FIELD_IS_DELETED,            outer.get("is_deleted"))
    _emit(fields, FIELD_IS_LIVE,               outer.get("is_live"))
    _emit(fields, FIELD_IS_TAKEDOWN,           outer.get("is_takedown"))
    _emit(fields, FIELD_LAST_LIVE_ON,          outer.get("last_live_on"))
    _emit(fields, FIELD_LOGO_MATCH,            outer.get("logo_match"))
    _emit(fields, FIELD_PHISHING_KEYWORD_NAME, outer.get("phishing_keyword_name"))
    _emit(fields, FIELD_PHISHING_STATUS,       outer.get("phishing_status"))
    _emit(fields, FIELD_SCREENSHOT_URL,        outer.get("screenshot_url"))
    _emit(fields, FIELD_SOURCE,                outer.get("source"))
    _emit(fields, FIELD_STATUS_CODE,           outer.get("status_code"))
    _emit_json(fields, FIELD_WATERMARKING_DATA, outer.get("watermarking_data"))


def _extract_product_vulnerability(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    product_vulnerability / Vulnerability Intelligence — newly-published CVE
    against a watched software product.

    The top-level `description` is typically null on this service; the rich
    description lives at `data.description`. We overwrite the common
    Description column with the nested value when present so analysts see
    the actual advisory text on the event blade.

    Duplicates skipped:
      - data.company   ⇄ top-level `company`
      - data.cve_id    ⇄ top-level `cve`
      - data.product   ⇄ top-level `product`
      - data.version   ⇄ top-level `version`
    """
    _emit(fields, FIELD_COMPANY, raw.get("company"))
    _emit(fields, FIELD_PRODUCT, raw.get("product"))
    _emit(fields, FIELD_VERSION, raw.get("version"))
    _emit(fields, FIELD_CVE,     raw.get("cve"))

    # NOTE: this service exposes its nested fields one level shallower than
    # most others — it's `data.<key>`, not `data.data.<key>` — so we read
    # directly from `raw["data"]` here.
    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}

    # Overwrite the (typically empty) common Description with the richer
    # nested description string when present.
    nested_desc = outer.get("description")
    if nested_desc:
        _emit(fields, FIELD_DESCRIPTION, nested_desc, max_len=_LONG_TEXT_MAX)

    _emit(fields, FIELD_TITLE,              outer.get("title"))
    _emit(fields, FIELD_DOC_ID,             outer.get("doc_id"))
    _emit(fields, FIELD_LAST_MODIFIED_DATE, outer.get("lastModifiedDate"))
    _emit(fields, FIELD_PUBLISHED_DATE,     outer.get("publishedDate"))
    _emit(fields, FIELD_UPDATED_FIELDS,     outer.get("updated_fields"))
    _emit_json(fields, FIELD_NEW_CVE_DETAILS,  outer.get("new_cve_details"))
    _emit_json(fields, FIELD_OLD_CVE_DETAILS,  outer.get("old_cve_details"))
    _emit_json(fields, FIELD_SEVERITY_DATA,    outer.get("severity_data"))
    _emit_json(fields, FIELD_SOFTWARE_DETAILS, outer.get("software_details"))


def _extract_ransomware_updates(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    ransomware_updates / Ransomware Updates — analyst-curated ransomware
    incident notifications.

    Duplicates skipped:
      - data.created_at / data.updated_at ⇄ common Created/UpdatedAt
    """
    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}

    _emit(fields, FIELD_ADDED_BY,         outer.get("added_by"))
    _emit(fields, FIELD_COUNTRY_NAME,     outer.get("country"))
    _emit(fields, FIELD_EVENT_DATE,       outer.get("date"))

    # Override common Description with nested when present (top-level desc
    # is null for this service; nested may carry the analyst note).
    nested_desc = outer.get("description")
    if nested_desc and str(nested_desc).strip():
        _emit(fields, FIELD_DESCRIPTION, nested_desc, max_len=_LONG_TEXT_MAX)

    _emit(fields, FIELD_THREAT_ACTOR,     outer.get("gang"))
    _emit(fields, FIELD_HASH,             outer.get("hash"))
    _emit(fields, FIELD_DOC_ID,           outer.get("id"))
    _emit(fields, FIELD_INDUSTRY,         outer.get("industry"))
    _emit(fields, FIELD_IS_PUBLISHED,     outer.get("is_published"))
    _emit(fields, FIELD_REGION,           outer.get("region"))
    _emit(fields, FIELD_SCREENSHOTS_PATH, outer.get("screenshots_path"))
    _emit(fields, FIELD_TA_LINK,          outer.get("ta_link"))
    _emit(fields, FIELD_TM_LINK,          outer.get("tm_link"))
    _emit(fields, FIELD_UPDATED_BY,       outer.get("updated_by"))
    _emit(fields, FIELD_VICTIM,           outer.get("victim"))
    _emit(fields, FIELD_URL,              outer.get("website"))


def _extract_darkweb_ransomware(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    darkweb_ransomware / Darkweb Ransomware — mentions of leaked company data
    on darkweb leak sites.

    Note the timestamps: `created_date` / `updated_date` here describe the
    DUMP file, not the alert; they're distinct from the common Created/UpdatedAt
    columns which track the alert lifecycle inside Cyble.

    Duplicates skipped:
      - data.file_name    ⇄ top-level `filename`
      - data.threat_actor ⇄ top-level `threat_actor`
      - data.updated_date ⇄ top-level `updated_date`
      - data.victim       ⇄ top-level `victim`
    """
    _emit(fields, FIELD_VICTIM,       raw.get("victim"))
    _emit(fields, FIELD_THREAT_ACTOR, raw.get("threat_actor"))
    _emit(fields, FIELD_FILENAME,     raw.get("filename"))
    _emit(fields, FIELD_UPDATED_DATE, raw.get("updated_date"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    _emit(fields, FIELD_COMPANY_LEAKED,        outer.get("company_leak"))
    _emit(fields, FIELD_CONTENT,               outer.get("content"), max_len=_LONG_TEXT_MAX)
    _emit(fields, FIELD_CREATED_DATE,          outer.get("created_date"))
    _emit(fields, FIELD_DOCUMENT_CREATED_YEAR, outer.get("document_created_year"))
    _emit(fields, FIELD_DOC_ID,                outer.get("id"))
    _emit(fields, FIELD_ORIGINAL_FILENAME,     outer.get("original_file_name"))


def _extract_social_media_monitoring(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    social_media_monitoring / Brand Mentions — references to the brand on
    public social media (LinkedIn, Twitter, etc.).

    This payload is the deepest nested one in the integration. The structure is:
      data.metadata.extras       ← post content, hashtags, mentions, URL
      data.metadata.extras.creator      ← author profile
      data.metadata.extras.extracts     ← parsed IOCs from post body
      data.tags / data.rules            ← classification metadata

    We hoist analyst-facing fields into named columns and emit anything
    structured (media, excerpts, location, rules) as compact JSON.

    Duplicates skipped:
      - data.category / data.sentiment / data.source / data.type ⇄ top-level
      - data.id ⇄ top-level `id`
      - extras.creator.name ⇄ top-level `name`
      - extras.title ⇄ top-level `title`
    """
    _emit(fields, FIELD_SOURCE,           raw.get("source"))
    _emit(fields, FIELD_CATEGORY,         raw.get("category"))
    _emit(fields, FIELD_SENTIMENT,        raw.get("sentiment"))
    _emit(fields, FIELD_NAME,             raw.get("name"))
    _emit(fields, FIELD_TITLE,            raw.get("title"))
    _emit(fields, FIELD_TYPE,             raw.get("type"))
    _emit(fields, FIELD_CONTENT_ADDED_ON, raw.get("content_added_on"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    _emit(fields, FIELD_CONFIDENCE,       outer.get("confidence"))
    _emit(fields, FIELD_CONFIDENCE_SCORE, outer.get("confidence_score"))
    _emit(fields, FIELD_FINDING_ID,       outer.get("finding_id"))
    _emit(fields, FIELD_LANGUAGE,         outer.get("language"))
    _emit_json(fields, FIELD_LOCATION,    outer.get("location"))
    _emit_json(fields, FIELD_RULES,       outer.get("rules"))
    _emit_json(fields, FIELD_TAGS,        outer.get("tags"))  # overrides common Tags
    _emit(fields, FIELD_WEIGHTAGE,        outer.get("weightage"))

    # ── data.metadata.extras ─────────────────────────────────────────────
    metadata = outer.get("metadata") if isinstance(outer.get("metadata"), dict) else {}
    extras = metadata.get("extras") if isinstance(metadata.get("extras"), dict) else {}

    _emit(fields, FIELD_CONTENT,    extras.get("content"), max_len=_LONG_TEXT_MAX)
    _emit(fields, FIELD_HASH,       extras.get("content_hash"))
    _emit(fields, FIELD_HASHTAGS,   extras.get("hashtags"))   # list → CSV
    _emit(fields, FIELD_MENTIONS,   extras.get("mentions"))   # list → CSV
    _emit(fields, FIELD_POSTED_AT,  extras.get("posted_at"))
    _emit(fields, FIELD_URL,        extras.get("url"))
    _emit_json(fields, FIELD_MEDIA,    extras.get("media"))
    _emit_json(fields, FIELD_EXCERPTS, extras.get("excerpts"))

    # ── extras.creator ───────────────────────────────────────────────────
    creator = extras.get("creator") if isinstance(extras.get("creator"), dict) else {}
    _emit(fields, FIELD_CREATOR_TYPE,   extras.get("creator_type"))
    _emit(fields, FIELD_CREATOR_URL,    creator.get("url"))
    _emit(fields, FIELD_USERNAME,       creator.get("username"))
    _emit(fields, FIELD_FOLLOWERS,      creator.get("followers"))
    _emit(fields, FIELD_FOLLOWING,      creator.get("following"))
    _emit(fields, FIELD_IS_VERIFIED,    creator.get("is_verified"))
    _emit(fields, FIELD_IS_PUBLIC,      creator.get("is_public"))
    # Override common Description with creator's bio when present (top-level
    # description is null for this service).
    creator_desc = creator.get("description")
    if creator_desc:
        _emit(fields, FIELD_DESCRIPTION, creator_desc, max_len=_LONG_TEXT_MAX)

    # ── extras.extracts (parsed IOCs from the post body) ─────────────────
    extracts = extras.get("extracts") if isinstance(extras.get("extracts"), dict) else {}
    _emit(fields, FIELD_EXTRACTED_DOMAINS,    extracts.get("domains"))
    _emit(fields, FIELD_EXTRACTED_URLS,       extracts.get("urls"))
    _emit(fields, FIELD_EXTRACTED_SUBDOMAINS, extracts.get("subdomains"))
    _emit(fields, FIELD_EXTRACTED_IPS,        extracts.get("ips"))
    _emit(fields, FIELD_SUSPICIOUS_URLS,      extracts.get("suspicious_urls"))


def _extract_subdomains(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    subdomains / Subdomains — newly discovered subdomain of a watched domain.
    `data.data` is a string scalar duplicating the top-level `subdomain`, so
    we only read the top-level value.
    """
    _emit(fields, FIELD_SUBDOMAIN, raw.get("subdomain"))


def _extract_suspicious_domains(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    suspicious_domains / Suspicious Domains — newly registered or typo-squatted
    domains that look like the watched brand.

    Duplicates skipped:
      - data.domain / data.domain_name ⇄ top-level `domain`
      - data.keyword                   ⇄ top-level `keyword_name`
      - data.created_at / data.updated_at ⇄ common Created/UpdatedAt
    """
    _emit(fields, FIELD_DOMAIN, raw.get("domain"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}

    # NOTE: Cyble uses SCREAMING_SNAKE_CASE for these two keys.
    _emit(fields, FIELD_REGISTRATION_DATE,    outer.get("REGISTRATIONDATE"))
    _emit(fields, FIELD_SOURCE,               outer.get("SOURCE"))

    _emit(fields, FIELD_DETECTED_TECHNOLOGIES, outer.get("detected_technologies"))
    _emit_json(fields, FIELD_DNS_RECORDS,     outer.get("dns_records"))
    _emit(fields, FIELD_FUZZER,               outer.get("fuzzer"))
    _emit(fields, FIELD_DOC_ID,               outer.get("id"))
    _emit(fields, FIELD_IS_LIVE,              outer.get("is_live"))
    _emit(fields, FIELD_LAST_LIVE_CHECK,      outer.get("last_live_check"))
    _emit(fields, FIELD_RAW_REGISTRATION_DATE, outer.get("raw_registration_date"))
    _emit(fields, FIELD_SCORE,                outer.get("score"))
    _emit(fields, FIELD_SCREENSHOT_URL,       outer.get("screenshot_url"))
    _emit(fields, FIELD_DETECTION_SERVICE,    outer.get("service"))
    _emit(fields, FIELD_STATUS_CODE,          outer.get("status_code"))
    _emit(fields, FIELD_WHOIS_ENRICHED,       outer.get("whois_enriched"))
    _emit(fields, FIELD_WHOIS_ENRICHED_TRIES, outer.get("whois_enriched_tries"))


def _extract_telegram_mentions(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    telegram_mentions / Telegram Channels — keyword mention in a Telegram
    chat / channel.

    Duplicates skipped:
      - data.chat_title ⇄ top-level `chat_title`
      - data.username   ⇄ top-level `username`
    """
    _emit(fields, FIELD_CHAT_TITLE,         raw.get("chat_title"))
    _emit(fields, FIELD_USERNAME,           raw.get("username"))
    _emit(fields, FIELD_CONTENT_UPDATED_ON, raw.get("content_updated_on"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    _emit(fields, FIELD_CHAT_ID,      outer.get("chat_id"))
    _emit(fields, FIELD_CREATED_DATE, outer.get("created_date"))
    _emit(fields, FIELD_DOC_ID,       outer.get("id"))
    _emit(fields, FIELD_MESSAGE,      outer.get("message"), max_len=_LONG_TEXT_MAX)
    _emit(fields, FIELD_UPDATED_DATE, outer.get("updated_date"))
    _emit(fields, FIELD_USER_ID,      outer.get("user_id"))


def _extract_tor_links(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    tor_links / Tor Links — keyword mention on a Tor-hosted (.onion) page.

    Duplicates skipped:
      - data.search_engine ⇄ top-level `search_engine`
      - data.updated_on    ⇄ common UpdatedAt
    """
    _emit(fields, FIELD_SEARCH_ENGINE,      raw.get("search_engine"))
    _emit(fields, FIELD_CONTENT_UPDATED_ON, raw.get("content_updated_on"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    _emit(fields, FIELD_CONTENT,        outer.get("data"), max_len=_LONG_TEXT_MAX)
    _emit(fields, FIELD_DOC_ID,         outer.get("id"))
    _emit(fields, FIELD_SEARCH_KEYWORD, outer.get("search_keyword"))
    _emit(fields, FIELD_URL,            outer.get("tor_url"))


def _extract_postman_nested(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    postman / Code Analysis - Postman — public Postman collection mentions.

    Postman uses a flatter nested shape than github: most service-specific
    fields live directly under `data.*` rather than `data.data.*`.

    Duplicates we deliberately skip (already covered by COMMON_FIELDS or
    extracted at top-level):
      - data.created_at   ⇄ common CreatedAt
      - data.updated_at   ⇄ common UpdatedAt
      - data.description  ⇄ common Description
      - data.keyword      ⇄ common Keyword
      - data.title        ⇄ top-level `title` (emitted as `Title` below)
      - data.last_updated_on  ⇄ data.last_updated_on_date (we prefer the
                                proper timestamp variant)

    Re-uses existing constants where the semantics match:
      - data.developed_by  → `Owner` (analyst views the publisher as owner)
      - data.url           → `Url`
    """
    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}

    # Top-level title (also used as the second half of the case header)
    _emit(fields, FIELD_TITLE,              raw.get("title"))

    # Publisher / location
    _emit(fields, FIELD_OWNER,              outer.get("developed_by"))
    _emit(fields, FIELD_DEVELOPER_URL,      outer.get("developed_by_url"))
    _emit(fields, FIELD_URL,                outer.get("url"))

    # Visibility & classification
    _emit(fields, FIELD_IS_PUBLIC,          outer.get("is_public"))
    _emit(fields, FIELD_CATEGORY,           outer.get("category"))

    # Engagement metrics
    _emit(fields, FIELD_VIEWS,              outer.get("views"))
    _emit(fields, FIELD_FORKS,              outer.get("forks"))
    _emit(fields, FIELD_WATCHERS,           outer.get("watchers"))

    # Volume / scope
    _emit(fields, FIELD_APIS_COUNT,         outer.get("apis"))
    _emit(fields, FIELD_COLLECTIONS_COUNT,  outer.get("collection"))
    _emit(fields, FIELD_WORKSPACES_COUNT,   outer.get("workspace"))

    # Provenance & misc
    _emit(fields, FIELD_ICON_URL,           outer.get("image_icon_url"))
    _emit(fields, FIELD_POSTMAN_KEY,        outer.get("postman_unique_key"))
    _emit(fields, FIELD_SOURCE_NAME,        outer.get("source_name"))
    _emit(fields, FIELD_SCRAP_TIME,         outer.get("scrapping_time"))
    _emit(fields, FIELD_METADATA,           outer.get("meta_data"))
    # Prefer the parsed timestamp; fall back to the display string when Cyble
    # populates only one of the two variants.
    _emit(fields, FIELD_LAST_UPDATED_AT,
          outer.get("last_updated_on_date") or outer.get("last_updated_on"))


def _extract_ssl_expiry(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """ssl_expiry / Asset SSL Expiry — top-level + data.data.*."""
    dd = _safe_data_data(raw)
    _emit(fields, FIELD_ASSET,          raw.get("asset") or dd.get("asset"))
    _emit(fields, FIELD_EXPIRY_DATE,    raw.get("expiry_date") or dd.get("expiry"))
    _emit(fields, FIELD_DAYS_TO_EXPIRY, dd.get("days"))
    _emit(fields, FIELD_SSL_PORT,       dd.get("port"))
    _emit(fields, FIELD_SSL_IS_VALID,   dd.get("is_valid"))
    _emit(fields, FIELD_SSL_ISSUED,     dd.get("issued"))
    _emit(fields, FIELD_SSL_HASH,       dd.get("hash"))
    _emit(fields, FIELD_SSL_AGE_DAYS,   dd.get("age"))
    _emit(fields, FIELD_SSL_DETAIL,     dd.get("detail"), max_len=_LONG_TEXT_MAX)
    _emit(fields, FIELD_SSL_VERSION,    dd.get("version"))
    _emit(fields, FIELD_SSL_TITLE,      dd.get("title"))
    _emit(fields, FIELD_COUNTRY_CODE,   dd.get("country_code"))


def _extract_web_applications(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    web_applications / Web Application Discovery — newly observed web app
    fingerprint on a watched asset.

    Duplicates skipped:
      - data.data.{host,ip,port,title,severity} ⇄ top-level
    """
    _emit(fields, FIELD_TITLE, raw.get("title"))
    _emit(fields, FIELD_HOST,  raw.get("host"))
    _emit(fields, FIELD_PORT,  raw.get("port"))
    _emit(fields, FIELD_IP,    raw.get("ip"))

    dd = _safe_data_data(raw)
    _emit(fields, FIELD_APP_ID,        dd.get("app_id"))
    _emit(fields, FIELD_CONFIDENCE,    dd.get("confidence"))
    _emit(fields, FIELD_FAVICON,       dd.get("favicon"))
    _emit(fields, FIELD_FIRST_SEEN_ON, dd.get("first_seen_on"))
    _emit(fields, FIELD_IS_BEHIND_WAF, dd.get("is_behind_waf"))
    _emit(fields, FIELD_IS_CDN,        dd.get("is_cdn"))
    _emit(fields, FIELD_IS_VHOST,      dd.get("is_vhost"))
    _emit(fields, FIELD_LAST_SEEN_ON,  dd.get("last_seen_on"))
    _emit(fields, FIELD_PATH,          dd.get("path"))
    _emit(fields, FIELD_URL,           dd.get("url"))


def _extract_physical_threats(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    physical_threats / Physical Threats — geolocated real-world incidents
    (geopolitical, natural disaster, civil unrest) near a watched asset.

    Duplicates skipped:
      - data.data.city / threat_type / title / severity ⇄ top-level
      - data.data.pin_name / pin_string ⇄ top-level pin_name
      - data.data.company_id ⇄ common CompanyId
    """
    _emit(fields, FIELD_PIN_NAME,    raw.get("pin_name"))
    _emit(fields, FIELD_CITY,        raw.get("city"))
    _emit(fields, FIELD_TITLE,       raw.get("title"))
    _emit(fields, FIELD_THREAT_TYPE, raw.get("threat_type"))

    dd = _safe_data_data(raw)
    _emit(fields, FIELD_ADDRESS,                  dd.get("address"))
    _emit_json(fields, FIELD_BASE_SOURCE,         dd.get("base_source"))
    _emit(fields, FIELD_COMPANY_UUID,             dd.get("company_uuid"))
    _emit(fields, FIELD_COUNTRY_NAME,             dd.get("country"))

    nested_desc = dd.get("description")
    if nested_desc:
        _emit(fields, FIELD_DESCRIPTION, nested_desc, max_len=_LONG_TEXT_MAX)

    _emit(fields, FIELD_DOC_ID,                   dd.get("id"))
    _emit(fields, FIELD_LATITUDE,                 dd.get("latitude"))
    _emit(fields, FIELD_LLM_SEVERITY_DESCRIPTION, dd.get("llm_severity_description"),
          max_len=_LONG_TEXT_MAX)
    _emit(fields, FIELD_LOCATION_NAME,            dd.get("location_name"))
    _emit(fields, FIELD_LOCATION_TYPE,            dd.get("location_type"))
    _emit(fields, FIELD_LONGITUDE,                dd.get("longitude"))
    _emit(fields, FIELD_PIN_ID,                   dd.get("pin_id"))
    _emit(fields, FIELD_PUBLISHED_DATE,           dd.get("published_at"))
    _emit(fields, FIELD_REGION,                   dd.get("region"))
    _emit(fields, FIELD_SOURCE_COUNT,             dd.get("source_count"))
    _emit_json(fields, FIELD_SOURCES,             dd.get("sources"))
    _emit(fields, FIELD_STATE,                    dd.get("state"))


def _extract_leaked_credentials(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    leaked_credentials / Leaked Credentials — credentials harvested from
    breach dumps and combolists.

    Duplicates skipped:
      - data.username / data.domain ⇄ top-level
      - data.date ⇄ top-level `breach_date`
    """
    _emit(fields, FIELD_USERNAME,      raw.get("username"))
    _emit(fields, FIELD_DOMAIN,        raw.get("domain"))
    _emit(fields, FIELD_BREACH_SOURCE, raw.get("breach_source"))
    _emit(fields, FIELD_BREACH_DATE,   raw.get("breach_date"))
    _emit(fields, FIELD_HASH,          raw.get("unique_content_hash"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    # `data.data` here is the raw `url:username:password` combolist row.
    _emit(fields, FIELD_CONTENT,  outer.get("data"), max_len=_LONG_TEXT_MAX)
    _emit(fields, FIELD_PASSWORD, outer.get("password"))
    _emit(fields, FIELD_S3_KEY,   outer.get("s3_key"))
    _emit(fields, FIELD_URL,      outer.get("url"))


def _extract_osint(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    osint / OSINT — generic open-source-intelligence brand mention.

    Cyble uses Title Case keys with spaces under `data.*` for this service
    (e.g. `"Author Name"`, `"Mention Date"`, `"Mention URL"`). We read them
    with their literal names — no string normalisation.

    Duplicates skipped:
      - data.created_at / data.updated_on ⇄ common Created/UpdatedAt
      - data["Author Name"]  ⇄ top-level `author_name`
      - data["Author Username"] ⇄ top-level `author_username`
      - data.Source ⇄ top-level `source`
    """
    _emit(fields, FIELD_NAME,        raw.get("author_name"))
    _emit(fields, FIELD_USERNAME,    raw.get("author_username"))
    _emit(fields, FIELD_SOURCE,      raw.get("source"))
    _emit(fields, FIELD_UPLOADED_AT, raw.get("uploaded_at"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    _emit(fields, FIELD_MENTION_DATE, outer.get("Mention Date"))
    _emit(fields, FIELD_URL,          outer.get("Mention URL"))
    _emit(fields, FIELD_CONTENT,      outer.get("Post Snippet"), max_len=_LONG_TEXT_MAX)
    _emit(fields, FIELD_REACH,        outer.get("Reach"))
    _emit(fields, FIELD_STARRED,      outer.get("Starred"))
    _emit(fields, FIELD_TITLE,        outer.get("Title"))


def _extract_malicious_ads(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    malicious_ads / Malicious Ads — phishing-style ads detected by URLScan.

    The nested structure mirrors `phishing` almost exactly; we reuse the same
    column names so the SOAR table is consistent across both services. Adds
    a few ads-specific fields (`IpDetail`, `Sponsored`, `Urls`).

    Duplicates skipped:
      - data.domain_name ⇄ top-level `domain`
      - data.created_at / data.updated_at ⇄ common Created/UpdatedAt
    """
    _emit(fields, FIELD_DOMAIN,             raw.get("domain"))
    _emit(fields, FIELD_CONTENT_UPDATED_ON, raw.get("content_updated_on"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    _emit(fields, FIELD_IP_DETAIL,             outer.get("IPDetail"))
    _emit(fields, FIELD_SPONSORED,             outer.get("Sponsored"))
    _emit(fields, FIELD_AWS_OBJECT_NAME,       outer.get("aws_object_name"))
    _emit(fields, FIELD_BRAND,                 outer.get("brand"))
    _emit(fields, FIELD_BRAND_INDUSTRY,        outer.get("brand_industry"))
    _emit(fields, FIELD_BRAND_WEBSITE,         outer.get("brand_website"))
    _emit(fields, FIELD_CONTENT_MATCH,         outer.get("content_match"))
    _emit(fields, FIELD_DETECTED_AT,           outer.get("detected_at"))
    _emit(fields, FIELD_DO_OBJECT_NAME,        outer.get("do_object_name"))
    _emit(fields, FIELD_DOMAIN_RANKING,        outer.get("domain_ranking"))
    _emit(fields, FIELD_HOST_NAME,             outer.get("host_name"))
    _emit(fields, FIELD_DOC_ID,                outer.get("id"))
    _emit(fields, FIELD_IS_DELETED,            outer.get("is_deleted"))
    _emit(fields, FIELD_IS_LIVE,               outer.get("is_live"))
    _emit(fields, FIELD_IS_TAKEDOWN,           outer.get("is_takedown"))
    _emit(fields, FIELD_LAST_LIVE_ON,          outer.get("last_live_on"))
    _emit(fields, FIELD_LOGO_MATCH,            outer.get("logo_match"))
    _emit(fields, FIELD_PHISHING_KEYWORD_NAME, outer.get("phishing_keyword_name"))
    _emit(fields, FIELD_PHISHING_STATUS,       outer.get("phishing_status"))
    _emit(fields, FIELD_SCORE,                 outer.get("score"))
    _emit(fields, FIELD_SCREENSHOT_URL,        outer.get("screenshot_url"))
    _emit(fields, FIELD_SOURCE,                outer.get("source"))
    _emit(fields, FIELD_STATUS_CODE,           outer.get("status_code"))
    _emit(fields, FIELD_TITLE,                 outer.get("title"))
    _emit(fields, FIELD_URLS,                  outer.get("urls"))


def _extract_bit_bucket(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    bit_bucket / Code Analysis - BitBucket — trufflehog secret-scan findings.

    Cyble returns `data.data` as a LIST of detection objects (one per leaked
    secret, often duplicated across commits). We summarise the list:
      - Scalar fields (DetectorName, Verified, RawSecret, Repository) are
        taken from the FIRST finding — same secret typically appears in
        every entry, just on different commits.
      - List fields (Files, Commits, CommitLinks, Authors) are deduplicated
        and joined as CSVs so analysts get every commit at a glance.
      - FindingsCount tracks total list length.
      - Findings carries the full list as compact JSON for playbook drill-down.
    """
    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    items = outer.get("data") if isinstance(outer.get("data"), list) else []

    _emit(fields, FIELD_FINDINGS_COUNT, len(items))

    first = items[0] if items else {}
    if not isinstance(first, dict):
        first = {}
    extra = first.get("ExtraData") if isinstance(first.get("ExtraData"), dict) else {}
    src_meta = first.get("SourceMetadata") if isinstance(first.get("SourceMetadata"), dict) else {}
    src_data = src_meta.get("Data") if isinstance(src_meta.get("Data"), dict) else {}
    bitbucket = src_data.get("Bitbucket") if isinstance(src_data.get("Bitbucket"), dict) else {}

    _emit(fields, FIELD_DETECTOR_NAME,  first.get("DetectorName"))
    _emit(fields, FIELD_VERIFIED,       first.get("Verified"))
    _emit(fields, FIELD_RAW_SECRET,     first.get("Raw"), max_len=_LONG_TEXT_MAX)
    _emit(fields, FIELD_SOURCE_NAME,    first.get("SourceName"))
    _emit(fields, FIELD_ROTATION_GUIDE, extra.get("rotation_guide"))
    _emit(fields, FIELD_REPOSITORY,     bitbucket.get("repository"))

    # Deduplicate per-commit values across all findings
    def _uniq(seq):
        seen, out = set(), []
        for v in seq:
            if v and v not in seen:
                seen.add(v)
                out.append(v)
        return out

    files, commits, links, authors = [], [], [], []
    for item in items:
        if not isinstance(item, dict):
            continue
        bb = (((item.get("SourceMetadata") or {}).get("Data") or {}).get("Bitbucket") or {})
        if not isinstance(bb, dict):
            continue
        files.append(bb.get("file"))
        commits.append(bb.get("commit"))
        links.append(bb.get("link"))
        authors.append(bb.get("email"))

    _emit(fields, FIELD_FILES,        _uniq(files))
    _emit(fields, FIELD_COMMITS,      _uniq(commits))
    _emit(fields, FIELD_COMMIT_LINKS, _uniq(links))
    _emit(fields, FIELD_AUTHORS,      _uniq(authors))
    _emit_json(fields, FIELD_FINDINGS, items)


def _extract_docker_nested(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    docker / Code Analysis - Docker Hub — public Docker image mentions.

    Mostly mirrors the postman extractor (same shape of public-marketplace
    metadata) with image-specific additions (`Downloads`, `Stars`,
    `TrustedContent`, `ImageTags`).

    Duplicates skipped:
      - data.title ⇄ top-level `title`
      - data.keyword ⇄ top-level `keyword_name`
      - data.created_at / updated_at ⇄ common
      - data.last_updated_on_date ⇄ data.last_updated_on (same value,
        different formatting)
    """
    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}

    nested_desc = outer.get("description")
    if nested_desc:
        _emit(fields, FIELD_DESCRIPTION, nested_desc, max_len=_LONG_TEXT_MAX)

    _emit(fields, FIELD_OWNER,           outer.get("developed_by"))
    _emit(fields, FIELD_DEVELOPER_URL,   outer.get("developed_by_url"))
    _emit(fields, FIELD_UNIQUE_KEY,      outer.get("docker_unique_key"))
    _emit(fields, FIELD_DOWNLOADS,       outer.get("downloads"))
    _emit(fields, FIELD_ICON_URL,        outer.get("image_icon_url"))
    _emit(fields, FIELD_LAST_UPDATED_AT, outer.get("last_updated_on"))
    _emit(fields, FIELD_METADATA,        outer.get("meta_data"))
    _emit(fields, FIELD_SCRAP_TIME,      outer.get("scrapping_time"))
    _emit(fields, FIELD_SOURCE_NAME,     outer.get("source_name"))
    _emit(fields, FIELD_STARS,           outer.get("stars"))
    _emit(fields, FIELD_IMAGE_TAGS,      outer.get("tags"))
    _emit(fields, FIELD_TRUSTED_CONTENT, outer.get("trusted_content"))
    _emit(fields, FIELD_URL,             outer.get("url"))


def _extract_defacement_content(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    defacement_content / Defacement Content — page content match on a
    monitored website.

    Duplicates skipped:
      - data.data.url         ⇄ top-level `url`
      - data.data.company_id  ⇄ common CompanyId
    """
    _emit(fields, FIELD_URL, raw.get("url"))

    dd = _safe_data_data(raw)
    _emit(fields, FIELD_DOC_CREATED_ON,    dd.get("created_on"))
    _emit(fields, FIELD_DOMAIN,            dd.get("domain_name"))
    _emit(fields, FIELD_DOC_ID,            dd.get("id"))
    _emit(fields, FIELD_KEYWORDS,          dd.get("keywords"))
    _emit(fields, FIELD_WEBSITE_ADDED_ON,  dd.get("website_added_on"))
    _emit(fields, FIELD_WEBSITE_ID,        dd.get("website_id"))


def _extract_defacement_keyword(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    defacement_keyword / Defacement Keyword — keyword match on a
    monitored website.

    `data.data.keyword` (singular) is the matched keyword string, which
    typically differs from the top-level `keyword_name` (the configured
    watch entry). We emit it as `MatchedKeyword` to avoid colliding with
    the common `Keyword` column.

    Duplicates skipped:
      - data.data.url         ⇄ top-level `url`
      - data.data.company_id  ⇄ common CompanyId
    """
    _emit(fields, FIELD_URL, raw.get("url"))

    dd = _safe_data_data(raw)
    _emit(fields, FIELD_DOC_CREATED_ON,    dd.get("created_on"))
    _emit(fields, FIELD_DOMAIN,            dd.get("domain_name"))
    _emit(fields, FIELD_FREQUENCY,         dd.get("frequency"))
    _emit(fields, FIELD_DOC_ID,            dd.get("id"))
    _emit(fields, FIELD_MATCHED_KEYWORD,   dd.get("keyword"))
    _emit(fields, FIELD_KEYWORDS,          dd.get("keywords"))
    _emit(fields, FIELD_WEBSITE_ADDED_ON,  dd.get("website_added_on"))
    _emit(fields, FIELD_WEBSITE_ID,        dd.get("website_id"))


def _extract_defacement_url(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    defacement_url / Defacement URL — defacement detected on a watched URL.

    The nested `data.data.description` is the actual defaced URL (more useful
    than the top-level `description` which is always null for this service),
    so we override the common Description with it. The top-level `type`
    duplicates `data.data.type`; the top-level wins and we skip the nested copy.

    Duplicates skipped:
      - data.data.company_id ⇄ common CompanyId
      - data.data.type       ⇄ top-level `type` (already covered by common)
    """
    _emit(fields, FIELD_TYPE, raw.get("type"))

    dd = _safe_data_data(raw)
    _emit(fields, FIELD_DOC_CREATED_ON,    dd.get("created_on"))
    if dd.get("description") not in (None, ""):
        _emit(fields, FIELD_DESCRIPTION, dd.get("description"))
    _emit(fields, FIELD_DOMAIN,            dd.get("domain_name"))
    _emit(fields, FIELD_DOC_ID,            dd.get("id"))
    _emit(fields, FIELD_KEYWORDS,          dd.get("keywords"))
    _emit(fields, FIELD_WEBSITE_ADDED_ON,  dd.get("website_added_on"))
    _emit(fields, FIELD_WEBSITE_ID,        dd.get("website_id"))


def _extract_discord(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    discord / Discord — Discord message mention.

    The author sub-tree carries ~15 fields; we hoist the four most useful
    (global_name → Name, username → Username, id → AuthorId, avatar →
    Avatar) and emit the complete sub-tree as compact JSON under
    `AuthorData` so playbooks can drill into the rest.

    Duplicates skipped:
      - data._id              ⇄ data.doc.id (DocId)
      - data.doc.channel_name ⇄ top-level `channel_name`
      - data.doc.server_name  ⇄ top-level `server_name`
    """
    _emit(fields, FIELD_CHANNEL_NAME,        raw.get("channel_name"))
    _emit(fields, FIELD_SERVER_NAME,         raw.get("server_name"))
    _emit(fields, FIELD_CONTENT_UPDATED_ON,  raw.get("content_updated_on"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    doc = outer.get("doc") if isinstance(outer.get("doc"), dict) else {}

    _emit(fields, FIELD_CONTENT,   doc.get("content"), max_len=_LONG_TEXT_MAX)
    _emit(fields, FIELD_DOC_ID,    doc.get("id"))
    _emit(fields, FIELD_TIMESTAMP, doc.get("timestamp"))

    author = doc.get("author") if isinstance(doc.get("author"), dict) else {}
    _emit(fields, FIELD_NAME,      author.get("global_name"))
    _emit(fields, FIELD_USERNAME,  author.get("username"))
    _emit(fields, FIELD_AUTHOR_ID, author.get("id"))
    _emit(fields, FIELD_AVATAR,    author.get("avatar"))
    _emit_json(fields, FIELD_AUTHOR_DATA,  author)

    _emit_json(fields, FIELD_ATTACHMENTS, doc.get("attachments"))
    _emit_json(fields, FIELD_EMBEDS,      doc.get("embeds"))


def _extract_iocs(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    iocs / IoCs — atomic indicators of compromise (IP, hash, URL, …).

    `data.description` overrides the (always-null on this service) top-level
    description when populated. `behaviour_tags` is a comma-separated string
    from Cyble; we pass it through verbatim rather than splitting since the
    semantics ("Bruteforce,Http,Malware,…") are already analyst-readable.

    Duplicates skipped:
      - data.ioc        ⇄ top-level `ioc`
      - data.first_seen ⇄ top-level `first_seen_on`
      - data.last_seen  ⇄ top-level `last_seen_on`
      - data.created_at / data.updated_at ⇄ common CreatedAt / UpdatedAt
    """
    _emit(fields, FIELD_IOC,             raw.get("ioc"))
    _emit(fields, FIELD_FIRST_SEEN_ON,   raw.get("first_seen_on"))
    _emit(fields, FIELD_LAST_SEEN_ON,    raw.get("last_seen_on"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    _emit(fields, FIELD_BEHAVIOUR_TAGS,    outer.get("behaviour_tags"))
    _emit(fields, FIELD_CONFIDENT_RATING,  outer.get("confident_rating"))
    if outer.get("description") not in (None, ""):
        _emit(fields, FIELD_DESCRIPTION, outer.get("description"))
    _emit(fields, FIELD_HOSTING_IP,        outer.get("hosting_ip"))
    _emit(fields, FIELD_IOC_ATTACK_NAME,   outer.get("ioc_attack_name"))
    _emit(fields, FIELD_IOC_TYPE,          outer.get("ioc_type"))
    _emit(fields, FIELD_REFERENCE_LINK,    outer.get("reference_link"))
    _emit(fields, FIELD_RISK_RATING,       outer.get("risk_rating"))
    _emit(fields, FIELD_SOURCE_NAME_ID,    outer.get("source_name_id"))
    _emit(fields, FIELD_UUID,              outer.get("uuid"))


def _extract_mobile_apps(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    mobile_apps / Mobile Apps — third-party Android/iOS app store record.

    The interesting payload lives under `data._source` (Elasticsearch-style
    wrapper). The four `ratings_1`/`_3`/`_4`/`_5` star-count buckets are
    JSON-encoded together as `Ratings` since they're rarely all populated
    and an analyst usually wants the whole distribution at a glance.

    Duplicates skipped:
      - data._source.market_source ⇄ top-level `market_source`
      - data._type / data.highlight (Elasticsearch internals)
      - data._source.icon_72       (sub-variation of `icon`)
      - data._source.search        (internal search blob)
    """
    _emit(fields, FIELD_APPLICATION_NAME, raw.get("application_name"))
    _emit(fields, FIELD_MARKET_SOURCE,    raw.get("market_source"))
    _emit(fields, FIELD_UPLOADED_AT,      raw.get("uploaded_at"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    _emit(fields, FIELD_DOC_ID, outer.get("_id"))
    _emit(fields, FIELD_INDEX,  outer.get("_index"))
    _emit(fields, FIELD_SCORE,  outer.get("_score"))

    src = outer.get("_source") if isinstance(outer.get("_source"), dict) else {}
    _emit_json(fields, FIELD_APP_AVAILABILITY, src.get("app_availability"))
    _emit(fields, FIELD_CAT_KEY,           src.get("cat_key"))
    _emit(fields, FIELD_CREATED_DATE,      src.get("created"))
    _emit(fields, FIELD_DEEP_LINK,         src.get("deep_link"))
    if src.get("description") not in (None, ""):
        _emit(fields, FIELD_DESCRIPTION, src.get("description"), max_len=_LONG_TEXT_MAX)
    _emit(fields, FIELD_OWNER,             src.get("developer"))
    _emit(fields, FIELD_DOWNLOADS,         src.get("downloads"))
    _emit(fields, FIELD_EMAIL,             src.get("email"))
    _emit(fields, FIELD_ICON_URL,          src.get("icon"))
    _emit(fields, FIELD_IDENTIFIED_AT,     src.get("identified_at"))
    _emit(fields, FIELD_MARKET_STATUS,     src.get("market_status"))
    _emit(fields, FIELD_MARKET_UPDATE,     src.get("market_update"))
    _emit(fields, FIELD_URL,               src.get("market_url"))
    _emit(fields, FIELD_PACKAGE_NAME,      src.get("package_name"))
    _emit(fields, FIELD_ADDRESS,           src.get("physical_address"))
    _emit(fields, FIELD_PRIVACY_POLICY,    src.get("privacy_policy"))
    ratings = {
        "ratings_1": src.get("ratings_1"),
        "ratings_3": src.get("ratings_3"),
        "ratings_4": src.get("ratings_4"),
        "ratings_5": src.get("ratings_5"),
    }
    _emit_json(fields, FIELD_RATINGS, ratings)
    _emit(fields, FIELD_SCREENSHOTS,       src.get("screenshots"))
    _emit(fields, FIELD_SHORT_DESCRIPTION, src.get("short_desc"))
    _emit(fields, FIELD_TITLE,             src.get("title"))
    _emit(fields, FIELD_VERSION,           src.get("version"))
    _emit(fields, FIELD_WEBSITE,           src.get("website"))
    _emit(fields, FIELD_WHAT_IS_NEW,       src.get("what_is_new"), max_len=_LONG_TEXT_MAX)


def _extract_news_feed(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    news_feed / Cyber Newsfeed — curated cybersecurity-news article mention.

    The article body is captured both as a short marketing-style
    `post_description` (overrides the always-null top-level description) and
    as a longer LLM-generated `ai_summary`. Every TTP/IOC/actor list is
    emitted as a CSV; the nested `ioc_details` and `post_source` objects are
    serialized as JSON so the analyst can drill in without losing structure.

    Duplicates skipped:
      - data.created_at / data.updated_at ⇄ common CreatedAt / UpdatedAt
      - data.tags overrides the always-empty top-level `tags` for this service.
    """
    _emit(fields, FIELD_ARTICLE_NAME, raw.get("article_name"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    _emit(fields, FIELD_DOC_ID,            outer.get("_id"))
    _emit(fields, FIELD_AI_SUMMARY,        outer.get("ai_summary"), max_len=_LONG_TEXT_MAX)
    _emit(fields, FIELD_COUNTRIES,         outer.get("countries"))
    _emit(fields, FIELD_CVES,              outer.get("cves"))
    _emit(fields, FIELD_INDUSTRIES,        outer.get("industries"))
    _emit_json(fields, FIELD_IOC_DETAILS,  outer.get("ioc_details"))
    _emit(fields, FIELD_IOC_TYPES,         outer.get("ioc_types"))
    _emit(fields, FIELD_IOCS,              outer.get("iocs"))
    _emit(fields, FIELD_IS_NOTIFIED,       outer.get("is_notified"))
    _emit(fields, FIELD_MALWARES,          outer.get("malwares"))
    _emit(fields, FIELD_MALWARES_NEW,      outer.get("malwares_new"))
    _emit(fields, FIELD_NEWS_FEED_TYPE,    outer.get("news_feed_type"))
    _emit(fields, FIELD_POST_DATE,         outer.get("post_date"))
    if outer.get("post_description") not in (None, ""):
        _emit(fields, FIELD_DESCRIPTION, outer.get("post_description"), max_len=_LONG_TEXT_MAX)
    _emit(fields, FIELD_POST_IMG,          outer.get("post_img"))
    _emit_json(fields, FIELD_POST_SOURCE,  outer.get("post_source"))
    _emit(fields, FIELD_TITLE,             outer.get("post_title"))
    _emit(fields, FIELD_URL,               outer.get("post_url"))
    _emit(fields, FIELD_REGIONS,           outer.get("regions"))
    _emit(fields, FIELD_SOURCE_COUNTRIES,  outer.get("source_countries"))
    _emit(fields, FIELD_TACTICS,           outer.get("tactics"))
    # data.tags is a populated list; common already emitted an empty Tags.
    # Override only when present.
    if outer.get("tags") not in (None, "", []):
        _emit(fields, FIELD_TAGS, outer.get("tags"))
    _emit(fields, FIELD_TARGET_COUNTRIES,  outer.get("target_countries"))
    _emit(fields, FIELD_THREAT_ACTORS,     outer.get("threat_actors"))
    _emit(fields, FIELD_THREAT_ACTORS_NEW, outer.get("threat_actors_new"))
    _emit(fields, FIELD_TTPS,              outer.get("ttps"))


def _extract_cyber_crime_forums(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    cyber_crime_forums / Cybercrime Forum Mentions — discussion-thread match
    on a monitored cybercrime forum.

    `data.discussion_content` is the (truncated) post body in the source
    language; we pass it through capped at `_LONG_TEXT_MAX`. `topic_url`
    becomes the canonical Url column so analyst can pivot to the source.

    Duplicates skipped:
      - data.discussion_by   ⇄ top-level `discussion_by`
      - data.discussion_date ⇄ top-level `discussion_date`
      - data.source_name     ⇄ top-level `source_name`
      - data.topic_name      ⇄ top-level `topic_name`
      - data.id              ⇄ data.discussion_id
      - data.updated_on      ⇄ common UpdatedAt
    """
    _emit(fields, FIELD_DISCUSSION_DATE, raw.get("discussion_date"))
    _emit(fields, FIELD_DISCUSSION_BY,   raw.get("discussion_by"))
    _emit(fields, FIELD_SOURCE_NAME,     raw.get("source_name"))
    _emit(fields, FIELD_TOPIC_NAME,      raw.get("topic_name"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    _emit(fields, FIELD_CATEGORY_ID,     outer.get("category_id"))
    _emit(fields, FIELD_CONTENT,         outer.get("discussion_content"), max_len=_LONG_TEXT_MAX)
    _emit(fields, FIELD_DISCUSSION_ID,   outer.get("discussion_id"))
    _emit(fields, FIELD_JOINED_DATE,     outer.get("joined_dated"))
    _emit(fields, FIELD_LIKES,           outer.get("likes"))
    _emit(fields, FIELD_NUMBER_OF_POSTS, outer.get("number_of_post"))
    _emit(fields, FIELD_REPUTATION,      outer.get("reputation"))
    _emit(fields, FIELD_TOPIC_CREATED_BY, outer.get("topic_created_by"))
    _emit(fields, FIELD_TOPIC_ID,        outer.get("topic_id"))
    _emit(fields, FIELD_URL,             outer.get("topic_url"))


def _extract_code_analysis_common(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """Shared top-level fields for github / bit_bucket / docker / postman."""
    _emit(fields, FIELD_FILENAME, raw.get("filename"))
    _emit(fields, FIELD_REPO,     raw.get("repository_name"))
    _emit(fields, FIELD_OWNER,    raw.get("owner_name"))


def _extract_github_nested(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """github — adds the data.data.* fields on top of the code-analysis trio."""
    dd = _safe_data_data(raw)
    _emit(fields, FIELD_FILE_URL,     dd.get("html_url"))
    _emit(fields, FIELD_FILE_PATH,    dd.get("path"))
    _emit(fields, FIELD_GIT_URL,      dd.get("git_url"))
    _emit(fields, FIELD_FILE_API_URL, dd.get("url"))
    _emit(fields, FIELD_COMMIT_SHA,   dd.get("sha"))
    _emit(fields, FIELD_MATCH_SCORE,  dd.get("score"))

    repo = dd.get("repository") if isinstance(dd.get("repository"), dict) else {}
    _emit(fields, FIELD_REPO_URL,         repo.get("html_url"))
    _emit(fields, FIELD_REPO_DESCRIPTION, repo.get("description"), max_len=_REPO_DESC_MAX)
    _emit(fields, FIELD_REPO_FULL_NAME,   repo.get("full_name"))
    _emit(fields, FIELD_REPO_LANGUAGE,    repo.get("language"))
    _emit(fields, FIELD_REPO_PRIVATE,     repo.get("private"))
    _emit(fields, FIELD_REPO_STARS,       repo.get("stargazers_count"))
    _emit(fields, FIELD_REPO_FORKS,       repo.get("forks_count"))
    owner = repo.get("owner") if isinstance(repo.get("owner"), dict) else {}
    _emit(fields, FIELD_REPO_OWNER_LOGIN, owner.get("login"))

    matches = dd.get("text_matches") if isinstance(dd.get("text_matches"), list) else []
    first = matches[0] if matches and isinstance(matches[0], dict) else {}
    _emit(fields, FIELD_MATCH_FRAGMENT, first.get("fragment"), max_len=_MATCH_FRAGMENT_MAX)
    inner = first.get("matches") if isinstance(first.get("matches"), list) else []
    texts = [m["text"] for m in inner if isinstance(m, dict) and m.get("text")]
    _emit(fields, FIELD_MATCHED_TEXT, texts)  # _emit joins lists with ", "


def _extract_stealer_logs(raw: Dict[str, Any], fields: Dict[str, str]) -> None:
    """
    stealer_logs / Compromised Endpoints — uses data.content / content_related_info
    rather than data.data.*. All declared fields are emitted, empty or not.
    """
    _emit(fields, FIELD_URL,              raw.get("url"))
    _emit(fields, FIELD_USERNAME,         raw.get("username"))
    _emit(fields, FIELD_COMPROMISED_DATE, raw.get("compromised_date"))
    _emit(fields, FIELD_MALWARE_FAMILY,   raw.get("malware_family"))

    outer = raw.get("data") if isinstance(raw.get("data"), dict) else {}

    content = outer.get("content") if isinstance(outer.get("content"), dict) else {}
    _emit(fields, FIELD_APPLICATION, content.get("Application"))
    # Plaintext leaked password. Stored as a Custom Field so analysts can
    # confirm the leak during triage. SOAR RBAC governs visibility; if a
    # tenant wants this masked, swap to a redaction helper here.
    _emit(fields, FIELD_PASSWORD, content.get("Password"))

    cri = outer.get("content_related_info") if isinstance(outer.get("content_related_info"), dict) else {}
    _emit(fields, FIELD_DOMAIN,       cri.get("domain"))
    _emit(fields, FIELD_USER_HASH,    cri.get("user_hash_ad"))
    _emit(fields, FIELD_COUNTRY_NAME, cri.get("country_name"))

    fm = outer.get("file_metadata") if isinstance(outer.get("file_metadata"), dict) else {}
    _emit(fields, FIELD_FILE_CREATED_DATE,  fm.get("creation_date"))
    _emit(fields, FIELD_FILE_MODIFIED_DATE, fm.get("last_modification_date"))
    _emit(fields, FIELD_FILE_C_DATE,        fm.get("c_date"))
    _emit(fields, FIELD_FILE_M_DATE,        fm.get("m_date"))
    _emit(fields, FIELD_FILE_FULL_PATH,     fm.get("full_filePath"))
    _emit(fields, FIELD_FILE_SIZE,          fm.get("size"))
    _emit(fields, FIELD_FILE_TYPE,          fm.get("type"))

    # `data.filename` (the file inside the stealer dump) shares the Filename
    # custom field with the code-analysis services. If `file_metadata.filename`
    # carries a more specific value we prefer that.
    _emit(fields, FIELD_FILENAME,         fm.get("filename") or outer.get("filename"))
    _emit(fields, FIELD_DOC_ID,           outer.get("doc_id"))
    _emit(fields, FIELD_PARENT_FOLDER_ID, outer.get("parent_folder_path_id"))
    _emit(fields, FIELD_DOC_CREATED_ON,   outer.get("created_on"))


# ── Title resolution ─────────────────────────────────────────────────────────


def _resolve_alert_title_value(raw: Dict[str, Any], service: str) -> str:
    """
    Decide what to render as the second half of the case title.

    Per-service rules (see constants.TITLE_FIELD_BY_SERVICE):
      - darkweb_data_breaches → breach_source
      - product_vulnerability → company
      - subdomains            → sub_domain
      - physical_threats, web_applications, vulnerability, postman, docker → title
      - everything else       → keyword_name

    Fallback chain when the configured field is empty/missing on a given alert:
      configured field  →  keyword_name  →  "N/A"
    so the SOAR case header is never blank.
    """
    field = TITLE_FIELD_BY_SERVICE.get(service, TITLE_FIELD_DEFAULT)
    value = _lookup_field(raw, field)
    if value:
        return value
    if field != "keyword_name":
        value = _lookup_field(raw, "keyword_name")
        if value:
            return value
    return "N/A"


# Known display names from the services API (populated at init or hardcoded fallback)
SERVICE_DISPLAY_NAMES: Dict[str, str] = {
    "ssl_expiry":                    "Asset SSL Expiry",
    "assets":                        "Assets",
    "botnet":                        "BotShield",
    "cloud_storage":                 "Cloud Storage",
    "bit_bucket":                    "Code Analysis - Bitbucket",
    "docker":                        "Code Analysis - Docker Hub",
    "github":                        "Code Analysis - Github",
    "postman":                       "Code Analysis - Postman",
    "compromised_cards":             "Compromised Cards",
    "compromised_endpoints_cookies": "Compromised Cookies",
    "stealer_logs":                  "Compromised Endpoints",
    "compromised_files":             "Compromised Files",
    "news_feed":                     "Cyber Newsfeed",
    "cyber_crime_forums":            "Cybercrime Forum Mentions",
    "cyble_research_labs":           "Cyble Research Labs",
    "advisory":                      "Cyble Research Labs Advisory",
    "darkweb_marketplaces":          "Darkweb Marketplaces",
    "darkweb_data_breaches":         "Data Exposures",
    "defacement_content":            "Defacement Content",
    "defacement_keyword":            "Defacement Keyword",
    "defacement_url":                "Defacement URL",
    "discord":                       "Discord",
    "domain_expiry":                 "Domain Expiry",
    "domain_watchlist":              "Domain Watchlist",
    "hacktivism":                    "Hacktivism",
    "i2p":                           "I2P Links",
    "iocs":                          "IoCs",
    "ip_risk_score":                 "IP Risk Score",
    "vulnerability":                 "Issues Catalog",
    "mobile_apps":                   "Mobile Apps",
    "new_vulnerability":             "Network Vulnerabilities - CVEs",
    "new_port":                      "New Ports",
    "flash_report":                  "News Flash",
    "osint":                         "OSINT",
    "ot_ics":                        "OT/ICS",
    "pastebin":                      "Pastesite",
    "phishing":                      "Phishing Monitoring",
    "product_vulnerability":         "Vulnerability Intelligence",
    "ransomware_updates":            "Ransomware Incidents",
    "darkweb_ransomware":            "Ransomware Leaks",
    "social_media_monitoring":       "Social Media Monitoring",
    "subdomains":                    "Subdomains",
    "suspicious_domains":            "Suspicious Domains",
    "telegram_mentions":             "Telegram Mentions",
    "tor_links":                     "Tor Links",
    "web_applications":              "Web Application Discovery",
    "physical_threats":              "Physical Threats",
    "malicious_ads":                 "Malicious Ads",
    "leaked_credentials":            "Leaked Credentials",
}


class CybleAlertMapper:

    @staticmethod
    def cyble_to_secops_alert(raw: Dict[str, Any], now_iso: str) -> Dict[str, Any]:
        """
        Transform a raw Cyble alert record into a dict ready for SecOps ingestion.

        Returns a dict with:
          - name:              display name for the alert
          - severity:          SecOps integer severity
          - rule_generator:    source system identifier
          - start_time:        alert creation time (unix ms)
          - end_time:          alert update time (unix ms)
          - events:            list with one event dict (raw alert flattened)
          - extensions:        custom properties — vendor-neutral field names,
                               every COMMON_FIELDS entry plus service extras,
                               always emitted even when the source value is null

        All field accesses use .get() with safe defaults — if Cyble adds or
        removes fields, ingestion continues and the missing field is logged.
        """
        service   = raw.get("service", "unknown")
        severity  = (raw.get("user_severity") or raw.get("severity") or "LOW").upper()
        status    = (raw.get("status") or "UNREVIEWED").upper()

        display_name = SERVICE_DISPLAY_NAMES.get(service, service.replace("_", " ").title())

        # Alert name format: "{Service Display Name} - {value}"
        # `value` comes from a per-service field (see TITLE_FIELD_BY_SERVICE);
        # falls back to keyword_name then "N/A" so the title is never blank.
        # Capped at 250 chars so it renders cleanly in the SOAR case header.
        title_value = _resolve_alert_title_value(raw, service)
        alert_name = ALERT_NAME_TEMPLATE.format(
            display_name=display_name,
            keyword=title_value,
        )[:250]

        secops_severity = CYBLE_TO_SECOPS_SEVERITY.get(severity, 0)
        # High-priority services get a severity bump if currently LOW/MEDIUM
        if service in HIGH_PRIORITY_SERVICES and secops_severity < 1:
            secops_severity = 1  # floor at MEDIUM for high-priority services

        created_ts = CybleAlertMapper._iso_to_unix_ms(raw.get("created_at"))
        updated_ts = CybleAlertMapper._iso_to_unix_ms(raw.get("updated_at")) or created_ts

        # Build the full custom-field set: common (always) + service-specific.
        fields: Dict[str, str] = {}
        _extract_common_fields(raw, fields)
        CybleAlertMapper._extract_service_fields(raw, service, fields)
        # LastSyncAt is the only synthetic field (set by the mapper, not from
        # the raw alert). Emit it AFTER the common loop so it always wins.
        fields[FIELD_LAST_SYNC_AT] = now_iso

        # Convenience labels for UDM event principal (kept for backward compat
        # with playbooks that read them off the event).
        keyword = fields.get(FIELD_KEYWORD, "")
        bucket  = fields.get(FIELD_BUCKET, "")
        alert_id = fields.get(FIELD_ALERT_ID, "")

        # Build the flat event record. UDM `additional.fields` is what shows
        # up in the SecOps "Event details" blade — keys here are lower_snake
        # by convention (UDM field-naming rules) and mirror the custom-field
        # contents so analysts can pivot either way.
        additional_fields = [
            {"key": k.lower() if k.isupper() else _camel_to_snake(k),
             "value": {"string_value": v}}
            for k, v in fields.items()
        ]
        event = {
            "metadata": {
                "product_name":       "Cyble Vision Alerts",
                "vendor_name":        "Cyble",
                "event_type":         "GENERIC_EVENT",
                "product_event_type": service,
            },
            "principal": {
                "labels": [
                    {"key": "keyword",   "value": keyword},
                    {"key": "service",   "value": service},
                    {"key": "bucket",    "value": bucket},
                    {"key": "alert_id",  "value": alert_id},
                ],
            },
            "additional": {"fields": additional_fields},
        }

        return {
            "name":           alert_name,
            "severity":       secops_severity,
            "rule_generator": f"Cyble Vision Alerts - {display_name}",
            "start_time":     created_ts,
            "end_time":       updated_ts,
            "events":         [event],
            "extensions":     fields,
        }

    @staticmethod
    def _extract_service_fields(raw: Dict[str, Any], service: str, fields: Dict[str, str]) -> None:
        """
        Dispatch to the appropriate per-service extractor. Each extractor uses
        `_emit` for every declared field so the output set is consistent
        regardless of whether the raw alert had a value for that field.

        Unknown services fall through with no extras — the common-fields loop
        already emitted everything top-level we know about.
        """
        if service == "assets":
            _extract_assets(raw, fields)

        elif service == "cloud_storage":
            _extract_cloud_storage(raw, fields)

        elif service == "ssl_expiry":
            _extract_ssl_expiry(raw, fields)

        elif service == "compromised_endpoints_cookies":
            _extract_compromised_endpoints_cookies(raw, fields)

        elif service == "compromised_files":
            _extract_compromised_files(raw, fields)

        elif service == "cyble_research_labs":
            _extract_cyble_research_labs(raw, fields)

        elif service == "advisory":
            _extract_advisory(raw, fields)

        elif service == "darkweb_marketplaces":
            _extract_darkweb_marketplaces(raw, fields)

        elif service == "darkweb_data_breaches":
            _extract_darkweb_data_breaches(raw, fields)

        elif service == "domain_expiry":
            _extract_domain_expiry(raw, fields)

        elif service == "domain_watchlist":
            _extract_domain_watchlist(raw, fields)

        elif service in ("github", "postman"):
            _extract_code_analysis_common(raw, fields)
            if service == "github":
                _extract_github_nested(raw, fields)
            else:  # postman
                _extract_postman_nested(raw, fields)

        elif service == "bit_bucket":
            # bit_bucket payload is structurally different (list of trufflehog
            # findings), so it has a dedicated extractor instead of going
            # through _extract_code_analysis_common.
            _extract_bit_bucket(raw, fields)

        elif service == "docker":
            _extract_docker_nested(raw, fields)

        elif service == "web_applications":
            _extract_web_applications(raw, fields)

        elif service == "physical_threats":
            _extract_physical_threats(raw, fields)

        elif service == "osint":
            _extract_osint(raw, fields)

        elif service == "malicious_ads":
            _extract_malicious_ads(raw, fields)

        elif service == "defacement_content":
            _extract_defacement_content(raw, fields)

        elif service == "defacement_keyword":
            _extract_defacement_keyword(raw, fields)

        elif service == "stealer_logs":
            _extract_stealer_logs(raw, fields)

        elif service == "hacktivism":
            _extract_hacktivism(raw, fields)

        elif service == "i2p":
            _extract_i2p(raw, fields)

        elif service == "ip_risk_score":
            _extract_ip_risk_score(raw, fields)

        elif service == "vulnerability":
            _extract_vulnerability(raw, fields)

        elif service == "new_vulnerability":
            _extract_new_vulnerability(raw, fields)

        elif service == "new_port":
            _extract_new_port(raw, fields)

        elif service == "flash_report":
            _extract_flash_report(raw, fields)

        elif service == "ot_ics":
            _extract_ot_ics(raw, fields)

        elif service == "pastebin":
            _extract_pastebin(raw, fields)

        elif service == "phishing":
            _extract_phishing(raw, fields)

        elif service == "product_vulnerability":
            _extract_product_vulnerability(raw, fields)

        elif service == "ransomware_updates":
            _extract_ransomware_updates(raw, fields)

        elif service == "darkweb_ransomware":
            _extract_darkweb_ransomware(raw, fields)

        elif service == "social_media_monitoring":
            _extract_social_media_monitoring(raw, fields)

        elif service == "subdomains":
            _extract_subdomains(raw, fields)

        elif service == "suspicious_domains":
            _extract_suspicious_domains(raw, fields)

        elif service == "telegram_mentions":
            _extract_telegram_mentions(raw, fields)

        elif service == "tor_links":
            _extract_tor_links(raw, fields)

        elif service == "leaked_credentials":
            _extract_leaked_credentials(raw, fields)

        elif service == "defacement_url":
            _extract_defacement_url(raw, fields)

        elif service == "discord":
            _extract_discord(raw, fields)

        elif service == "iocs":
            _extract_iocs(raw, fields)

        elif service == "mobile_apps":
            _extract_mobile_apps(raw, fields)

        elif service == "news_feed":
            _extract_news_feed(raw, fields)

        elif service == "cyber_crime_forums":
            _extract_cyber_crime_forums(raw, fields)

        # Remaining services (botnet, etc.) currently rely solely on
        # the common-fields loop. As samples arrive, add per-service
        # extractors above — never inline field-name string literals here.

    @staticmethod
    def build_idempotency_key(raw: Dict[str, Any]) -> str:
        """
        Stable unique key for deduplication.

        Uses `id` (alert UUID) as primary key — it's immutable.
        Falls back to data_id if id is absent (shouldn't happen but defensive).
        The same alert re-ingested due to an update will have the same key.
        """
        return raw.get("id") or raw.get("data_id") or ""

    @staticmethod
    def secops_to_cyble_update(
        cyble_alert_id: str,
        service: str,
        new_status: Optional[str] = None,
        new_severity: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build a Cyble update payload from SecOps action parameters.

        Args:
            cyble_alert_id: UUID stored in FIELD_ALERT_ID
            service:        service name stored in FIELD_SERVICE
            new_status:     SecOps-side status string or Cyble-native status
            new_severity:   SecOps-side severity string or Cyble-native severity

        Returns:
            Dict ready to pass to CybleManager.update_alerts()

        Raises:
            ValueError if neither status nor severity is provided.
        """
        if not new_status and not new_severity:
            raise ValueError("At least one of new_status or new_severity must be provided.")

        update: Dict[str, Any] = {
            "id":      cyble_alert_id,
            "service": service,
        }

        if new_status:
            cyble_status = SECOPS_TO_CYBLE_STATUS.get(new_status.upper(), new_status.upper())
            if cyble_status not in CYBLE_STATUSES:
                raise ValueError(
                    f"'{new_status}' is not a valid status. "
                    f"Valid values: {CYBLE_STATUSES}"
                )
            update["status"] = cyble_status

        if new_severity:
            upper = new_severity.upper()
            if upper.lstrip("-").isdigit():
                cyble_sev = SECOPS_INT_TO_CYBLE_SEVERITY.get(int(upper), "MEDIUM")
            else:
                cyble_sev = SECOPS_TO_CYBLE_SEVERITY.get(upper, upper)
            valid_severities = set(SECOPS_TO_CYBLE_SEVERITY.values())
            if cyble_sev not in valid_severities:
                raise ValueError(
                    f"'{new_severity}' is not a valid severity. "
                    f"Valid values: {list(valid_severities)}"
                )
            update["user_severity"] = cyble_sev

        return update

    # ── Utilities ─────────────────────────────────────────────────────────────

    @staticmethod
    def _iso_to_unix_ms(iso_str: Optional[str]) -> Optional[int]:
        """
        Convert an ISO 8601 string (with or without timezone) to Unix milliseconds.
        Returns None if the string is absent or unparseable — never crashes.
        """
        if not iso_str:
            return None
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
        ):
            try:
                from datetime import datetime
                dt = datetime.strptime(iso_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return int(dt.timestamp() * 1000)
            except ValueError:
                continue
        logger.warning("Could not parse datetime string: %s", iso_str)
        return None


def _camel_to_snake(name: str) -> str:
    """
    Convert PascalCase / camelCase custom-field names to snake_case for the
    UDM event additional-fields dictionary. Idempotent for already-snake names.
    """
    out = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0 and (name[i - 1].islower() or
                                       (i + 1 < len(name) and name[i + 1].islower())):
            out.append("_")
        out.append(ch.lower())
    return "".join(out)
