"""RSC client methods for DSPM / Identity Resilience violations and their files.

Mixed into APIManager, which supplies the HTTP session, GraphQL execution and
logging these methods rely on.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import requests

from .constants import (
    ACCESS_TYPE_UNSPECIFIED,
    DEFAULT_FILE_LIST_MAX_RESULTS,
    DEFAULT_MAX_RESULTS,
    DEFAULT_REQUEST_TIMEOUT,
    ERROR_NO_VIOLATION_FOUND,
    FILE_DOWNLOAD_ENDPOINT,
    FILE_TYPE_HITS,
    GET_CLASSIFICATION_OBJECT_DETAIL_ACTION_IDENTIFIER,
    GET_SNAPPABLE_IDENTITY_ACTION_IDENTIFIER,
    REMEDIATION_TARGET_TYPE_VIOLATION,
    REMEDIATION_TYPE_EXPORT_LOG,
)
from .graphql_queries import (
    CLASSIFICATION_OBJECT_DETAIL_QUERY,
    SNAPPABLE_IDENTITY_QUERY,
)
from .rubrik_exceptions import (
    AmbiguousFileMatchException,
    ConnectionTimeoutException,
    ItemNotFoundException,
    RubrikException,
)
from .violation_graphql_queries import (
    CREATE_REMEDIATION_MUTATION,
    DOWNLOAD_BAR_QUERY,
    DOWNLOAD_CSV_MUTATION,
    DSPM_GET_QUERY,
    DSPM_LIST_QUERY,
    FILE_LIST_QUERY,
    IR_GET_QUERY,
    IR_LIST_QUERY,
    UPDATE_VIOLATIONS_MUTATION,
)

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class DateRange:
    """An optional start/end pair; only applied as a filter when both are set."""

    start: str | None = None
    end: str | None = None

    def is_set(self) -> bool:
        return bool(self.start and self.end)


@dataclasses.dataclass(slots=True)
class SortSpec:
    """GraphQL sortBy / sortOrder API values."""

    sort_by: str | None = None
    sort_order: str | None = None


@dataclasses.dataclass(slots=True)
class DSPMViolationSearchFilter:
    """Filters for the DSPM policy violations list query (all API enum values)."""

    statuses: list[str] | None = None
    severities: list[str] | None = None
    categories: list[str] | None = None
    sensitivity_levels: list[str] | None = None
    object_types: list[str] | None = None
    detection_date: DateRange = dataclasses.field(default_factory=DateRange)
    update_date: DateRange = dataclasses.field(default_factory=DateRange)
    sort: SortSpec = dataclasses.field(default_factory=SortSpec)


@dataclasses.dataclass(slots=True)
class IRViolationSearchFilter:
    """Filters for the Identity Resilience violations list query (API enum values)."""

    policy_types: list[str]
    statuses: list[str] | None = None
    severities: list[str] | None = None
    categories: list[str] | None = None
    idp_types: list[str] | None = None
    identity_tags: list[str] | None = None
    detection_date: DateRange = dataclasses.field(default_factory=DateRange)
    update_date: DateRange = dataclasses.field(default_factory=DateRange)
    sort: SortSpec = dataclasses.field(default_factory=SortSpec)


@dataclasses.dataclass(slots=True)
class ViolationFileListFilter:
    """Filters for the files-at-risk list of a single DSPM violation snapshot."""

    snappable_fid: str
    snapshot_fid: str
    violation_id: str | None = None
    filename_filter: str | None = None
    risk_levels: list[str] | None = None
    exposures: list[str] | None = None
    access_via: str | None = None
    last_access: DateRange = dataclasses.field(default_factory=DateRange)
    last_updated: DateRange = dataclasses.field(default_factory=DateRange)
    creation: DateRange = dataclasses.field(default_factory=DateRange)
    last_scan: DateRange = dataclasses.field(default_factory=DateRange)
    sort: SortSpec = dataclasses.field(default_factory=SortSpec)


@dataclasses.dataclass(slots=True)
class Page:
    """Cursor pagination for list queries."""

    first: int = DEFAULT_MAX_RESULTS
    after_cursor: str | None = None


def _add_violation_search_variables(
    variables: SingleJson,
    search_filter: DSPMViolationSearchFilter | IRViolationSearchFilter,
) -> None:
    """Add the filter fields DSPM and IR list queries share, in place."""
    if search_filter.statuses:
        variables["statuses"] = search_filter.statuses
    if search_filter.severities:
        variables["severities"] = search_filter.severities
    if search_filter.categories:
        variables["categories"] = search_filter.categories
    if search_filter.detection_date.is_set():
        variables["detectionDate"] = {
            "start": search_filter.detection_date.start,
            "end": search_filter.detection_date.end,
        }
    if search_filter.update_date.is_set():
        variables["updateDate"] = {
            "start": search_filter.update_date.start,
            "end": search_filter.update_date.end,
        }


def _add_sort_and_cursor(variables: SingleJson, sort: SortSpec, page: Page) -> None:
    """Add sortBy / sortOrder / after to a list query's variables, in place."""
    if sort.sort_by:
        variables["sortBy"] = sort.sort_by
    if sort.sort_order:
        variables["sortOrder"] = sort.sort_order
    if page.after_cursor:
        variables["after"] = page.after_cursor


def _time_range_filter(date_range: DateRange) -> dict[str, str] | None:
    """Build a {startTime, endTime, timezone} filter block, or None if either is absent."""
    if not date_range.is_set():
        return None
    return {"startTime": date_range.start, "endTime": date_range.end, "timezone": "UTC"}


def _flatten_user_files(data: SingleJson) -> list[SingleJson]:
    """Flatten allUserFiles download groups into one list of file entries."""
    all_files: list[SingleJson] = []
    for group in data.get("allUserFiles") or []:
        all_files.extend(group.get("downloads") or [])
    return all_files


def _parse_user_file_created_at(created_at: str | None) -> datetime | None:
    """Parse an allUserFiles createdAt timestamp into a timezone-aware datetime.

    RSC returns ISO-8601 UTC timestamps such as "2026-07-21T18:07:11.000Z".
    Returns None if the value is missing or cannot be parsed.
    """
    if not created_at:
        return None
    try:
        normalized = created_at.strip().replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (ValueError, AttributeError):
        return None


def _filter_matching_user_files(
    all_files: list[SingleJson],
    file_type: str,
    filename_contains: str,
    created_after: datetime | None,
) -> list[SingleJson]:
    """Keep entries of `file_type` whose filename contains `filename_contains`.

    When `created_after` is provided, only entries created strictly after it are
    kept; entries with a missing or unparseable createdAt are treated as oldest.
    """
    candidates = [
        f
        for f in all_files
        if f.get("type") == file_type
        and filename_contains.lower() in (f.get("filename") or "").lower()
    ]
    if created_after is None:
        return candidates
    oldest = datetime.min.replace(tzinfo=timezone.utc)
    return [
        f
        for f in candidates
        if (_parse_user_file_created_at(f.get("createdAt")) or oldest) > created_after
    ]


def _raise_if_ambiguous(candidates: list[SingleJson], filename_contains: str) -> None:
    """Raise AmbiguousFileMatchException when more than one candidate remains."""
    if len(candidates) <= 1:
        return
    filenames = ", ".join(
        f"{f.get('filename')!r} (createdAt={f.get('createdAt')})" for f in candidates
    )
    raise AmbiguousFileMatchException(
        f"Found {len(candidates)} files matching '{filename_contains}' created after "
        f"the action started; cannot determine which one belongs to this request. "
        f"Matches: {filenames}."
    )


class ViolationsApiMixin:
    """DSPM / IR violation, user-file and classification calls for APIManager."""

    def search_dspm_violations(
        self,
        search_filter: DSPMViolationSearchFilter,
        page: Page,
    ) -> SingleJson:
        """Paginated search for DSPM policy violations."""
        variables: SingleJson = {"first": page.first}
        _add_violation_search_variables(variables, search_filter)
        if search_filter.sensitivity_levels:
            variables["sensitivityLevels"] = search_filter.sensitivity_levels
        if search_filter.object_types:
            variables["resourceMetadataFilter"] = {
                "managedObjectTypes": search_filter.object_types
            }
        _add_sort_and_cursor(variables, search_filter.sort, page)

        self._log(f"Searching DSPM violations with variables: {variables}")
        return self._execute_graphql(DSPM_LIST_QUERY, variables)

    def get_dspm_violation_details(self, violation_id: str) -> SingleJson:
        """Retrieve full details for a single DSPM violation."""
        variables = {
            "violationId": violation_id,
        }
        self._log(f"Getting DSPM violation details: {violation_id}")
        data = self._execute_graphql(DSPM_GET_QUERY, variables)
        if not data.get("policyViolation"):
            raise ItemNotFoundException(ERROR_NO_VIOLATION_FOUND.format(violation_id))
        return data

    def update_violation_status(
        self,
        violation_ids: list[str],
        new_status: str,
    ) -> None:
        """Update the status of one or more DSPM or IR violations.

        The bulkUpdatePolicyViolations mutation returns null on success.
        Raises GraphQLQueryException if the response contains errors.
        """
        variables = {
            "input": {
                "newPolicyViolationStatus": new_status,
                "policyViolationIds": violation_ids,
            }
        }
        self._log(f"Updating violation(s) {violation_ids} to status: {new_status}")
        self._execute_graphql(UPDATE_VIOLATIONS_MUTATION, variables)

    def trigger_snapshot_csv(
        self,
        snappable_fid: str,
        snapshot_fid: str,
        violation_id: str,
    ) -> bool:
        """Trigger async CSV generation for files at risk in a snapshot.

        Returns:
            True if isSuccessful was returned as true.

        Raises:
            RubrikException: If isSuccessful is false.
        """
        variables = {
            "snappableFid": snappable_fid,
            "snapshotFid": snapshot_fid,
            "filters": {
                "policyViolationId": violation_id,
                "fileType": FILE_TYPE_HITS,
            },
        }
        self._log(
            f"Triggering snapshot CSV: snappableFid={snappable_fid} "
            f"snapshotFid={snapshot_fid} violationId={violation_id}"
        )
        data = self._execute_graphql(DOWNLOAD_CSV_MUTATION, variables)
        is_successful = (data.get("downloadSnapshotResultsCsv") or {}).get("isSuccessful", False)
        if not is_successful:
            raise RubrikException(
                "CSV generation trigger returned isSuccessful=false. "
                "Check RSC permissions and input IDs."
            )
        return True

    def find_user_file_by_filename(
        self,
        file_type: str,
        filename_contains: str,
        created_after: datetime | None = None,
    ) -> SingleJson | None:
        """Locate a user file entry by type + filename pattern, in any state.

        The entry is returned in whatever state it currently happens to be
        (READY, FAILED, or still generating).

        Intended to be called only until a matching entry is found at all —
        once found, callers should persist its externalId and switch to
        get_user_file_by_external_id() for all subsequent status checks
        instead of re-matching by filename on every poll. This avoids
        repeatedly re-scanning every user's downloads and pins the poll to
        one concrete file as soon as its identity is known.

        Args:
            file_type: One of USER_FILE_TYPE_CSV or USER_FILE_TYPE_LOG.
            filename_contains: Hard filter — only entries whose filename
                contains this value (case-insensitive) are considered.
            created_after: When provided, only entries created strictly after
                this time are considered. This isolates the file generated by
                the current action run from files with the same name format
                that were triggered earlier for the same object but a different
                violation/snapshot. If more than one entry matches the name and
                was created after this time, the correct file cannot be
                determined and AmbiguousFileMatchException is raised.

        Returns:
            The most-recently-created matching entry, or None if no matching
            entry exists yet (the triggered file hasn't appeared in the
            download bar at all so far).

        Raises:
            AmbiguousFileMatchException: If created_after is provided and more
                than one matching entry was created after it.
        """
        all_files = _flatten_user_files(self._execute_graphql(DOWNLOAD_BAR_QUERY, {}))
        candidates = _filter_matching_user_files(
            all_files, file_type, filename_contains, created_after
        )

        if not candidates:
            self._log(
                f"No file located yet (file_type={file_type}, "
                f"filename_contains={filename_contains!r})."
            )
            return None

        if created_after is not None:
            _raise_if_ambiguous(candidates, filename_contains)

        candidates.sort(key=lambda f: f.get("createdAt", ""), reverse=True)
        entry = candidates[0]
        self._log(
            f"File located: state={entry.get('state')} "
            f"externalId={entry.get('externalId')} filename={entry.get('filename')}"
        )
        return entry

    def get_user_file_by_external_id(self, external_id: str) -> SingleJson | None:
        """Look up a specific, already-identified user file entry by its externalId.

        Args:
            external_id: The externalId captured from a prior
                find_user_file_by_filename() call.

        Returns:
            The matching entry (in whatever state it currently has), or None
            if it's not present in allUserFiles (not yet visible, or expired).
        """
        for entry in _flatten_user_files(self._execute_graphql(DOWNLOAD_BAR_QUERY, {})):
            if entry.get("externalId") == external_id:
                self._log(f"File status: state={entry.get('state')} externalId={external_id}")
                return entry
        self._log(f"File not visible yet for externalId={external_id}.")
        return None

    def download_file(self, external_id: str) -> bytes:
        """Download a generated file from /file-downloads/{external_id}.

        Returns:
            Binary content of the file.

        Raises:
            RubrikException: If the HTTP download request fails (e.g. missing
                ViewReport permission, expired file). Message is intentionally
                unprefixed so each calling action can prepend its own wording.
        """
        endpoint = FILE_DOWNLOAD_ENDPOINT.format(external_id=external_id)
        url = f"https://{self.domain}{endpoint}"
        self._log(f"Downloading file externalId={external_id}")
        try:
            response = self.session.get(url, timeout=DEFAULT_REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as e:
            raise ConnectionTimeoutException(
                f"Unable to connect to Rubrik at {url}. Please verify the endpoint is "
                f"reachable and the Service Account JSON is valid. Details: {e}"
            ) from e
        if not response.ok:
            raise RubrikException(
                f"File download failed. Status: {response.status_code}. Body: {response.text}"
            )
        return response.content

    def trigger_remediation_log(
        self,
        violation_id: str,
        resource_id: str,
    ) -> str:
        """Trigger async remediation log CSV generation.

        Returns:
            The remediationId string.

        Raises:
            RubrikException: If remediationId is missing from the response.
        """
        variables = {
            "input": {
                "targets": {
                    "targetIds": [violation_id],
                    "targetType": REMEDIATION_TARGET_TYPE_VIOLATION,
                },
                "remediationType": REMEDIATION_TYPE_EXPORT_LOG,
                "resourceId": resource_id,
            }
        }
        self._log(
            f"Triggering remediation log: violationId={violation_id} resourceId={resource_id}"
        )
        data = self._execute_graphql(CREATE_REMEDIATION_MUTATION, variables)
        remediation_id = (data.get("createViolationRemediation") or {}).get("remediationId")
        if not remediation_id:
            raise RubrikException(
                "Remediation log creation did not return a remediationId. "
                "Check RSC permissions and input IDs."
            )
        return remediation_id

    def get_violation_file_list(
        self,
        file_filter: ViolationFileListFilter,
        page: Page | None = None,
    ) -> SingleJson:
        """Paginated list of files at risk for a DSPM violation."""
        page = page or Page(first=DEFAULT_FILE_LIST_MAX_RESULTS)
        variables: SingleJson = {
            "snappableFid": file_filter.snappable_fid,
            "snapshotFid": file_filter.snapshot_fid,
            "first": page.first,
            "filters": _build_file_list_filters(file_filter),
            "timezone": "UTC",
        }
        sort = file_filter.sort
        if sort.sort_by or sort.sort_order:
            variables["sort"] = {
                "sortBy": sort.sort_by or "HITS",
                "sortOrder": sort.sort_order or "DESC",
            }
        if page.after_cursor:
            variables["after"] = page.after_cursor

        self._log(
            f"Getting violation file list: snappableFid={file_filter.snappable_fid} "
            f"snapshotFid={file_filter.snapshot_fid} violationId={file_filter.violation_id}"
        )
        return self._execute_graphql(FILE_LIST_QUERY, variables)

    def search_ir_violations(
        self,
        search_filter: IRViolationSearchFilter,
        page: Page,
    ) -> SingleJson:
        """Paginated search for Identity Resilience (IR) policy violations."""
        variables: SingleJson = {
            "policyTypes": search_filter.policy_types,
            "first": page.first,
        }
        _add_violation_search_variables(variables, search_filter)
        resource_metadata_filter: SingleJson = {}
        if search_filter.idp_types:
            resource_metadata_filter["idpTypes"] = search_filter.idp_types
        if search_filter.identity_tags:
            resource_metadata_filter["identityTags"] = search_filter.identity_tags
        if resource_metadata_filter:
            variables["resourceMetadataFilter"] = resource_metadata_filter
        _add_sort_and_cursor(variables, search_filter.sort, page)

        self._log(f"Searching IR violations: policyTypes={search_filter.policy_types}")
        return self._execute_graphql(IR_LIST_QUERY, variables)

    def get_ir_violation_details(
        self,
        violation_id: str,
        policy_types: list[str],
    ) -> SingleJson:
        """Retrieve full details for a single IR violation.

        Uses the same DataSecurityViolationGetQuery operation as DSPM details,
        but with IR policy types which drives the IR-specific response schema.
        """
        variables = {
            "violationId": violation_id,
            "policyTypes": policy_types,
        }
        self._log(f"Getting IR violation details: {violation_id} policyTypes={policy_types}")
        data = self._execute_graphql(IR_GET_QUERY, variables)
        if not data.get("policyViolation"):
            raise ItemNotFoundException(ERROR_NO_VIOLATION_FOUND.format(violation_id))
        return data

    def get_snappable_identity(self, fid: str) -> SingleJson:
        """Resolve a snappable's hierarchy identity from its fid.

        `fid` is the activity series' objectId. Returns the raw response so the
        caller can read data.hierarchyObject; the shape is type-dependent, since
        O365Site and O365Onedrive contribute extra fields through inline fragments
        while other object types return only id/name/objectType.
        """
        variables = {"fid": fid}
        payload = json.dumps({"query": SNAPPABLE_IDENTITY_QUERY, "variables": variables})
        return self._make_rest_call(
            GET_SNAPPABLE_IDENTITY_ACTION_IDENTIFIER,
            "POST",
            self.graphql_url,
            data=payload,
        )

    def get_classification_object_detail(
        self,
        snappable_fid: str,
        snapshot_fid: str,
    ) -> SingleJson:
        variables = {
            "snappableFid": snappable_fid,
            "snapshotFid": snapshot_fid,
            "includeWhitelistedResults": False,
        }
        payload = json.dumps({"query": CLASSIFICATION_OBJECT_DETAIL_QUERY, "variables": variables})
        return self._make_rest_call(
            GET_CLASSIFICATION_OBJECT_DETAIL_ACTION_IDENTIFIER,
            "POST",
            self.graphql_url,
            data=payload,
        )


def _build_file_list_filters(file_filter: ViolationFileListFilter) -> SingleJson:
    """Build the `filters` input of the violation file list query."""
    filters: SingleJson = {
        "fileType": FILE_TYPE_HITS,
        "whitelistEnabled": True,
        "snappablePaths": [{"snappableFid": file_filter.snappable_fid}],
        "riskLevelTypesFilter": file_filter.risk_levels or [],
        "exposureFilter": file_filter.exposures or [],
        "accessVia": file_filter.access_via or ACCESS_TYPE_UNSPECIFIED,
    }
    if file_filter.violation_id:
        filters["violationId"] = file_filter.violation_id
    if file_filter.filename_filter:
        filters["searchText"] = file_filter.filename_filter

    time_filters = {
        "lastAccessFilter": file_filter.last_access,
        "lastModifiedFilter": file_filter.last_updated,
        "creationTimeFilter": file_filter.creation,
        "lastScanFilter": file_filter.last_scan,
    }
    for key, date_range in time_filters.items():
        time_range = _time_range_filter(date_range)
        if time_range:
            filters[key] = time_range
    return filters
