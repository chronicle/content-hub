"""Input validation and checkpoint helpers for the DSPM / IR violations connector."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from TIPCommon.extraction import extract_connector_param

from .constants import (
    ERROR_SERVICE_ACCOUNT_MISSING_KEYS,
    MAX_SEARCH_TIME_PERIOD_DAYS,
    MIN_SEARCH_TIME_PERIOD_DAYS,
    SERVICE_ACCOUNT_REQUIRED_KEYS,
)
from .utils import validate_json
from .validators import string_to_multi_select

if TYPE_CHECKING:
    from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution

TIME_FORMAT: str = "%Y-%m-%dT%H:%M:%S.000Z"


def validate_search_time_period(days: str | int | None) -> int:
    """Validate 'Search Time Period In Days': must be a whole number within bounds."""
    if days is None or str(days).strip() == "":
        return MIN_SEARCH_TIME_PERIOD_DAYS
    try:
        days = int(str(days).strip())
    except (TypeError, ValueError):
        raise ValueError(
            f"'Search Time Period In Days' must be a whole number. Received: {days}."
        )
    if days > MAX_SEARCH_TIME_PERIOD_DAYS:
        raise ValueError(
            f"'Search Time Period In Days' cannot exceed {MAX_SEARCH_TIME_PERIOD_DAYS} days. "
            f"Received: {days}."
        )
    if days < MIN_SEARCH_TIME_PERIOD_DAYS:
        raise ValueError(
            f"'Search Time Period In Days' cannot be negative. Received: {days}."
        )
    return days


def validate_service_account_json(raw_value: str | None) -> str | None:
    """Validate 'Service Account JSON': a JSON object carrying RSC credentials.

    Checked before any other work so a malformed or partial credential fails with
    a message naming the parameter, rather than surfacing later as a connection
    error from the API layer.

    Returns:
        The raw value, unchanged, ready to hand to APIManager.

    Raises:
        ValueError: If the value is not valid JSON or omits a required field.
    """
    service_account = validate_json(raw_value, "Service Account JSON", is_mandatory=True)
    missing = [key for key in SERVICE_ACCOUNT_REQUIRED_KEYS if not service_account.get(key)]
    if missing:
        raise ValueError(ERROR_SERVICE_ACCOUNT_MISSING_KEYS.format(", ".join(missing)))
    return raw_value


def _checkpoint_identity(siemplify: SiemplifyConnectorExecution) -> tuple[int, str]:
    """(context_type, identifier) addressing this connector's server-side context.

    context_type 4 is SiemplifyConnectorExecution.CONTEXT_TYPE; the identifier is
    the connector instance's own id, so two instances of this connector keep
    independent checkpoints.
    """
    return (
        getattr(siemplify, "CONTEXT_TYPE", 4),
        siemplify.context.connector_info.identifier,
    )


def read_checkpoint(siemplify: SiemplifyConnectorExecution) -> dict[str, str]:
    """Read the {from_timestamp} checkpoint. Returns {} if none has been saved.

    Held in the SOAR server's context store, NOT on disk. A Remote connector runs
    in a fresh pod with a clean filesystem, so anything written locally is gone by
    the next run: the window is re-swept every time, the same alerts are re-emitted
    and overflow protection trips.

    get_context_property_from_server is used in preference to the plain
    get_context_property / fetch_timestamp wrappers because those branch on the
    deployment mode:

        if (not is_remote_publisher_sdk) or is_locally_scheduled_remote_connector:
            -> server DB
        else:
            -> <RUN_FOLDER>/context_file.json      # still the pod's local disk

    A remote agent connector that is not locally scheduled takes that second path,
    which is the very failure being fixed. The *_from_server / *_in_server variants
    skip the branch and always talk to the server, so one code path is correct in
    all three deployment modes. See _read_raw_checkpoint for the fallback.
    """
    raw = _read_raw_checkpoint(siemplify)

    last_run_unix_ms = _coerce_unix_ms(raw)
    if not last_run_unix_ms:
        return {}

    from_timestamp = datetime.fromtimestamp(
        last_run_unix_ms / 1000, tz=timezone.utc
    ).strftime(TIME_FORMAT)
    return {"from_timestamp": from_timestamp}


def _read_raw_checkpoint(siemplify: SiemplifyConnectorExecution) -> Any:
    """Fetch the stored checkpoint value as-is from the server context store.

    Falls back to the branching wrapper if the direct server call fails, so a mode
    where the session cannot reach the API degrades to today's behaviour instead of
    failing the run outright -- logged as an error, because that degraded state
    silently re-ingests.
    """
    context_type, identifier = _checkpoint_identity(siemplify)
    try:
        raw = siemplify.get_context_property_from_server(
            context_type, identifier, siemplify.TIMESTAMP_KEY
        )
    except Exception as err:
        siemplify.LOGGER.error(
            f"Could not read the checkpoint from the server context store ({err}). "
            "Falling back to the SDK's mode-dependent store, which on a Remote "
            "agent is pod-local and will cause the window to be re-ingested."
        )
        raw = None
        try:
            raw = siemplify.fetch_timestamp() or None
        except Exception as fallback_err:
            siemplify.LOGGER.error(f"Fallback checkpoint read also failed: {fallback_err}")
    return raw


def _coerce_unix_ms(raw: Any) -> int:
    """Normalise whatever the context store returns into unix milliseconds.

    The value is written with json.dumps, so it comes back as the string "1756…"
    rather than an int, and a 204 from the server surfaces as None. Anything
    unparseable is treated as "no checkpoint" rather than raising, since a corrupt
    value should cost one re-swept window, not every subsequent run.
    """
    if raw in (None, "", 0):
        return 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        pass
    try:
        return int(json.loads(raw))
    except Exception:
        return 0


def write_checkpoint(siemplify: SiemplifyConnectorExecution, from_timestamp: str) -> None:
    """Persist the from_timestamp the next run should start from.

    Written straight to the server context store for the reason set out in
    read_checkpoint. Encoded with json.dumps to match what the SDK's own
    save_timestamp writes, so the two remain interchangeable.
    """
    parsed = datetime.strptime(from_timestamp, TIME_FORMAT).replace(tzinfo=timezone.utc)
    unix_ms = int(parsed.timestamp() * 1000)
    context_type, identifier = _checkpoint_identity(siemplify)

    try:
        siemplify.set_context_property_in_server(
            context_type, identifier, siemplify.TIMESTAMP_KEY, json.dumps(unix_ms)
        )
    except Exception as err:
        siemplify.LOGGER.error(
            f"Could not write the checkpoint to the server context store ({err}). "
            "Falling back to the SDK's mode-dependent store."
        )
        siemplify.save_timestamp(new_timestamp=unix_ms)

    siemplify.LOGGER.info(f"Checkpoint updated: from_timestamp set to '{from_timestamp}'.")


def extract_multi_select_param(
    siemplify: SiemplifyConnectorExecution,
    param_name: str,
    enum_map: dict[str, str],
) -> list[str] | None:
    """Extract a multi-select connector parameter and map its labels to API enums.

    Connector parameters have no dropdown type, so the values arrive as a
    comma-separated (or JSON array) string of the labels documented in the
    parameter description. string_to_multi_select handles both forms and rejects
    unknown labels.

    Returns:
        List of mapped API enum values, or None when the parameter is empty.
    """
    raw = extract_connector_param(
        siemplify,
        param_name=param_name,
        input_type=str,
        is_mandatory=False,
        default_value=None,
        print_value=True,
    )
    return string_to_multi_select(raw, enum_map, param_name)
