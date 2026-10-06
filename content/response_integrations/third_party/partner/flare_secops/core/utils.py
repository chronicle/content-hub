"""Shared helpers for timestamps, filters, and historical backfill."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .constants import MAX_BACKFILL_RANGE_DAYS
from .exceptions import (
    FlareBadRequestException,
    FlareException,
    FlareForbiddenException,
    FlareNotFoundException,
    FlareRateLimitException,
    FlareUnauthorizedException,
    FlareValidationException,
)

logger = logging.getLogger(__name__)

_JSONISH_RE = re.compile(r"\{[^{}]{0,500}\}")
_HTTP_STATUS_RE = re.compile(r"HTTP\s+(\d{3})", re.IGNORECASE)


def parse_tenant_id(value: Any) -> int:
    """Parse and validate Flare Tenant ID as a positive integer."""
    text = str(value if value is not None else "").strip()
    if not text:
        raise FlareValidationException(
            "Flare Tenant ID is required. Enter the numeric tenant ID from Flare."
        )
    if not text.isdigit():
        raise FlareValidationException(
            "Flare Tenant ID must be a number. Please enter a valid tenant ID."
        )
    tenant_id = int(text)
    if tenant_id <= 0:
        raise FlareValidationException(
            "Flare Tenant ID must be a positive number. Please enter a valid tenant ID."
        )
    return tenant_id


def format_user_facing_error(exc: BaseException) -> str:
    """
    Convert raw exceptions / API payloads into short, human-readable messages
    for Configure Instance Test, connector Testing, Run once, and Logs.
    """
    if isinstance(exc, FlareValidationException):
        return str(exc)
    if isinstance(exc, FlareUnauthorizedException):
        return "Invalid API Key. Please check your credentials and try again."
    if isinstance(exc, FlareForbiddenException):
        return (
            "Access denied for this Flare Tenant ID. "
            "Verify the tenant ID and API key permissions."
        )
    if isinstance(exc, FlareBadRequestException):
        return "Invalid request to Flare. Check the connector filters and try again."
    if isinstance(exc, FlareNotFoundException):
        return "Requested Flare resource was not found. Verify the tenant ID and filters."
    if isinstance(exc, FlareRateLimitException):
        return "Flare rate limit reached. Wait a moment and try again."
    if isinstance(exc, FlareException):
        cleaned = _strip_raw_payload(str(exc))
        return cleaned or "Flare request failed. Please try again."

    raw = str(exc or "").strip()
    lower = raw.lower()

    if "invalid literal for int" in lower or (
        "tenant id" in lower and "number" in lower
    ):
        return "Flare Tenant ID must be a number. Please enter a valid tenant ID."
    if any(token in lower for token in ("invalid_key", "invalid api key", "unauthorized")):
        return "Invalid API Key. Please check your credentials and try again."
    if "forbidden" in lower:
        return (
            "Access denied for this Flare Tenant ID. "
            "Verify the tenant ID and API key permissions."
        )
    if "timeout" in lower or "timed out" in lower:
        return "Connection to Flare timed out. Check network access and try again."
    if any(token in lower for token in ("connection", "name or service not known", "nodename")):
        return "Unable to reach the Flare API. Check network access and try again."

    status_match = _HTTP_STATUS_RE.search(raw)
    if status_match:
        status = status_match.group(1)
        if status == "401":
            return "Invalid API Key. Please check your credentials and try again."
        if status == "403":
            return (
                "Access denied for this Flare Tenant ID. "
                "Verify the tenant ID and API key permissions."
            )
        if status == "404":
            return "Requested Flare resource was not found."
        if status == "429":
            return "Flare rate limit reached. Wait a moment and try again."
        if status.startswith("5"):
            return "Flare service is temporarily unavailable. Please try again later."

    cleaned = _strip_raw_payload(raw)
    if cleaned:
        return cleaned
    return "Unexpected error while talking to Flare. Check configuration and try again."


def _strip_raw_payload(message: str) -> str:
    """Drop embedded JSON / HTML dumps so operators see a short sentence."""
    text = (message or "").strip()
    if not text:
        return ""
    text = _JSONISH_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" :-")
    # Prefer the first sentence-like chunk when the platform appends a traceback hint.
    for sep in ("Traceback", "File \"", "\n"):
        if sep in text:
            text = text.split(sep, 1)[0].strip(" :-")
    return text[:300]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw or raw.lower() in ("null", "none"):
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_flare_timestamp(value: Optional[str]) -> Optional[str]:
    """Normalize UI/checkpoint timestamps to Flare-friendly ISO-8601 UTC."""
    parsed = parse_iso_timestamp(value)
    if parsed is None:
        return value.strip() if isinstance(value, str) and value.strip() else None
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_backfill_range_days(val: Any) -> int:
    """
    Validate a backfill range from 0 through MAX_BACKFILL_RANGE_DAYS.

    Zero disables historical backfill. Invalid or out-of-range values fail
    explicitly instead of silently requesting an unexpected date range.
    """
    try:
        days = int(val)
    except (TypeError, ValueError):
        raise ValueError(
            f"Backfill Range (Days) must be an integer from 0 to "
            f"{MAX_BACKFILL_RANGE_DAYS}."
        )

    if days < 0 or days > MAX_BACKFILL_RANGE_DAYS:
        raise ValueError(
            f"Backfill Range (Days) must be between 0 and "
            f"{MAX_BACKFILL_RANGE_DAYS}; received {days}."
        )

    return days


def default_backfill_start(backfill_days: Any) -> str:
    days = validate_backfill_range_days(backfill_days)
    if days == 0:
        return utc_now_iso()

    start = utc_now() - timedelta(days=days)
    return start.replace(hour=0, minute=0, second=0, microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def parse_csv_list(raw: Optional[str]) -> list:
    """Parse comma/semicolon/pipe-separated values (or a JSON list) into a list."""
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        return [str(s).strip() for s in raw if str(s).strip()]
    text = str(raw).strip()
    if not text:
        return []
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(s).strip() for s in parsed if str(s).strip()]
        except Exception:
            pass
    for sep in (",", ";", "|"):
        if sep in text:
            return [s.strip() for s in text.split(sep) if s.strip()]
    return [text]


def safe_log(logger_obj, level: str, msg: str, *args) -> None:
    """
    Log through the Siemplify logger, which does not accept %-style args.

    Interpolating here keeps messages readable instead of emitting raw "%s".
    """
    text = msg
    if args:
        try:
            text = msg % args
        except Exception:
            text = " ".join([msg] + [str(arg) for arg in args])

    log_fn = getattr(logger_obj, level, None) if logger_obj else None
    if callable(log_fn):
        log_fn(text)
    else:
        getattr(logger, level)(text)


def _normalize_filter_token(value: Any) -> str:
    """Case-insensitive token: lower-case and collapse spaces/hyphens to underscores."""
    text = str(value or "").strip().lower()
    text = re.sub(r"[\s\-]+", "_", text)
    return text


def _option_key_and_labels(item: Any, extra_label_map: Optional[dict] = None) -> Optional[dict]:
    """
    Normalize one Flare filter catalog entry to {"key": <api value>, "labels": set()}.

    Accepts strings or dicts with common key/label fields (value/name/label/...).
    """
    labels: set = set()
    key = None

    if isinstance(item, str):
        key = item.strip()
    elif isinstance(item, dict):
        for field in ("value", "id", "key", "uid", "type", "code"):
            candidate = item.get(field)
            if candidate is not None and str(candidate).strip():
                key = str(candidate).strip()
                break
        for field in (
            "name",
            "label",
            "display_name",
            "displayName",
            "title",
            "description",
        ):
            candidate = item.get(field)
            if candidate is not None and str(candidate).strip():
                labels.add(str(candidate).strip())
        if key is None and labels:
            key = next(iter(labels))
    else:
        key = str(item).strip() if item is not None else ""

    if not key:
        return None

    labels.add(key)
    if extra_label_map:
        mapped = extra_label_map.get(key) or extra_label_map.get(key.lower())
        if mapped:
            labels.add(str(mapped))
    return {"key": key, "labels": labels}


def extract_filter_options(
    raw: Any,
    extra_label_map: Optional[dict] = None,
) -> list:
    """
    Flatten Flare severity/type filter payloads into option dicts.

    Handles:
      - ["critical", ...]
      - [{"value": "paste", "name": "..."}, ...]
      - {"severities"|"items"|"data"|"types": [...]}
      - {"categories": [{"types": [...]}]}
    """
    items: list = []
    if raw is None:
        items = []
    elif isinstance(raw, list):
        items = list(raw)
    elif isinstance(raw, dict):
        if isinstance(raw.get("categories"), list):
            for category in raw["categories"]:
                if not isinstance(category, dict):
                    continue
                types = category.get("types") or category.get("items") or []
                if isinstance(types, list):
                    items.extend(types)
        else:
            for field in ("severities", "types", "items", "data", "results"):
                candidate = raw.get(field)
                if isinstance(candidate, list):
                    items = list(candidate)
                    break
            if not items and raw.get("value") is not None:
                items = [raw]
    else:
        items = [raw]

    options: list = []
    seen: set = set()
    for item in items:
        option = _option_key_and_labels(item, extra_label_map=extra_label_map)
        if not option:
            continue
        dedupe = _normalize_filter_token(option["key"])
        if dedupe in seen:
            continue
        seen.add(dedupe)
        options.append(option)
    return options


def resolve_selected_filters(
    user_input: Any,
    options: list,
    filter_name: str,
    *,
    allow_empty_as_all: bool = True,
) -> list:
    """
    Resolve connector filter input against Flare catalog values.

    - Case-insensitive match on API key and display labels.
    - Empty input → all catalog keys (API defaults), when allow_empty_as_all.
    - Unknown values → FlareValidationException with a human-readable message.
    """
    selected = parse_csv_list(user_input)
    option_keys = [opt["key"] for opt in options if opt.get("key")]

    if not selected:
        if allow_empty_as_all:
            return list(option_keys)
        return []

    lookup: dict = {}
    for opt in options:
        key = opt.get("key")
        if not key:
            continue
        lookup[_normalize_filter_token(key)] = key
        for label in opt.get("labels") or set():
            lookup[_normalize_filter_token(label)] = key

    resolved: list = []
    unknown: list = []
    seen: set = set()
    for value in selected:
        match = lookup.get(_normalize_filter_token(value))
        if not match:
            unknown.append(value)
            continue
        token = _normalize_filter_token(match)
        if token in seen:
            continue
        seen.add(token)
        resolved.append(match)

    if unknown:
        valid = ", ".join(option_keys) if option_keys else "(none returned by Flare)"
        raise FlareValidationException(
            f"Invalid {filter_name} value(s): {', '.join(unknown)}. "
            f"Valid values: {valid}."
        )

    return resolved



def extract_event_timestamp(event: dict) -> str:
    """Prefer estimated_created_at — matches Flare _search filter watermark."""
    meta = event.get("metadata") or {}
    tenant_meta = event.get("tenant_metadata") or {}
    for obj in (meta, tenant_meta, event):
        if not isinstance(obj, dict):
            continue
        for key in ("estimated_created_at", "matched_at", "created_at"):
            val = obj.get(key)
            if val:
                return val
    return ""


def max_event_timestamp(events: list) -> Optional[str]:
    best_ts: Optional[str] = None
    best_dt: Optional[datetime] = None
    for event in events:
        if not isinstance(event, dict):
            continue
        ts = extract_event_timestamp(event)
        parsed = parse_iso_timestamp(ts)
        if parsed is None:
            continue
        if best_dt is None or parsed > best_dt:
            best_dt = parsed
            best_ts = ts
    return best_ts


def cap_page_size(size: int, maximum: int = 10) -> int:
    try:
        size = int(size)
    except (TypeError, ValueError):
        size = maximum
    return max(1, min(size, maximum))
