"""Validation, filter mapping, timestamps, and log redaction."""

from __future__ import annotations

import json
import logging
import re
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable
from urllib.parse import urlparse

from .constants import (
    ALERT_STATUS_OPTIONS,
    BACKFILL_MAX,
    BACKFILL_MIN,
    ENTITY_OPTIONS,
    INCIDENT_INVESTIGATION_STATUS_OPTIONS,
    INCIDENT_USER_STATUS_OPTIONS,
    LOOKBACK_MAX,
    LOOKBACK_MIN,
    MSG_BAD_REQUEST,
    MSG_FORBIDDEN,
    MSG_INVALID_ACCESS_KEY,
    MSG_INVALID_ACCESS_KEY_ID,
    MSG_NOT_FOUND,
    MSG_RATE_LIMIT,
    MSG_TIMEOUT,
    MSG_UNAUTHORIZED,
    MSG_UNREACHABLE,
    PARAM_ALERT_SEVERITIES,
    PARAM_ALERT_STATUSES,
    PARAM_ALERT_VERDICTS,
    PARAM_BACKFILL,
    PARAM_ENTITIES,
    PARAM_HAS_RELATED,
    PARAM_INCIDENT_INVESTIGATION_STATUSES,
    PARAM_INCIDENT_SEVERITIES,
    PARAM_INCIDENT_USER_STATUSES,
    PARAM_INCIDENT_VERDICTS,
    PARAM_LOOKBACK,
    PARAM_PYTHON_TIMEOUT,
    PYTHON_TIMEOUT_MAX,
    PYTHON_TIMEOUT_MIN,
    RELATED_OPTIONS,
    SEVERITY_OPTIONS,
    VERDICT_OPTIONS,
)
from .exceptions import (
    VegaBadRequestException,
    VegaException,
    VegaForbiddenException,
    VegaNotFoundException,
    VegaRateLimitException,
    VegaTimeoutException,
    VegaUnauthorizedException,
    VegaValidationException,
)

logger = logging.getLogger(__name__)

_SECRET_KEYS = (
    "access_key",
    "access_key_id",
    "session_jwt",
    "jwtsessiontoken",
    "x-vega-key-id",
    "authorization",
)
_JSONISH_RE = re.compile(r"\{[^{}]{0,500}\}")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_timestamp(value: str | None) -> datetime | None:
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


def to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_csv_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        return [str(item).strip() for item in raw if str(item).strip()]
    text = str(raw).strip()
    if not text:
        return []
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except Exception:
            pass
    for sep in (",", ";", "|"):
        if sep in text:
            return [part.strip() for part in text.split(sep) if part.strip()]
    return [text]


def truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in ("true", "1", "yes")


def normalize_api_root(value: Any) -> str:
    text = str(value or "").strip().rstrip("/")
    if not text:
        raise VegaValidationException(
            "API Root is required. Enter the Vega HTTPS base URL, for example https://api.vega.io."
        )
    parsed = urlparse(text)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise VegaValidationException("API Root must be an HTTPS URL, for example https://api.vega.io.")
    return text


def require_secret(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise VegaValidationException(f"{name} is required. Enter a valid {name}.")
    return text


def parse_int_in_range(
    value: Any,
    name: str,
    minimum: int,
    maximum: int,
    default: int | None = None,
) -> int:
    """Parse a required integer in [minimum, maximum]. Invalid values raise."""
    text = "" if value is None else str(value).strip()
    if text == "":
        if default is not None:
            return default
        raise VegaValidationException(f"{name} is required. Enter an integer from {minimum} to {maximum}.")
    if not re.fullmatch(r"-?\d+", text):
        raise VegaValidationException(
            f'"{text}" is not a valid value for {name}. Enter an integer from {minimum} to {maximum}.'
        )
    number = int(text)
    if number < minimum or number > maximum:
        raise VegaValidationException(
            f'"{text}" is not a valid value for {name}. Use a number from {minimum} to {maximum}.'
        )
    return number


def parse_lookback_minutes(value: Any) -> int:
    return parse_int_in_range(
        value,
        PARAM_LOOKBACK,
        LOOKBACK_MIN,
        LOOKBACK_MAX,
    )


def parse_backfill_days(value: Any) -> int:
    return parse_int_in_range(
        value,
        PARAM_BACKFILL,
        BACKFILL_MIN,
        BACKFILL_MAX,
    )


def to_graphql_enum(value: str) -> str:
    """Map operator labels with spaces to GraphQL enum names."""
    return " ".join(str(value).split()).replace(" ", "_")


def _raise_unsupported(param_name: str, unknown: list[str], allowed: Iterable[str]) -> None:
    quoted = ", ".join(f'"{item}"' for item in unknown)
    possible = ", ".join(allowed)
    if len(unknown) == 1:
        raise VegaValidationException(f"{quoted} is not a valid value for {param_name}. Possible values: {possible}.")
    raise VegaValidationException(f"{quoted} are not valid values for {param_name}. Possible values: {possible}.")


def _filter_known(selected: list[str], allowed: Iterable[str]) -> tuple[list[str], list[str]]:
    allowed_map = {item.upper(): to_graphql_enum(item) for item in allowed}
    allowed_tokens = {to_graphql_enum(item).upper(): to_graphql_enum(item) for item in allowed}
    result: list[str] = []
    unknown: list[str] = []
    seen: set[str] = set()
    seen_unknown: set[str] = set()
    for raw in selected:
        token = to_graphql_enum(raw)
        key = token.upper()
        mapped = allowed_map.get(raw.strip().upper()) or allowed_tokens.get(key)
        if not mapped:
            label = " ".join(str(raw).split())
            if label and label not in seen_unknown:
                seen_unknown.add(label)
                unknown.append(label)
            continue
        if mapped in seen:
            continue
        seen.add(mapped)
        result.append(mapped)
    return result, unknown


def resolve_multi_filter(
    raw: Any,
    allowed: Iterable[str],
    *,
    param_name: str,
    empty_means_all: bool = True,
) -> list[str] | None:
    """Return GraphQL enum values. Empty = all/omit. Unsupported values raise."""
    selected = parse_csv_list(raw)
    if not selected:
        return None if empty_means_all else []
    resolved, unknown = _filter_known(selected, allowed)
    if unknown:
        _raise_unsupported(param_name, unknown, allowed)
    if not resolved:
        return None if empty_means_all else []
    allowed_list = [to_graphql_enum(item) for item in allowed]
    if empty_means_all and set(resolved) == set(allowed_list):
        return None
    return resolved


def resolve_entities(raw: Any) -> list[str]:
    selected = parse_csv_list(raw)
    if not selected:
        raise VegaValidationException(f"{PARAM_ENTITIES} is required. Use one or both of: {', '.join(ENTITY_OPTIONS)}.")
    known = {item.lower(): item for item in ENTITY_OPTIONS}
    known["alert"] = "Alerts"
    known["incident"] = "Incidents"
    resolved = []
    unknown = []
    for item in selected:
        match = known.get(item.lower())
        if match:
            if match not in resolved:
                resolved.append(match)
            continue
        if item not in unknown:
            unknown.append(item)
    if unknown:
        _raise_unsupported(PARAM_ENTITIES, unknown, ENTITY_OPTIONS)
    if not resolved:
        raise VegaValidationException(f"{PARAM_ENTITIES} is required. Use one or both of: {', '.join(ENTITY_OPTIONS)}.")
    return resolved


def resolve_has_related(raw: Any) -> bool | None:
    selected = parse_csv_list(raw)
    if not selected:
        raise VegaValidationException(
            f"{PARAM_HAS_RELATED} is required. Use one or both of: {', '.join(RELATED_OPTIONS)}."
        )
    known = {item.lower(): item for item in RELATED_OPTIONS}
    resolved = []
    unknown = []
    for item in selected:
        match = known.get(item.lower())
        if match:
            if match not in resolved:
                resolved.append(match)
            continue
        if item not in unknown:
            unknown.append(item)
    if unknown:
        _raise_unsupported(PARAM_HAS_RELATED, unknown, RELATED_OPTIONS)
    if not resolved:
        raise VegaValidationException(
            f"{PARAM_HAS_RELATED} is required. Use one or both of: {', '.join(RELATED_OPTIONS)}."
        )
    if set(resolved) == set(RELATED_OPTIONS):
        return None
    return resolved[0] == "Yes"


def resolve_alert_filters(config: dict) -> dict:
    return {
        "severities": resolve_multi_filter(
            config.get("alert_severities"),
            SEVERITY_OPTIONS,
            param_name=PARAM_ALERT_SEVERITIES,
        ),
        "statuses": resolve_multi_filter(
            config.get("alert_statuses"),
            ALERT_STATUS_OPTIONS,
            param_name=PARAM_ALERT_STATUSES,
        ),
        "verdicts": resolve_multi_filter(
            config.get("alert_verdicts"),
            VERDICT_OPTIONS,
            param_name=PARAM_ALERT_VERDICTS,
        ),
        "has_related": resolve_has_related(config.get("has_related")),
    }


def resolve_incident_filters(config: dict) -> dict:
    return {
        "severities": resolve_multi_filter(
            config.get("incident_severities"),
            SEVERITY_OPTIONS,
            param_name=PARAM_INCIDENT_SEVERITIES,
        ),
        "user_statuses": resolve_multi_filter(
            config.get("incident_user_statuses"),
            INCIDENT_USER_STATUS_OPTIONS,
            param_name=PARAM_INCIDENT_USER_STATUSES,
        ),
        "investigation_statuses": resolve_multi_filter(
            config.get("incident_investigation_statuses"),
            INCIDENT_INVESTIGATION_STATUS_OPTIONS,
            param_name=PARAM_INCIDENT_INVESTIGATION_STATUSES,
        ),
        "verdicts": resolve_multi_filter(
            config.get("incident_verdicts"),
            VERDICT_OPTIONS,
            param_name=PARAM_INCIDENT_VERDICTS,
        ),
    }


def redact(value: Any) -> Any:
    """Return a copy with secret-looking keys and JWT-like strings removed."""
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if str(key).strip().lower() in _SECRET_KEYS:
                redacted[key] = "<redacted>"
            else:
                redacted[key] = redact(item)
        return redacted
    if isinstance(value, list):
        return [redact(item) for item in value]
    text = str(value) if value is not None else ""
    if len(text) > 20 and text.count(".") == 2:
        return "<redacted>"
    return value


_KEY_ID_HINTS = (
    "key-id",
    "key_id",
    "keyid",
    "x-vega-key-id",
    "access key id",
    "access_key_id",
)
_ACCESS_KEY_ONLY_RE = re.compile(r"access[_\s]?key(?![_\s]?id)")


def classify_credential_error(text: str) -> str | None:
    """Return a specific credential message when the API text names the field."""
    raw = (text or "").lower()
    mentions_key_id = any(hint in raw for hint in _KEY_ID_HINTS)
    mentions_key = bool(_ACCESS_KEY_ONLY_RE.search(raw))
    if mentions_key_id and not mentions_key:
        return MSG_INVALID_ACCESS_KEY_ID
    if mentions_key and not mentions_key_id:
        return MSG_INVALID_ACCESS_KEY
    return None


def format_user_facing_error(exc: BaseException) -> str:
    if isinstance(exc, VegaValidationException):
        return str(exc)
    if isinstance(exc, VegaUnauthorizedException):
        return str(exc).strip() or MSG_UNAUTHORIZED
    if isinstance(exc, VegaForbiddenException):
        return MSG_FORBIDDEN
    if isinstance(exc, VegaBadRequestException):
        return str(exc).strip() or MSG_BAD_REQUEST
    if isinstance(exc, VegaNotFoundException):
        return MSG_NOT_FOUND
    if isinstance(exc, VegaRateLimitException):
        return MSG_RATE_LIMIT
    if isinstance(exc, VegaTimeoutException):
        return str(exc).strip() or MSG_TIMEOUT
    if isinstance(exc, VegaException):
        classified = classify_credential_error(str(exc))
        if classified:
            return classified
        return str(exc)[:300] or "Vega request failed. Please try again."
    raw = str(exc or "").strip().lower()
    if "timeout" in raw or "timed out" in raw:
        return MSG_TIMEOUT
    if any(token in raw for token in ("connection", "name or service not known")):
        return MSG_UNREACHABLE
    if "429" in raw:
        return MSG_RATE_LIMIT
    if "401" in raw:
        return classify_credential_error(raw) or MSG_UNAUTHORIZED
    cleaned = _JSONISH_RE.sub("", str(exc or ""))
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" :-")[:300]
    return cleaned or "Unexpected error while talking to Vega. Check configuration."


def format_connector_field_errors(errors: list[str]) -> str:
    """Friendly message that names each invalid connector field."""
    cleaned = [str(item).strip() for item in errors if str(item).strip()]
    if not cleaned:
        return "Cannot run the Vega Alerts and Incidents Connector. Check the connector fields and try again."
    if len(cleaned) == 1:
        return f"Cannot run the Vega Alerts and Incidents Connector. {cleaned[0]}"
    bullets = "\n".join(f"- {item}" for item in cleaned)
    return f"Cannot run the Vega Alerts and Incidents Connector because some fields are invalid:\n{bullets}"


def format_test_connection_summary(
    incident_count: int,
    related_alert_count: int,
    unrelated_alert_count: int,
    total_alert_count: int,
    sample_count: int = 0,
    include_incidents: bool = True,
    include_related: bool = True,
    include_unrelated: bool = True,
) -> str:
    """Clean test-connection output shown with sample alerts.

    Count lines follow Vega Entities to Fetch and Has Related Incidents, so a
    Yes-only connector does not report unrelated alerts.
    """
    lines = ["Successfully connected to Vega.", "", "What this connector currently sees:"]
    if include_incidents:
        lines.append(f"- Vega incidents: {incident_count}")
    if include_related:
        lines.append(f"- Vega related alerts: {related_alert_count}")
    if include_unrelated:
        lines.append(f"- Vega unrelated alerts: {unrelated_alert_count}")
    if include_related or include_unrelated:
        lines.append(f"- Total Vega alerts: {total_alert_count}")
    sample_line = (
        f"Showing {sample_count} sample alert(s) below. Nothing was ingested."
        if sample_count
        else ("No sample alerts were found for the current filters and time window. Nothing was ingested.")
    )
    lines.extend(["", sample_line])
    return "\n".join(lines)


def validate_connector_fields(
    *,
    api_root: Any,
    access_key_id: Any,
    access_key: Any,
    entities_raw: Any,
    lookback_minutes: Any,
    backfill_days: Any,
    alert_severities: Any = "",
    alert_statuses: Any = "",
    alert_verdicts: Any = "",
    has_related: Any = "Yes,No",
    incident_severities: Any = "",
    incident_user_statuses: Any = "",
    incident_investigation_statuses: Any = "",
    incident_verdicts: Any = "",
    python_timeout: Any = None,
) -> None:
    """Validate every connector field before login or ingest.

    Collects all field problems so the test-connection output and connector
    logs can name each invalid field and what is wrong with it.
    """
    errors: list[str] = []

    def _check(callback) -> None:
        try:
            callback()
        except VegaValidationException as exc:
            text = str(exc).strip()
            if text and text not in errors:
                errors.append(text)

    _check(lambda: normalize_api_root(api_root))
    _check(lambda: require_secret(access_key_id, "Access Key ID"))
    _check(lambda: require_secret(access_key, "Access Key"))
    _check(lambda: resolve_entities(entities_raw))
    _check(lambda: parse_lookback_minutes(lookback_minutes))
    _check(lambda: parse_backfill_days(backfill_days))
    _check(
        lambda: resolve_multi_filter(
            alert_severities,
            SEVERITY_OPTIONS,
            param_name=PARAM_ALERT_SEVERITIES,
        )
    )
    _check(
        lambda: resolve_multi_filter(
            alert_statuses,
            ALERT_STATUS_OPTIONS,
            param_name=PARAM_ALERT_STATUSES,
        )
    )
    _check(
        lambda: resolve_multi_filter(
            alert_verdicts,
            VERDICT_OPTIONS,
            param_name=PARAM_ALERT_VERDICTS,
        )
    )
    _check(lambda: resolve_has_related(has_related))
    _check(
        lambda: resolve_multi_filter(
            incident_severities,
            SEVERITY_OPTIONS,
            param_name=PARAM_INCIDENT_SEVERITIES,
        )
    )
    _check(
        lambda: resolve_multi_filter(
            incident_user_statuses,
            INCIDENT_USER_STATUS_OPTIONS,
            param_name=PARAM_INCIDENT_USER_STATUSES,
        )
    )
    _check(
        lambda: resolve_multi_filter(
            incident_investigation_statuses,
            INCIDENT_INVESTIGATION_STATUS_OPTIONS,
            param_name=PARAM_INCIDENT_INVESTIGATION_STATUSES,
        )
    )
    _check(
        lambda: resolve_multi_filter(
            incident_verdicts,
            VERDICT_OPTIONS,
            param_name=PARAM_INCIDENT_VERDICTS,
        )
    )
    if python_timeout is not None:
        _check(
            lambda: parse_int_in_range(
                python_timeout,
                PARAM_PYTHON_TIMEOUT,
                PYTHON_TIMEOUT_MIN,
                PYTHON_TIMEOUT_MAX,
            )
        )
    if errors:
        raise VegaValidationException(format_connector_field_errors(errors))


def safe_log(logger_obj, level: str, msg: str, *args) -> None:
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


def iter_current_vega_ids(siemplify: Any) -> list[str]:
    """Collect Vega IDs from the current SOAR alert's events."""
    found: list[str] = []
    seen: set[str] = set()

    def _add(value: Any) -> None:
        text = str(value or "").strip()
        if not text or ":event:" in text:
            return
        if text not in seen:
            seen.add(text)
            found.append(text)

    keys = ("vega_id", "product_log_id", "vega_alert_id", "vegaAlertId")
    try:
        alert = siemplify.current_alert
        events = getattr(alert, "security_events", None) or getattr(alert, "events", None) or []
        for event in events:
            additional = getattr(event, "additional_properties", None) or {}
            sources = []
            if isinstance(additional, dict):
                sources.append(additional)
            if isinstance(event, dict):
                sources.append(event)
            else:
                sources.append(getattr(event, "__dict__", {}) or {})
            for source in sources:
                if not isinstance(source, dict):
                    continue
                for key in keys:
                    _add(source.get(key))
            for key in keys:
                _add(getattr(event, key, None))
    except Exception:
        return found
    return found


def get_current_vega_id(siemplify: Any) -> str:
    """Return the first Vega ID from the current alert, or '' when none."""
    ids = iter_current_vega_ids(siemplify)
    return ids[0] if ids else ""


def compute_time_window(
    checkpoint: dict,
    backfill_days: int,
    lookback_minutes: int,
    now: datetime | None = None,
) -> dict:
    current = now or utc_now()
    lookback = timedelta(minutes=lookback_minutes)
    state = checkpoint or {}
    origin = parse_iso_timestamp(state.get("origin_from"))
    if origin is None:
        origin = current - timedelta(days=backfill_days) - lookback
    watermark = parse_iso_timestamp(state.get("watermark"))
    incomplete = bool(state.get("incomplete"))
    query_mode = str(state.get("query_mode") or "").strip().lower()
    # Missing origin_from means an upgraded or poisoned checkpoint that already
    # jumped watermark to "now". Rescan the original createdAt backfill and skip
    # ingested IDs instead of polling a 5-minute updatedAt window.
    catching_up = incomplete or query_mode == "created" or not str(state.get("origin_from") or "").strip()
    if catching_up:
        return {
            "first_run": watermark is None,
            "query_mode": "created",
            "from": to_iso(origin),
            "to": to_iso(current),
            "updated_from": None,
            "updated_to": None,
            "end": to_iso(current),
            "origin_from": to_iso(origin),
        }
    start = (watermark or origin) - lookback
    return {
        "first_run": False,
        "query_mode": "updated",
        "from": None,
        "to": None,
        "updated_from": to_iso(start),
        "updated_to": to_iso(current),
        "end": to_iso(current),
        "origin_from": to_iso(origin),
    }


def generate_random_password(length: int = 16) -> str:
    """Return a random password that meets typical Okta complexity rules.

    The alphabet omits quotes, backslashes, and brackets so the value can be
    dropped into playbook JSON and email bodies without extra escaping.
    """
    from .constants import MIN_PASSWORD_LENGTH, PASSWORD_SYMBOLS

    if length < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password length must be at least {MIN_PASSWORD_LENGTH} characters.")
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    pools = (lower, upper, digits, PASSWORD_SYMBOLS)
    alphabet = "".join(pools)
    chars = [secrets.choice(pool) for pool in pools]
    chars.extend(secrets.choice(alphabet) for _ in range(length - len(pools)))
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)
