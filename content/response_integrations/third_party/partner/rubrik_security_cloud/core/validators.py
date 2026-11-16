"""Parameter parsing and validation helpers for the DSPM / IR actions and connector."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .constants import (
    DEFAULT_IR_POLICY_TYPES,
    DEFAULT_MAX_RESULTS,
    DSPM_CATEGORY_MAP,
    DSPM_OBJECT_TYPE_ENUM_MAP,
    DSPM_SEVERITY_MAP,
    DSPM_SORT_BY_MAP,
    ERROR_INVALID_ENUM,
    FILE_ACCESS_VIA_MAP,
    FILE_EXPOSURE_MAP,
    FILE_RISK_LEVEL_MAP,
    FILE_SORT_BY_MAP,
    IR_CATEGORY_MAP,
    IR_IDENTITY_PROVIDER_ENUM_MAP,
    IR_IDENTITY_TAG_ENUM_MAP,
    IR_POLICY_TYPE_MAP,
    IR_SORT_BY_MAP,
    MAX_VIOLATIONS,
    SENSITIVITY_LEVEL_MAP,
    SORT_ORDER_MAP,
    STATUS_ENUM_MAP,
)
from .rubrik_exceptions import (
    InvalidIntegerException,
    InvalidValueException,
)
from .violations_api import DateRange

if TYPE_CHECKING:
    from soar_sdk.SiemplifyAction import SiemplifyAction
    from TIPCommon.types import SingleJson


def parse_optional_datetime_param(
    value: Optional[str], param_name: str = "parameter"
) -> Optional[str]:
    """Validate and return an optional datetime string parameter.

    Args:
        value: Raw datetime string value, coming from the action parameter.
        param_name: Parameter name used in error messages.

    Returns:
        The datetime string, or None if empty.
    """
    if not value or not value.strip():
        return None
    return value.strip()


def clean_none_values(d: Dict[str, Any]) -> Dict[str, Any]:
    """Remove keys with None values from a dictionary."""
    return {k: v for k, v in d.items() if v is not None}


def format_authentication_failure_message(error: Exception) -> str:
    """Build the standard 'Authentication failed: <detail>' case wall message.

    Shared across actions so every action surfaces auth failures identically.
    """
    return f"Authentication failed: {error}"


def format_graphql_error_message(message_prefix: str, error: Exception) -> str:
    """Build a '<prefix>: GraphQL errors: <detail>' case wall message.

    The ": GraphQL errors: <detail>" suffix is shared across every action's TDD spec;
    the prefix wording varies per action (e.g. "API error during Search DSPM
    Violations" vs. "Failed to update DSPM violation status"), so callers pass the
    full prefix rather than just an action name.
    """
    return f"{message_prefix}: GraphQL errors: {error}"


def _normalize_enum_label(value: Any) -> str:
    """Normalize a hand-typed enum label: trim ends, collapse inner whitespace runs."""
    return " ".join(str(value).split())


def resolve_enum_label(value: Any, enum_map: Dict[str, str], param_name: str) -> str:
    """Resolve one human-readable label to its API enum value.

    Connector parameters have no multi-select input type in SecOps, so their
    values are typed by hand as comma-separated text. Matching is therefore
    tolerant of casing and of stray whitespace ("in  progress" resolves the same
    as "In Progress"), but stays restricted to the labels documented in the
    parameter description -- anything else is rejected, naming the parameter and
    listing what is accepted.

    Args:
        value: A single label, as typed.
        enum_map: Mapping of documented labels to API enum values.
        param_name: Parameter name used in the error message.

    Returns:
        The mapped API enum value.

    Raises:
        InvalidValueException: If the value is not one of the documented labels.
    """
    lookup = {_normalize_enum_label(label).lower(): label for label in enum_map}
    matched_label = lookup.get(_normalize_enum_label(value).lower())
    if matched_label is None:
        raise InvalidValueException(
            ERROR_INVALID_ENUM.format(value, param_name, ", ".join(enum_map.keys()))
        )
    return enum_map[matched_label]


def string_to_multi_select(
    items_str: Optional[str], enum_map: Dict[str, str], param_name: str
) -> Optional[List[str]]:
    """Convert a multi-select parameter value to a list of mapped enum values.

    Accepts either a JSON array string (e.g. '["Low", "High"]') or a
    comma-separated string, since action dropdowns deliver the former while
    connector parameters -- which have no dropdown type -- are typed by hand as
    the latter. Labels are matched case-insensitively via resolve_enum_label,
    and repeated selections collapse to one API value.

    Args:
        items_str: JSON array or comma-separated string of human-readable labels.
        enum_map: Mapping of human-readable labels to API enum values.
        param_name: Parameter name used in error messages.

    Returns:
        List of mapped API enum values, or None if items_str is empty.

    Raises:
        InvalidValueException: If any label is not a valid key in enum_map.
    """
    if not items_str or not items_str.strip():
        return None

    labels = None
    try:
        parsed = json.loads(items_str)
        if isinstance(parsed, list):
            labels = [str(item).strip() for item in parsed if str(item).strip()]
    except (json.JSONDecodeError, TypeError):
        pass
    if labels is None:
        labels = [item.strip() for item in items_str.split(",") if item.strip()]

    mapped_values: List[str] = []
    for label in labels:
        mapped = resolve_enum_label(label, enum_map, param_name)
        if mapped not in mapped_values:
            mapped_values.append(mapped)
    return mapped_values or None


def map_enum_values(
    value: Optional[str],
    enum_map: Dict[str, str],
    param_name: str,
    default: Optional[str] = None,
) -> Optional[str]:
    """Map a single human-readable label to its API enum value.

    Args:
        value: Human-readable label to map.
        enum_map: Mapping of human-readable labels to API enum values.
        param_name: Parameter name used in error messages.
        default: Value to return when value is empty (already an API enum value).

    Returns:
        The mapped API enum value, or default if value is empty.

    Raises:
        InvalidValueException: If value is not a valid key in enum_map.
    """
    if not value or not value.strip():
        return default

    return resolve_enum_label(value, enum_map, param_name)


# ---------------------------------------------------------------------------
# Parameter parsing helpers used by action scripts
# ---------------------------------------------------------------------------

def parse_status_param(siemplify: SiemplifyAction, param_name: str = "Status") -> Optional[List[str]]:
    """Extract and map the Status multi-select parameter."""
    raw = siemplify.extract_action_param(
        param_name=param_name, input_type=str, is_mandatory=False, print_value=True
    )
    return string_to_multi_select(raw, STATUS_ENUM_MAP, param_name)


def parse_dspm_severity_param(siemplify: SiemplifyAction) -> Optional[List[str]]:
    """Extract and map the Severity multi-select parameter for DSPM."""
    raw = siemplify.extract_action_param(
        param_name="Severity", input_type=str, is_mandatory=False, print_value=True
    )
    return string_to_multi_select(raw, DSPM_SEVERITY_MAP, "Severity")


def parse_dspm_category_param(siemplify: SiemplifyAction) -> Optional[List[str]]:
    """Extract and map the Category multi-select parameter for DSPM."""
    raw = siemplify.extract_action_param(
        param_name="Category", input_type=str, is_mandatory=False, print_value=True
    )
    return string_to_multi_select(raw, DSPM_CATEGORY_MAP, "Category")


def parse_sensitivity_level_param(siemplify: SiemplifyAction) -> Optional[List[str]]:
    """Extract and map the Sensitivity Level multi-select parameter for DSPM violations."""
    raw = siemplify.extract_action_param(
        param_name="Sensitivity Level", input_type=str, is_mandatory=False, print_value=True
    )
    return string_to_multi_select(raw, SENSITIVITY_LEVEL_MAP, "Sensitivity Level")


def parse_dspm_object_type_param(siemplify: SiemplifyAction) -> Optional[List[str]]:
    """Extract and validate the Object Type multi-select parameter for DSPM violations."""
    raw = siemplify.extract_action_param(
        param_name="Object Type", input_type=str, is_mandatory=False, print_value=True
    )
    return string_to_multi_select(raw, DSPM_OBJECT_TYPE_ENUM_MAP, "Object Type")


def parse_dspm_sort_by_param(siemplify: SiemplifyAction, default: str = "SORT_DETECTION_TIME") -> str:
    """Extract and map the Sort By parameter for DSPM violations."""
    raw = siemplify.extract_action_param(
        param_name="Sort By", input_type=str, is_mandatory=False, print_value=True
    )
    return map_enum_values(raw, DSPM_SORT_BY_MAP, "Sort By", default=default)


def parse_ir_sort_by_param(siemplify: SiemplifyAction, default: str = "SORT_DETECTION_TIME") -> str:
    """Extract and map the Sort By parameter for IR violations."""
    raw = siemplify.extract_action_param(
        param_name="Sort By", input_type=str, is_mandatory=False, print_value=True
    )
    return map_enum_values(raw, IR_SORT_BY_MAP, "Sort By", default=default)


def parse_sort_order_param(siemplify: SiemplifyAction, default: str = "DESC") -> str:
    """Extract and map the Sort Order parameter."""
    raw = siemplify.extract_action_param(
        param_name="Sort Order", input_type=str, is_mandatory=False, print_value=True
    )
    return map_enum_values(raw, SORT_ORDER_MAP, "Sort Order", default=default)


def map_ir_policy_types(raw: Optional[str], param_name: str = "Policy Types") -> List[str]:
    """Map a raw IR policy types parameter value to its API enum values.

    Falls back to the documented default (Identity, IDP) when the value is empty,
    so an unselected multi-select behaves as documented instead of failing.

    Robust against every form the platform may deliver the multi-select value in —
    a proper JSON array (["Identity", "IDP"]), a single comma-joined chip
    (["Identity, IDP"]), a plain comma-separated string (Identity, IDP), or an
    unparseable raw default that gets naively comma-split into bracket/quote fragments
    (e.g. '["Identity"' and '"IDP"]'). Policy-type labels never contain commas or
    brackets, so flattening on commas and stripping stray [ ] " ' characters is always
    safe for this parameter.

    Args:
        raw: Raw parameter value, as delivered by the platform.
        param_name: Parameter name used in error messages (differs between the
            actions' "Policy Types" and the connector's "IR Violation Policy Types").

    Returns:
        List of mapped API enum values, never empty.

    Raises:
        InvalidValueException: If any label is not a valid IR policy type.
    """
    if not raw or not raw.strip():
        return list(DEFAULT_IR_POLICY_TYPES)

    try:
        parsed = json.loads(raw)
        items = parsed if isinstance(parsed, list) else [parsed]
    except (json.JSONDecodeError, TypeError):
        items = [raw]

    labels: List[str] = []
    for item in items:
        for part in str(item).split(","):
            cleaned = part.strip().strip("[]\"'").strip()
            if cleaned:
                labels.append(cleaned)

    mapped: List[str] = []
    for label in labels:
        policy_type = resolve_enum_label(label, IR_POLICY_TYPE_MAP, param_name)
        if policy_type not in mapped:
            mapped.append(policy_type)

    return mapped or list(DEFAULT_IR_POLICY_TYPES)


def parse_ir_policy_types_param(siemplify: SiemplifyAction) -> List[str]:
    """Extract and map the Policy Types multi-select parameter for IR actions.

    Extracted as non-mandatory so an empty/unselected value falls back to the
    documented default (Identity, IDP) instead of raising a raw "mandatory parameter
    missing" error — the TDD marks Policy Types required but ships a default selection.
    """
    raw = siemplify.extract_action_param(
        param_name="Policy Types", input_type=str, is_mandatory=False, print_value=True
    )
    return map_ir_policy_types(raw)


def parse_ir_category_param(siemplify: SiemplifyAction) -> Optional[List[str]]:
    """Extract and map the Category multi-select parameter for IR violations."""
    raw = siemplify.extract_action_param(
        param_name="Category", input_type=str, is_mandatory=False, print_value=True
    )
    return string_to_multi_select(raw, IR_CATEGORY_MAP, "Category")


def parse_ir_identity_provider_param(siemplify: SiemplifyAction) -> Optional[List[str]]:
    """Extract and map the Identity Provider multi-select parameter for IR violations."""
    raw = siemplify.extract_action_param(
        param_name="Identity Provider", input_type=str, is_mandatory=False, print_value=True
    )
    return string_to_multi_select(raw, IR_IDENTITY_PROVIDER_ENUM_MAP, "Identity Provider")


def parse_ir_identity_tag_param(siemplify: SiemplifyAction) -> Optional[List[str]]:
    """Extract and map the Identity Tag multi-select parameter for IR violations."""
    raw = siemplify.extract_action_param(
        param_name="Identity Tag", input_type=str, is_mandatory=False, print_value=True
    )
    return string_to_multi_select(raw, IR_IDENTITY_TAG_ENUM_MAP, "Identity Tag")


def parse_file_risk_level_param(siemplify: SiemplifyAction) -> Optional[List[str]]:
    """Extract and map the Risk Level multi-select for file list."""
    raw = siemplify.extract_action_param(
        param_name="Risk Level", input_type=str, is_mandatory=False, print_value=True
    )
    return string_to_multi_select(raw, FILE_RISK_LEVEL_MAP, "Risk Level")


def parse_file_exposure_param(siemplify: SiemplifyAction) -> Optional[List[str]]:
    """Extract and map the Exposure multi-select for file list."""
    raw = siemplify.extract_action_param(
        param_name="Exposure", input_type=str, is_mandatory=False, print_value=True
    )
    return string_to_multi_select(raw, FILE_EXPOSURE_MAP, "Exposure")


def parse_file_access_via_param(siemplify: SiemplifyAction, default: str = "ACCESS_TYPE_UNSPECIFIED") -> str:
    """Extract and map the Access Via parameter for file list."""
    raw = siemplify.extract_action_param(
        param_name="Access Via", input_type=str, is_mandatory=False, print_value=True
    )
    return map_enum_values(raw, FILE_ACCESS_VIA_MAP, "Access Via", default=default)


def parse_file_sort_by_param(siemplify: SiemplifyAction, default: str = "HITS") -> str:
    """Extract and map the Sort By parameter for file list."""
    raw = siemplify.extract_action_param(
        param_name="Sort By", input_type=str, is_mandatory=False, print_value=True
    )
    return map_enum_values(raw, FILE_SORT_BY_MAP, "Sort By", default=default)


def validate_max_results(
    value: Optional[str],
    default: int = DEFAULT_MAX_RESULTS,
    max_allowed: int = MAX_VIOLATIONS,
    param_name: str = "Max Results",
) -> int:
    """
    Validate and return max_results as an integer within bounds.

    Produces the exact wording required across the TDD's Case Wall Output
    Message tables (e.g. Search DSPM Violations, Get Violation File List):
    "{param_name} must be an integer. Got: <value>", "{param_name} must be
    at least 1.", "{param_name} cannot exceed {max_allowed}. Got: <value>".

    Args:
        value: Raw string from action parameter.
        default: Default value when value is empty.
        max_allowed: Upper bound.
        param_name: Parameter name used in error messages.

    Returns:
        Validated integer.

    Raises:
        InvalidIntegerException: If value is present but invalid.
    """
    if value is None or not str(value).strip():
        return default

    raw_value = str(value).strip()
    try:
        int_value = int(raw_value)
    except ValueError:
        raise InvalidIntegerException(f"{param_name} must be an integer. Got: {raw_value}")

    if int_value < 1:
        raise InvalidIntegerException(f"{param_name} must be at least 1.")
    if int_value > max_allowed:
        raise InvalidIntegerException(
            f"{param_name} cannot exceed {max_allowed}. Got: {raw_value}"
        )

    return int_value


def validate_iso_datetime(value: Optional[str], param_name: str) -> Optional[str]:
    """Validate a date parameter against the single supported format: YYYY-MM-DDTHH:MM:SSZ.

    Shared across actions so every date-range filter enforces the same format.

    Raises:
        InvalidValueException: If the value is non-empty and does not match the
            required format.
    """
    if value is None or not str(value).strip():
        return None

    value = str(value).strip()
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise InvalidValueException(
            f"{param_name} must be in YYYY-MM-DDTHH:MM:SSZ format. Received: {value}"
        )
    return value


def validate_date_pair_required(
    start_value: Optional[str], end_value: Optional[str], start_label: str, end_label: str
) -> None:
    """Ensure a date-range pair is either both provided or both empty.

    Raises:
        InvalidValueException: If exactly one of start_value/end_value is provided.
    """
    if bool(start_value) != bool(end_value):
        raise InvalidValueException(
            f"Both {start_label} and {end_label} must be provided together."
        )


def validate_date_order(start_value: Optional[str], end_value: Optional[str], error_message: str) -> None:
    """Ensure end_value is chronologically after start_value, when both are present.

    Assumes both values (if present) already match the YYYY-MM-DDTHH:MM:SSZ
    format enforced by validate_iso_datetime.

    Raises:
        InvalidValueException: If end_value is not strictly after start_value.
    """
    if not start_value or not end_value:
        return

    start_dt = datetime.strptime(start_value, "%Y-%m-%dT%H:%M:%SZ")
    end_dt = datetime.strptime(end_value, "%Y-%m-%dT%H:%M:%SZ")
    if end_dt <= start_dt:
        raise InvalidValueException(error_message)


def validate_date_ranges(
    raw_dates: dict[str, str | None],
    range_params: tuple[tuple[str, str, str], ...],
) -> list[DateRange]:
    """Validate every date parameter, then each pair's presence, then each pair's order.

    Args:
        raw_dates: Raw parameter values keyed by parameter name.
        range_params: (start parameter, end parameter, order error message) per range.

    Returns:
        One DateRange per entry in range_params, in the same order.
    """
    dates = {name: validate_iso_datetime(value, name) for name, value in raw_dates.items()}
    for start, end, _ in range_params:
        validate_date_pair_required(dates[start], dates[end], start, end)
    for start, end, order_error in range_params:
        validate_date_order(dates[start], dates[end], order_error)
    return [DateRange(start=dates[start], end=dates[end]) for start, end, _ in range_params]


def parse_connection(connection: SingleJson) -> tuple[list[SingleJson], str | None]:
    """Return a GraphQL connection's nodes and the cursor of the next page, if any."""
    edges: list[SingleJson] = connection.get("edges") or []
    nodes = [edge.get("node", {}) for edge in edges if edge.get("node")]
    page_info: SingleJson = connection.get("pageInfo") or {}
    end_cursor: str | None = page_info.get("endCursor")
    has_next_page: bool = page_info.get("hasNextPage", False)
    return nodes, end_cursor if has_next_page and end_cursor else None
