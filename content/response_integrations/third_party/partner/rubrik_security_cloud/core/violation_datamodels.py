"""Data models for DSPM / Identity Resilience violations and connector alerts."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple
from urllib.parse import quote

from .constants import (
    ACTIONS_LOG_DOWNLOAD_MESSAGE_PREFIX,
    ALERT_NAME_CLASSIFICATION_TEMPLATE,
    ALERT_NAME_IDENTITY_EVENT_TEMPLATE,
    ALERT_NAME_VIOLATION_TEMPLATE,
    CLASSIFICATION_ACTIVITY_MESSAGE_FILTER,
    CLASSIFICATION_ALERT_EVENT_NAME,
    RUBRIK_SEVERITY_MAP,
    UNKNOWN_LABEL,
)

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

DEVICE_VENDOR = "Rubrik Security Cloud"
DEVICE_PRODUCT = "RSC"

# The snapshot time inside a classification activity message, e.g.
# "... on the snapshot at Friday 19-Jun-26 20:01 UTC." Tried in order: the text
# following "snapshot at", then a bare weekday-prefixed timestamp anywhere in
# the message.
_SNAPSHOT_AT_PATTERN = re.compile(r"snapshot\s+at\s+(?P<time>[^.]+)", re.IGNORECASE)
_SNAPSHOT_TIME_PATTERN = re.compile(
    r"(?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day\s+\d{1,2}-[A-Za-z]{3}-\d{2,4}"
    r"\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s+[A-Za-z]{2,5})?"
)

# The violation severity an RSC violation activity message leads with, e.g.
# "Low severity violation of policy '...' detected on '...'". The series' own
# severity field describes the activity (reported as "Info" even for a Low or
# Critical violation), so the message is the only place the severity that
# matters for triage appears.
_MESSAGE_SEVERITY_PATTERN = re.compile(r"^\s*(?P<severity>[A-Za-z]+)\s+severity\b")

# Severity and policy name are only available inside the activity message, which
# RSC rewords for every lifecycle transition:
#   "<Severity> severity violation of policy 'P' detected on 'X'"
#   "<Severity> severity violation of policy 'P' on 'X' was remediated"
#   "<Severity> severity violation of policy 'P' on 'X' changed status to in progress"
# and, for identity events, without the severity prefix:
#   "'Member was added to a privileged group' detected on 'fuji.us'"
# These patterns pull the severity and policy back out; the alert's target comes
# from the series' own objectName field, not from the message.
#
# Everything after the message's own "on '<target>'" clause is matched by .* and
# discarded, rather than enumerating RSC's transition wordings ("was remediated",
# "changed status to in progress", ...) -- that list is not knowable up front, and
# an unlisted wording would fail the match and leak the raw message into the
# alert name.
#
# The message's target is matched but deliberately not captured: it is not always
# the series object (an identity violation on directory 'rubrik.us' names the
# specific identity 'Law Murphy' on transition), so using it would make the name
# shift between transitions.
#
# The policy group is greedy, NOT non-greedy: policy names contain apostrophes
# ("Privileged users that don't require a password"), which a non-greedy match
# would truncate at "don". Greedy backtracks to the rightmost valid
# "' [detected] on '<target>'" split, which is the correct delimiter.
_ACTIVITY_VIOLATION_MESSAGE_PATTERN = re.compile(
    r"^\s*(?P<severity>[A-Za-z]+)\s+severity\s+violation\s+of\s+policy\s+"
    r"'(?P<policy>.+)'(?:\s+detected)?\s+on\s+'[^']+'.*$"
)
_ACTIVITY_EVENT_MESSAGE_PATTERN = re.compile(
    r"^\s*'(?P<policy>.+)'(?:\s+detected)?\s+on\s+'[^']+'.*$"
)


def _iso_to_unix_ms(iso_str: str) -> int:
    """Convert ISO 8601 timestamp to Unix epoch milliseconds (AlertInfo requirement)."""
    if not iso_str:
        return 0
    try:
        return int(datetime.fromisoformat(iso_str.replace("Z", "+00:00")).timestamp() * 1000)
    except Exception:
        return 0


def _stringify(value: Any) -> str:
    """Convert any value to a string suitable for CSV / event display."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value)
    except TypeError:
        return str(value)


def _flatten_payload(payload: Any, prefix: str = "") -> Dict[str, Any]:
    """Flatten a nested API payload into scalar event fields.

    Lets an alert carry everything RSC returned instead of a hand-picked subset.
    Nested keys are joined with "_", following the convention
    SiemplifyUtils.dict_to_flat uses, so the fields look native in SOAR:

        {"policy": {"policyType": "POLICY_TYPE_IDENTITY"}}
            -> {"policy_policyType": "POLICY_TYPE_IDENTITY"}

    Lists of objects are indexed, so their inner fields stay addressable for
    playbook conditions, while lists of scalars collapse to one JSON string —
    'PRIVILEGED, AT_RISK' style values are far easier to match on as a single
    field than as identityTags_0 / identityTags_1:

        {"remediations": [{"state": "NEW"}]} -> {"remediations_0_state": "NEW"}
        {"identityTags": ["PRIVILEGED"]}     -> {"identityTags": '["PRIVILEGED"]'}

    None and empty containers become empty strings, so a field RSC returned as
    null is still visible in the alert rather than silently missing.
    """
    flat: Dict[str, Any] = {}

    if isinstance(payload, dict):
        if not payload and prefix:
            flat[prefix] = ""
        for key, value in payload.items():
            child_prefix = f"{prefix}_{key}" if prefix else str(key)
            flat.update(_flatten_payload(value, child_prefix))
    elif isinstance(payload, list):
        if any(isinstance(item, (dict, list)) for item in payload):
            for index, item in enumerate(payload):
                flat.update(_flatten_payload(item, f"{prefix}_{index}"))
        elif prefix:
            flat[prefix] = _stringify(payload)
    elif prefix:
        flat[prefix] = "" if payload is None else payload

    return flat


def _first_non_empty(*values: Any) -> str:
    """Return the first value that is a non-blank string, else UNKNOWN_LABEL."""
    for value in values:
        if value and str(value).strip():
            return str(value).strip()
    return UNKNOWN_LABEL


def _extract_snapshot_time(*messages: Optional[str]) -> str:
    """Trim the snapshot timestamp out of classification activity messages.

    RSC reports the snapshot inline, e.g. "Data security violations found for
    workload 'ran test' on the snapshot at Friday 19-Jun-26 20:01 UTC. Results
    available in the Objects page ...". Each message is tried in order, and for
    each the text after "snapshot at" is preferred over a bare weekday-prefixed
    timestamp found anywhere in it.

    Returns:
        The trimmed timestamp, or "" if no message carries one.
    """
    for message in messages:
        if not message:
            continue
        match = _SNAPSHOT_AT_PATTERN.search(message)
        if match:
            return match.group("time").strip()
        match = _SNAPSHOT_TIME_PATTERN.search(message)
        if match:
            return match.group(0).strip()
    return ""


def _extract_message_severity(message: Optional[str]) -> str:
    """Pull the leading '<Severity> severity ...' word out of an activity message.

    Returns "" when the message does not start that way (e.g. a classification
    message, or an identity-event message that carries no severity prefix).
    """
    match = _MESSAGE_SEVERITY_PATTERN.match(message or "")
    return match.group("severity") if match else ""


def _build_violation_alert_name(message: Optional[str], object_name: Optional[str]) -> str:
    """Build a DSPM / IR alert name from the activity message and the series object.

    Composes "<Severity> severity violation of policy '<P>' detected on
    '<objectName>'", taking severity and policy name from the message (the only
    place activitySeriesConnection exposes them) and the target from the series'
    own objectName field.

    Both halves matter for keeping the name stable across a violation's
    lifecycle. RSC rewords the message on each transition -- "... detected on
    'X'" when raised, "... on 'X' was remediated" when closed out -- and can name
    a different target in the process, so neither the wording nor the message's
    target can be used as-is. severity and policy, by contrast, are unchanged
    across transitions, and objectName is a series-level field.

    The transition itself is not lost: the raw message stays on the event as
    activityMessage.

    Returns:
        The composed name, or the message unchanged if it matches neither known
        shape (so an unrecognised message is still surfaced, not blanked).
    """
    message = (message or "").strip()
    target = _first_non_empty(object_name)

    match = _ACTIVITY_VIOLATION_MESSAGE_PATTERN.match(message)
    if match:
        return ALERT_NAME_VIOLATION_TEMPLATE.format(
            severity=match.group("severity").strip().title(),
            policy_name=match.group("policy"),
            target=target,
        )

    # Identity events carry no severity prefix, only a quoted policy name.
    match = _ACTIVITY_EVENT_MESSAGE_PATTERN.match(message)
    if match:
        return ALERT_NAME_IDENTITY_EVENT_TEMPLATE.format(
            policy_name=match.group("policy"),
            target=target,
        )

    return message


def _hierarchy_fields(hierarchy_object: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Event fields from the SnappableIdentity lookup for a series' objectId.

    Prefixed with `hierarchy_` rather than merged flat: the payload's id, name and
    objectType would otherwise overwrite the activity series' own fields of those
    names, which describe the series rather than the tenant object.

    The shape is type-dependent -- an O365Site adds title/url, an O365Onedrive adds
    userPrincipalName/userName/userID, anything else returns only the three common
    fields -- so whatever RSC sent is flattened as-is instead of being mapped field
    by field. Returns {} when the lookup produced nothing, leaving the event
    unchanged rather than adding blank keys.

    One derived field is added: hierarchy_userPrincipalName_encoded, the UPN
    percent-encoded for use in a URL. A playbook that drops the raw value into a
    Graph or SharePoint URL breaks on the "@"
    ("AlexW@txfnw.onmicrosoft.com" -> "AlexW%40txfnw.onmicrosoft.com"), and doing
    it here means every playbook gets it right instead of each one re-implementing
    the escape. safe="" so nothing is left unencoded; "." and "-" are never
    escaped by quote(), which is why the domain part is unchanged.
    """
    if not hierarchy_object:
        return {}

    fields = _flatten_payload(hierarchy_object, prefix="hierarchy")

    # Only present on object types that carry a UPN (O365Onedrive), so the field is
    # added conditionally rather than as an empty string on every other type.
    user_principal_name = fields.get("hierarchy_userPrincipalName")
    if user_principal_name:
        fields["hierarchy_userPrincipalName_encoded"] = quote(
            str(user_principal_name), safe=""
        )

    return fields


class BaseModel:
    """Base model for all Rubrik datamodels."""

    def __init__(self, raw_data: Dict[str, Any]) -> None:
        self.raw_data = raw_data

    def to_json(self) -> Dict[str, Any]:
        """Return the raw data dict."""
        return self.raw_data

    @staticmethod
    def _stringify(value: Any) -> str:
        """Convert any value to a string suitable for CSV display."""
        return _stringify(value)


class DSPMViolation(BaseModel):
    """Model for a single DSPM violation from the list query."""

    def __init__(self, raw_data: Dict[str, Any]) -> None:
        super().__init__(raw_data)
        self.violation_id: str = raw_data.get("policyViolationId", "")
        self.status: str = raw_data.get("status", "")
        self.created_at: str = raw_data.get("createdAt", "")
        self.last_updated_at: str = raw_data.get("lastUpdatedAt", "")
        self.severity: str = raw_data.get("violationSeverity", "")
        policy = raw_data.get("policy") or {}
        self.policy_name: str = policy.get("name", "")
        self.policy_category: str = policy.get("policyCategory", "")
        self.policy_severity: str = policy.get("policySeverity", "")
        self.resource_id: str = raw_data.get("resourceId", "")
        metadata = (raw_data.get("resourceMetadata") or {}).get("metadata") or {}
        self.object_name: str = metadata.get("name", "")
        self.object_type: str = metadata.get("objectType", "")
        details = raw_data.get("details") or {}
        self.snapshot_id: str = details.get("snapshotId", "")

    def to_csv(self) -> Dict[str, Any]:
        """Return a flat dict suitable for SOAR data table display."""
        return {
            "Violation ID": self.violation_id,
            "Status": self.status,
            "Severity": self.severity,
            "Policy Name": self.policy_name,
            "Category": self.policy_category,
            "Resource Name": self.object_name,
            "Object Type": self.object_type,
            "Snapshot ID": self.snapshot_id,
            "Detected At": self.created_at,
            "Last Updated": self.last_updated_at,
        }


class DSPMViolationDetails(BaseModel):
    """Model for the full details of a single DSPM violation."""

    def __init__(self, raw_data: Dict[str, Any]) -> None:
        super().__init__(raw_data)
        self.violation_id: str = raw_data.get("policyViolationId", "")
        self.status: str = raw_data.get("status", "")
        self.severity: str = raw_data.get("violationSeverity", "")
        self.resource_id: str = raw_data.get("resourceId", "")
        policy = raw_data.get("policy") or {}
        self.policy_name: str = policy.get("name", "")
        self.policy_category: str = policy.get("policyCategory", "")
        details = raw_data.get("details") or {}
        self.snapshot_id: str = details.get("snapshotId", "")
        self.total_sensitive_hits: int = details.get("violatedSensitiveHits", 0) or 0
        metadata = (raw_data.get("resourceMetadata") or {}).get("metadata") or {}
        self.object_type: str = metadata.get("objectType", "")
        self.platform: str = metadata.get("platform", "")
        self.physical_host: str = metadata.get("physicalHost", "")

    def to_csv(self) -> Dict[str, Any]:
        """Return a flat dict suitable for SOAR data table display."""
        return {
            "Violation Id": self.violation_id,
            "Status": self.status,
            "Severity": self.severity,
            "Policy Name": self.policy_name,
            "Policy Category": self.policy_category,
            "Snapshot Id": self.snapshot_id,
            "Resource Id": self.resource_id,
            "Object Type": self.object_type,
            "Platform": self.platform,
            "Physical Host": self.physical_host,
            "Total Sensitive Hits": self.total_sensitive_hits,
        }


class IRViolation(BaseModel):
    """Model for a single IR violation from the list query."""

    def __init__(self, raw_data: Dict[str, Any]) -> None:
        super().__init__(raw_data)
        self.violation_id: str = raw_data.get("policyViolationId", "")
        self.status: str = raw_data.get("status", "")
        self.severity: str = raw_data.get("violationSeverity", "")
        self.created_at: str = raw_data.get("createdAt", "")
        policy = raw_data.get("policy") or {}
        self.policy_name: str = policy.get("name", "")
        self.policy_category: str = policy.get("policyCategory", "")
        metadata = (raw_data.get("resourceMetadata") or {}).get("metadata") or {}
        self.display_name: str = metadata.get("displayName", "")
        self.idp_type: str = metadata.get("idpType", "")
        self.user_principal_name: str = metadata.get("userPrincipalName", "")

    def to_csv(self) -> Dict[str, Any]:
        """Return a flat dict suitable for SOAR data table display."""
        return {
            "Violation ID": self.violation_id,
            "Status": self.status,
            "Severity": self.severity,
            "Policy Name": self.policy_name,
            "Category": self.policy_category,
            "Identity (Display Name)": self.display_name,
            "User Principal Name": self.user_principal_name,
            "IDP Type": self.idp_type,
            "Detected At": self.created_at,
        }


class IRViolationDetails(BaseModel):
    """Model for the full details of a single IR violation."""

    def __init__(self, raw_data: Dict[str, Any]) -> None:
        super().__init__(raw_data)
        self.violation_id: str = raw_data.get("policyViolationId", "")
        self.status: str = raw_data.get("status", "")
        self.severity: str = raw_data.get("violationSeverity", "")
        self.resource_id: str = raw_data.get("resourceId", "")
        self.resource_type: str = raw_data.get("resourceType", "")
        policy = raw_data.get("policy") or {}
        self.policy_name: str = policy.get("name", "")
        self.policy_category: str = policy.get("policyCategory", "")
        self.manual_remediation: str = policy.get("manualRemediationProcess", "")
        metadata = (raw_data.get("resourceMetadata") or {}).get("metadata") or {}
        self.display_name: str = metadata.get("displayName", "")
        self.idp_type: str = metadata.get("idpType", "")
        self.principal_type: str = metadata.get("principalType", "")
        self.user_principal_name: str = metadata.get("userPrincipalName", "")

    def to_csv(self) -> Dict[str, Any]:
        """Return a flat dict suitable for SOAR data table display."""
        return {
            "Violation ID": self.violation_id,
            "Status": self.status,
            "Severity": self.severity,
            "Policy Name": self.policy_name,
            "Policy Category": self.policy_category,
            "Resource ID": self.resource_id,
            "Resource Type": self.resource_type,
            "Display Name": self.display_name,
            "User Principal Name": self.user_principal_name,
            "IDP Type": self.idp_type,
            "Principal Type": self.principal_type,
            "Remediation Guidance": self.manual_remediation,
        }


class FileEntry(BaseModel):
    """Model for a single file entry from the violation file list query."""

    def __init__(self, raw_data: Dict[str, Any]) -> None:
        super().__init__(raw_data)
        self.filename: str = raw_data.get("filename", "")
        self.native_path: str = raw_data.get("nativePath", "")
        self.directory: str = raw_data.get("directory", "")
        self.size: int = raw_data.get("size", 0) or 0
        self.last_modified_time: str = raw_data.get("lastModifiedTime", "")
        self.last_access_time: str = raw_data.get("lastAccessTime", "")
        hits = raw_data.get("hits") or {}
        self.total_hits: int = hits.get("totalHits", 0) or 0
        sensitive_hits = raw_data.get("sensitiveHits") or {}
        high_risk = sensitive_hits.get("highRiskHits") or {}
        self.high_risk_hits: int = high_risk.get("violatedHits", 0) or 0
        medium_risk = sensitive_hits.get("mediumRiskHits") or {}
        self.medium_risk_hits: int = medium_risk.get("violatedHits", 0) or 0
        low_risk = sensitive_hits.get("lowRiskHits") or {}
        self.low_risk_hits: int = low_risk.get("violatedHits", 0) or 0
        self.open_access_type: str = raw_data.get("openAccessType", "")
        self.staleness_type: str = raw_data.get("stalenessType", "")

    def to_csv(self) -> Dict[str, Any]:
        """Return a flat dict suitable for SOAR data table display."""
        return {
            "File Name": self.filename,
            "Path": self.native_path,
            "Directory": self.directory,
            "Size (bytes)": self.size,
            "Last Modified": self.last_modified_time,
            "Last Accessed": self.last_access_time,
            "Total Hits": self.total_hits,
            "High Risk Hits": self.high_risk_hits,
            "Medium Risk Hits": self.medium_risk_hits,
            "Low Risk Hits": self.low_risk_hits,
            "Exposure Type": self.open_access_type,
            "Staleness": self.staleness_type,
        }


class UserFile:
    """Internal model for a file entry from allUserFiles (async polling only)."""

    def __init__(self, raw_data: Dict[str, Any]) -> None:
        self.external_id: Optional[str] = raw_data.get("externalId")
        self.filename: str = raw_data.get("filename", "")
        self.file_type: str = raw_data.get("type", "")
        self.state: str = raw_data.get("state", "")
        self.created_at: str = raw_data.get("createdAt", "")

    def is_ready(self) -> bool:
        return self.state == "READY"

    def is_failed(self) -> bool:
        return self.state == "FAILED"


class RubrikClassificationAlertDatamodel:
    """Data model for Rubrik Classification alerts in connectors."""

    def __init__(
        self,
        event_node: SingleJson,
        policy_obj: SingleJson,
        snapshot_id: str,
        hierarchy_object: Optional[SingleJson] = None,
    ) -> None:
        self.event_node = event_node
        self.policy_obj = policy_obj
        self.snapshot_id = snapshot_id
        # Optional so a failed identity lookup degrades the event rather than
        # dropping the alert.
        self.hierarchy_object = hierarchy_object or {}

    def get_alert_info(
        self,
        alert_info: Any,
        environment_common: Any,
        event_field_parameter: str = "",
        product_field_name: str = "",
    ) -> Any:
        """Convert raw data to Siemplify AlertInfo format."""
        fields = self._series_fields()
        fields.update(self._activity_fields(fields))
        fields.update(self._policy_fields())

        self._set_alert_fields(alert_info, fields, environment_common)
        alert_info.event_field_name = event_field_parameter
        alert_info.source_system_name = product_field_name
        alert_info.event_product = fields["last_activity_type"]

        alert_info.events = [self._build_event(fields)]

        return alert_info

    def _series_fields(self) -> SingleJson:
        """activitySeriesConnection node fields carried onto the alert and event."""
        activity_series_id = self.event_node.get("activitySeriesId") or self.event_node.get(
            "id", ""
        )
        start_time = self.event_node.get("startTime", "")
        return {
            "activity_series_id": activity_series_id,
            "start_time": start_time,
            "last_updated": self.event_node.get("lastUpdated", start_time),
            "object_id": self.event_node.get("objectId", ""),
            "object_name": self.event_node.get("objectName", ""),
            "object_type": self.event_node.get("objectType", ""),
            "cluster_id": (self.event_node.get("cluster") or {}).get("id", ""),
            "cluster_name": (self.event_node.get("cluster") or {}).get("name", ""),
            "severity": self.event_node.get("severity", "Info"),
            "last_activity_type": self.event_node.get("lastActivityType", "Classification"),
            "last_activity_status": self.event_node.get("lastActivityStatus", ""),
            "location": self.event_node.get("location", ""),
            "progress": self.event_node.get("progress", ""),
            "fid": self.event_node.get("fid", ""),
        }

    def _activity_fields(self, series: SingleJson) -> SingleJson:
        """Fields from the selected activityConnection node, plus the alert name."""
        # activityConnection node fields — select the "Results available" node specifically.
        # Falls back to nodes[0] if the expected message is not found.
        activity_nodes = self.event_node.get("activityConnection", {}).get("nodes", [])
        activity_node = next(
            (
                n for n in activity_nodes
                if CLASSIFICATION_ACTIVITY_MESSAGE_FILTER in n.get("message", "")
            ),
            activity_nodes[0] if activity_nodes else {},
        )
        # Field 1 / 8: individual activity node ID used as ticketId and DisplayId
        activity_node_id = activity_node.get("id", series["activity_series_id"])
        # Field 7: message used as Description
        message = activity_node.get("message", "")

        # Field 3 / 5: Name and RuleGenerator. The snapshot time is trimmed out of
        # the selected message; if that message does not carry one, every other
        # activity message is tried before falling back to the event's own
        # lastUpdated timestamp.
        snapshot_time = _extract_snapshot_time(
            message, *(n.get("message") for n in activity_nodes)
        )
        alert_name = ALERT_NAME_CLASSIFICATION_TEMPLATE.format(
            object_name=_first_non_empty(series["object_name"], series["object_id"]),
            snapshot_time=_first_non_empty(snapshot_time, series["last_updated"]),
        )
        return {
            "activity_node_id": activity_node_id,
            "message": message,
            "snapshot_time": snapshot_time,
            "alert_name": alert_name,
        }

    def _policy_fields(self) -> SingleJson:
        """policyObj fields carried onto the event."""
        # policyObj fields
        root = self.policy_obj.get("rootFileResult", {})
        risk_level = self.policy_obj.get("riskLevel", "UNKNOWN")

        analyzer_groups = [
            ag for ag in (root.get("analyzerGroupResults") or [])
            if (ag.get("hits") or {}).get("violations", 0) > 0
        ]
        policies_violated = ", ".join(
            (ag.get("analyzerGroup") or {}).get("name", "") for ag in analyzer_groups
        ) or risk_level
        policies_applied = ", ".join(
            p.get("name", "") for p in (self.policy_obj.get("policySummaries") or [])
        )
        return {
            "violations": root.get("hits", {}).get("violations", 0),
            "total_hits": root.get("hits", {}).get("totalHits", 0),
            "violation_delta": root.get("hits", {}).get("violationsDelta", 0),
            "risk_level": risk_level,
            "share_type": self.policy_obj.get("shareType", ""),
            "os_type": self.policy_obj.get("osType", ""),
            "policies_violated": policies_violated,
            "policies_applied": policies_applied,
        }

    def _set_alert_fields(
        self, alert_info: Any, fields: SingleJson, environment_common: Any
    ) -> None:
        """Set the SecOps alert-level fields, up to and including the grouping key."""
        # Priority from node.severity (Field 10)
        _priority_map = {"Critical": 1, "High": 1, "Warning": 2, "Medium": 2, "Info": 3, "Low": 3}
        priority = _priority_map.get(fields["severity"], 2)
        activity_node_id = fields["activity_node_id"]
        alert_name = fields["alert_name"]
        last_updated = fields["last_updated"]

        # --- AlertInfo fields (SecOps alert-level mapping) ---
        alert_info.ticket_id = activity_node_id                   # Field 1: ticketId (activityConnection.nodes[0].id)
        alert_info.display_id = activity_node_id
        alert_info.name = alert_name                               # Field 3: Name
        alert_info.rule_generator = alert_name                     # Field 5: RuleGenerator
        alert_info.description = fields["message"]                 # Field 7: Description
        alert_info.start_time = _iso_to_unix_ms(last_updated)     # Field 6: StartTime (lastUpdated)
        alert_info.end_time = _iso_to_unix_ms(last_updated)
        alert_info.device_product = "RSC"                              # Field 9: DeviceProduct
        alert_info.device_vendor = "Rubrik Security Cloud"
        alert_info.priority = priority                             # Field 10: Priority
        alert_info.environment = environment_common.get_environment(self.event_node)
        # Grouped by objectId, NOT activitySeriesId: RSC opens a new activity
        # series for every classification scan, so grouping on the series would
        # open a fresh case per snapshot and read as duplicate cases for one
        # workload. objectId is stable for the lifetime of the workload, so every
        # scan result for it lands in the same case. Falls back to the series id
        # if objectId is somehow absent -- an empty grouping identifier would
        # merge unrelated workloads into a single case.
        alert_info.source_grouping_identifier = fields["object_id"]

    def _build_event(self, fields: SingleJson) -> SingleJson:
        """Event dict (SecOps EventsList — entire merged payload, Field 11)."""
        event = {
            # SecOps mapping fields
            "SourceSystemName":   "Rubrik Security Cloud",         # Field 2
            "DeviceVendor":       "Rubrik Security Cloud",         # Field 4
            "Description":        fields["message"],               # Field 7
            "DisplayId":          fields["activity_node_id"],      # Field 8 (activityConnection.nodes[0].id)
            "eventName":          CLASSIFICATION_ALERT_EVENT_NAME,
            "DeviceProduct":      "RSC",                           # Field 9
            "EventProduct":       fields["last_activity_type"],    # Field 12
            # SOAR required time fields
            "StartTime":          _iso_to_unix_ms(fields["last_updated"]),
            "EndTime":            _iso_to_unix_ms(fields["last_updated"]),
            "Name":               fields["alert_name"],            # Field 3
            "snapshotTime":       fields["snapshot_time"],
            # activitySeriesConnection node fields
            "activitySeriesId":   fields["activity_series_id"],
            "fid":                fields["fid"],
            "startTime":          fields["start_time"],
            "lastUpdated":        fields["last_updated"],
            "lastActivityType":   fields["last_activity_type"],
            "lastActivityStatus": fields["last_activity_status"],
            "objectId":           fields["object_id"],
            "objectName":         fields["object_name"],
            "objectType":         fields["object_type"],
            "severity":           fields["severity"],
            "location":           fields["location"],
            "progress":           fields["progress"],
            "clusterId":          fields["cluster_id"],
            "clusterName":        fields["cluster_name"],
            "message":            fields["message"],
            # policyObj fields
            "riskLevel":          fields["risk_level"],
            "violations":         fields["violations"],
            "totalHits":          fields["total_hits"],
            "violationsDelta":    fields["violation_delta"],
            "snapshotId":         self.snapshot_id,
            "shareType":          fields["share_type"],
            "osType":             fields["os_type"],
            "policiesViolated":   fields["policies_violated"],
            "policiesApplied":    fields["policies_applied"],
        }
        event.update(_hierarchy_fields(self.hierarchy_object))
        return event


class RubrikActivityViolationAlertDatamodel:
    """Data model for DSPM / IR violation alerts built from an activitySeries node.

    DSPM (SECURITY_VIOLATION) and IR (IDENTITY_VIOLATION / IDENTITY_ALERTS) series
    share one shape, so a single model covers both; violation_type only records
    which RSC fetch type routed the series here, for playbook branching.

    A series' activityConnection holds one immutable entry per lifecycle
    transition -- "<Severity> severity violation of policy 'P' detected on 'X'",
    then later "... on 'X' was remediated" -- each with its own stable id. The
    latest entry is the violation's current state, and that entry's id is what
    the alert dedups on. This is why activity series replaced policyViolations
    for the connector: RSC's periodic re-evaluation of an unchanged violation
    bumps policyViolations.lastUpdatedAt (raising a fresh alert every hour) but
    mints no new activityConnection entry, so it raises nothing here.

    The alert name is composed from the message's severity and policy plus the
    series' objectName -- see _build_violation_alert_name.

    violation_status is the POLICY_VIOLATION_STATUS_* value the connector looked
    up for this series, and the only thing that lookup contributes: the activity
    series has no status field, and the Close Duplicate Violation Alerts Job
    cannot tell a finished violation from a live one without it. Everything else
    on the policyViolation record restates what the series already carries, so
    the connector passes the status alone rather than the whole record.

    It is optional so an alert is still produced when the lookup fails, in which
    case the event has no `status` at all and the job leaves that violation open
    rather than guessing at its state from the message wording.
    """

    def __init__(
        self,
        event_node: SingleJson,
        violation_type: str,
        violation_status: str = "",
        hierarchy_object: Optional[SingleJson] = None,
        window: Optional[Tuple[str, str]] = None,
    ) -> None:
        self.event_node = event_node or {}
        self.violation_type = violation_type
        self.violation_status = violation_status or ""
        # Resolved for DSPM (SECURITY_VIOLATION) only; IR series identify their
        # subject through the message and resourceMetadata instead.
        self.hierarchy_object = hierarchy_object or {}
        # (from_iso, to_iso) for this run. RSC filters the SERIES by lastUpdated,
        # not its entries, so a series returns its whole activityConnection
        # history -- entries from long before this window included. Kept as unix
        # ms so the comparison does not depend on both sides being formatted
        # identically. None disables the filter.
        self.window_start_ms, self.window_end_ms = (
            (_iso_to_unix_ms(window[0]), _iso_to_unix_ms(window[1])) if window else (0, 0)
        )
        self.activity_nodes = [
            node
            for node in ((self.event_node.get("activityConnection") or {}).get("nodes") or [])
            if node
        ]

    def get_latest_activity_node(self) -> SingleJson:
        """The most recent activityConnection entry, by its own time.

        Sorted explicitly rather than trusting the API's ordering, so the current
        state is picked correctly regardless of which direction RSC returns.

        Two filters are applied before picking "latest".

        1. Entries whose message starts with ACTIONS_LOG_DOWNLOAD_MESSAGE_PREFIX
           are excluded. Downloading the remediation log or snapshot results CSV
           against a violation mints a new, immutable entry on that same activity
           series; left unfiltered, that entry becomes the pick here, changes the
           dedup id in get_alert_info, and raises a fresh alert on a violation
           nothing about actually changed -- which re-triggers the remediation
           playbook on its own audit trail.

        2. Entries whose own time falls outside this run's window are excluded --
           see _entries_in_window.

        Returns:
            The winning entry, or {} when no entry qualifies -- the caller must
            treat that as "no alert for this series this run".
        """
        real_activity = [
            node
            for node in self.activity_nodes
            if not (node.get("message") or "").startswith(
                ACTIONS_LOG_DOWNLOAD_MESSAGE_PREFIX
            )
        ]

        real_activity = self._entries_in_window(real_activity)

        if not real_activity:
            return {}
        return max(real_activity, key=lambda node: node.get("time") or "")

    def _entries_in_window(self, real_activity: list[SingleJson]) -> list[SingleJson]:
        """Keep only the entries whose own time falls inside this run's window.

        RSC filters the SERIES by lastUpdated, never its entries, so a series
        pulled in by a recent entry arrives carrying its entire history. An
        audit-log download therefore drags the original "detected" entry --
        possibly days old -- back into scope, and with the audit-entry filter
        removing the audit entries that original becomes the pick and is
        re-alerted on every run. Restricting to entries that actually happened in
        this window means a series whose only new activity was an audit download
        yields nothing, which is correct: nothing about the violation changed.

        Window bounds are (start, end]: start is the previous run's end, so an
        entry exactly on it was already ingested, while an entry exactly on this
        run's end has not been. With no window, every entry is kept.
        """
        if self.window_end_ms:
            real_activity = [
                node
                for node in real_activity
                if self.window_start_ms
                < _iso_to_unix_ms(node.get("time"))
                <= self.window_end_ms
            ]
        return real_activity

    def _get_priority(self, latest: SingleJson) -> int:
        """SOAR priority for this alert, most specific severity signal first.

        1. The severity the message leads with ("Low severity violation of ..."):
           the violation's own severity, and the only place it appears.
        2. The latest activity entry's severity: current for this transition, and
           set even on messages that carry no severity prefix (identity events).
        3. The series-level severity: least specific -- RSC reports it as "Info"
           even for a Low or Critical violation, so relying on it alone would
           flatten every DSPM/IR alert to the lowest priority.
        """
        severity = _first_non_empty(
            _extract_message_severity(latest.get("message")),
            latest.get("severity"),
            self.event_node.get("severity"),
        )
        return RUBRIK_SEVERITY_MAP.get(severity.strip().upper(), RUBRIK_SEVERITY_MAP["INFO"])

    def get_alert_info(
        self,
        alert_info: Any,
        environment_common: Any,
        event_field_parameter: str = "",
        product_field_name: str = "",
    ) -> Any:
        """Convert an activitySeries node to Siemplify AlertInfo format."""
        fields = self._alert_fields(self.get_latest_activity_node())

        self._set_alert_fields(alert_info, fields, environment_common)
        alert_info.event_field_name = event_field_parameter
        alert_info.source_system_name = product_field_name
        alert_info.event_product = fields["last_activity_type"]

        event = self._build_event(fields)
        self._enrich_event(event, fields["latest"])
        alert_info.events = [event]

        return alert_info

    def _alert_fields(self, latest: SingleJson) -> SingleJson:
        """Values shared by the alert-level fields and the event dict."""
        series_id = _first_non_empty(
            self.event_node.get("activitySeriesId"), self.event_node.get("id")
        )
        # Dedup key: the latest transition's own immutable id.
        activity_node_id = _first_non_empty(latest.get("id"), series_id)
        message = latest.get("message") or ""
        last_activity_type = self.event_node.get("lastActivityType") or ""
        start_time = self.event_node.get("startTime") or ""
        last_updated = self.event_node.get("lastUpdated") or start_time
        # Composed from the message's severity/policy and the series' objectName,
        # so the name does not change as the violation transitions; the raw
        # message is kept on the event as activityMessage.
        name = _first_non_empty(
            _build_violation_alert_name(message, self.event_node.get("objectName")),
            last_activity_type,
        )
        return {
            "latest": latest,
            "series_id": series_id,
            "activity_node_id": activity_node_id,
            "message": message,
            "last_activity_type": last_activity_type,
            "start_time": start_time,
            "last_updated": last_updated,
            "name": name,
        }

    def _set_alert_fields(
        self, alert_info: Any, fields: SingleJson, environment_common: Any
    ) -> None:
        """Set the SecOps alert-level fields, up to and including the grouping key."""
        # --- AlertInfo fields (SecOps alert-level mapping) ---
        alert_info.ticket_id = fields["activity_node_id"]
        alert_info.display_id = fields["activity_node_id"]
        alert_info.name = fields["name"]
        alert_info.rule_generator = fields["name"]
        alert_info.description = fields["name"]
        alert_info.start_time = _iso_to_unix_ms(fields["start_time"])
        alert_info.end_time = _iso_to_unix_ms(fields["last_updated"])
        alert_info.device_product = DEVICE_PRODUCT
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.priority = self._get_priority(fields["latest"])
        alert_info.environment = environment_common.get_environment(self.event_node)
        # Grouping key: every transition of one violation shares its series id,
        # so they all land in the same case.
        alert_info.source_grouping_identifier = fields["series_id"]

    def _build_event(self, fields: SingleJson) -> SingleJson:
        """Event dict (SecOps EventsList): mapping, time and latest-transition fields."""
        latest = fields["latest"]
        message = fields["message"]
        # --- Event dict (SecOps EventsList) ---
        return {
            # SecOps mapping fields
            "SourceSystemName":   DEVICE_VENDOR,
            "DeviceVendor":       DEVICE_VENDOR,
            "DeviceProduct":      DEVICE_PRODUCT,
            "Description":        fields["name"],
            "DisplayId":          fields["activity_node_id"],
            # lastActivityType verbatim -- not a constructed label.
            "eventName":          fields["last_activity_type"],
            "EventProduct":       fields["last_activity_type"],
            # SOAR required time fields
            "StartTime":          _iso_to_unix_ms(fields["start_time"]),
            "EndTime":            _iso_to_unix_ms(fields["last_updated"]),
            "Name":               fields["name"],
            # Discriminator promoted to the top level for playbook conditions.
            "violationType":      self.violation_type,
            # The latest transition, promoted so playbooks need not index into
            # the flattened activityConnection entry below.
            "activityNodeId":     fields["activity_node_id"],
            "activityMessage":    message,
            "activityTime":       latest.get("time", ""),
            "activitySeverity":   latest.get("severity", ""),
            "violationSeverity":  _extract_message_severity(message),
        }

    def _enrich_event(self, event: SingleJson, latest: SingleJson) -> None:
        """Add the flattened series, the resolved status and the hierarchy identity."""
        # Every field the API returned for this series, flattened -- but only the
        # latest activityConnection entry. The older entries are prior
        # transitions of the same violation that were already ingested by earlier
        # runs; carrying them here would re-ingest superseded state alongside the
        # current one. What remains is a single-entry list, so the flattened
        # fields are always activityConnection_nodes_0_*.
        event.update(_flatten_payload(self._series_with_latest_activity_only(latest)))

        # The one field the violation lookup contributes, added after the series
        # flatten so it cannot be shadowed. Set only when resolved: an empty
        # `status` would read to the job as a violation with an unrecognised
        # status rather than one it could not resolve -- both leave the case open,
        # but only the latter is countable in the run log.
        if self.violation_status:
            event["status"] = self.violation_status

        event.update(_hierarchy_fields(self.hierarchy_object))

    def _series_with_latest_activity_only(self, latest: SingleJson) -> SingleJson:
        """Shallow copy of the series whose activityConnection holds only `latest`.

        Copied rather than mutated so the caller's node -- which the connector
        also logs and may reuse -- is left untouched.
        """
        series = dict(self.event_node)
        activity_connection = dict(series.get("activityConnection") or {})
        activity_connection["nodes"] = [latest] if latest else []
        series["activityConnection"] = activity_connection
        return series
