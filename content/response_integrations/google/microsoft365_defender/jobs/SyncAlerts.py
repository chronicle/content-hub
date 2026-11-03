# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import datetime
import json
from typing import Any, TYPE_CHECKING

from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time, convert_unixtime_to_datetime

from TIPCommon.base.action.data_models import (
    CloseCaseOrAlertInconclusiveRootCauses,
    CloseCaseOrAlertMaliciousRootCauses,
    CloseCaseOrAlertNotMaliciousRootCauses,
)
from TIPCommon.base.job.base_sync_job import BaseSyncJob
from TIPCommon.base.job.job_case import (
    JobCase,
    SyncMetadata,
    JobCommentsResult,
    JobStatusResult,
)
from TIPCommon.data_models import CaseDataStatus, AlertCard
from TIPCommon.rest.soar_api import rename_case
from microsoft365_defender.core import constants
from microsoft365_defender.core.datamodels import AlertWithEvidence, Incident
from microsoft365_defender.core.Microsoft365DefenderExceptions import (
    Microsoft365DefenderException,
    NotFoundItemException,
)
from microsoft365_defender.core.Microsoft365DefenderManager import Microsoft365DefenderManager
from microsoft365_defender.core.UtilsManager import (
    get_m365_alert_id_from_soar_alert,
    get_m365_alert_id_from_soar_alerts,
    parse_iso_datetime,
)

if TYPE_CHECKING:
    from typing import NoReturn, TypeAlias
    from TIPCommon.types import SingleJson


CaseIdModifiedTimeList: TypeAlias = list[tuple[str, int]]


class SyncAlerts(BaseSyncJob[Microsoft365DefenderManager]):
    def __init__(self) -> None:
        super().__init__(
            job_name=constants.SYNC_ALERTS_SCRIPT_NAME,
            context_identifier=constants.SYNC_ALERTS_IDENTIFIER,
            tags_identifiers=[constants.M365_DEFENDER_ALERT_TAG],
        )
        self.sync_limit = constants.CASES_SYNC_LIMIT
        self.manager: Microsoft365DefenderManager | None = None

    def _init_api_clients(self) -> None:
        """Initializes the API clients."""
        self.manager = Microsoft365DefenderManager(
            api_root=self.params.api_root,
            tenant_id=self.params.tenant_id,
            client_id=self.params.client_id,
            client_secret=self.params.client_secret,
            verify_ssl=self.params.verify_ssl,
            login_api_root=self.params.login_api_root,
            microsoft_graph_url=self.params.graph_api_root,
            siemplify=self.soar_job,
        )

    def modified_synced_case_ids_by_product(
        self,
        incident_ids: list[str],
        sorted_modified_ids: CaseIdModifiedTimeList,
    ) -> CaseIdModifiedTimeList:
        """Fetches modified alerts from Microsoft Defender and maps them to SecOps
        case IDs.

        Args:
            incident_ids (list[str]): A list of Microsoft Defender alert IDs that are
            associated with the SecOps cases to check for modifications.
            sorted_modified_ids (CaseIdModifiedTimeList): A list of tuples containing
            SecOps case IDs and their last modified times, sorted by time.

        Returns:
            CaseIdModifiedTimeList: A list of tuples containing SecOps case IDs and
            their last modified times.
        """
        product_ids_to_case_map = self.alert_ids_to_case_map_builder()
        modified_alerts = self._fetch_modified_alerts(incident_ids)
        filtered_alert_ids = self._filter_alert_ids(modified_alerts)
        new_modified_alerts = self._fetch_alerts_by_ids(filtered_alert_ids)

        return self._map_alerts_to_cases(
            new_modified_alerts,
            product_ids_to_case_map,
            sorted_modified_ids,
        )

    def _fetch_modified_alerts(self, alert_ids: list[str]) -> list[AlertWithEvidence]:
        """Fetches modified alerts from Microsoft Defender.

        Args:
            alert_ids (list[str]): A list of Microsoft Defender alert IDs to check for
            modifications.

        Returns:
            list[AlertWithEvidence]: A list of AlertWithEvidence datamodel objects
            representing the modified alerts.
        """
        return self.manager.get_alerts_by_ids(alert_ids)

    def _filter_alert_ids(self, modified_alerts: list[AlertWithEvidence]) -> list[str]:
        """Filters alert IDs to only those present in the modified alerts list.

        Args:
            modified_alerts (list[AlertWithEvidence]): A list of AlertWithEvidence
            datamodel objects representing the modified alerts.

        Returns:
            list[str]: A list of Microsoft Defender alert IDs that are present in the
            modified alerts list.
        """
        final_alert_ids = []

        for alert in modified_alerts:
            alert_timestamp = (
                alert.raw_data.get("lastUpdateDateTime")
                or alert.raw_data.get("createdDateTime")
            )
            if not alert_timestamp:
                continue
            modified_time = parse_iso_datetime(alert_timestamp)
            if (
                modified_time
                and modified_time > convert_unixtime_to_datetime(self.last_run_time)
            ):
                final_alert_ids.append(alert.alert_id)

        return final_alert_ids

    def _fetch_alerts_by_ids(self, alert_ids: list[str]) -> list[AlertWithEvidence]:
        """Fetches alerts by their IDs.

        Args:
            alert_ids (list[str]): A list of Microsoft Defender alert IDs to fetch.

        Returns:
            list[AlertWithEvidence]: A list of AlertWithEvidence datamodel objects
            representing the fetched alerts.
        """
        return self.manager.get_alerts_by_ids(alert_ids)

    def _map_alerts_to_cases(
        self,
        alerts: list[AlertWithEvidence],
        product_ids_to_case_map: dict[str, str],
        sorted_modified_ids: CaseIdModifiedTimeList,
    ) -> CaseIdModifiedTimeList:
        """Maps alerts to SecOps cases and determines the final modified time.

        Args:
            alerts (list[AlertWithEvidence]): A list of AlertWithEvidence datamodel
            objects representing the modified alerts.
            product_ids_to_case_map (dict[str, str]): A dictionary mapping Microsoft
            Defender alert IDs to SecOps case IDs.
            sorted_modified_ids (CaseIdModifiedTimeList): A list of tuples containing
            SecOps case IDs and their last modified times, sorted by time.

        Returns:
            CaseIdModifiedTimeList: A list of tuples containing SecOps case IDs and
            their last modified times.
        """
        results = []
        case_time_map = dict(sorted_modified_ids)

        for alert in alerts:
            alert_id = alert.alert_id
            case_id = product_ids_to_case_map.get(alert_id)

            if not case_id:
                self.logger.info(
                    f"Skipping alert sync for Defender alert ID {alert_id} "
                    "as no matching SecOps case/alert ID was found in the map."
                )
                continue

            modified_time_ms = self._get_alert_modified_time_ms(alert)
            case_time_ms = case_time_map.get(case_id, constants.DEFAULT_CASE_TIME)
            results.append((case_id, max(modified_time_ms, case_time_ms)))

        return results

    def _get_alert_modified_time_ms(self, alert: AlertWithEvidence) -> int:
        """Extracts the modified time from an alert and converts it to milliseconds.

        Args:
            alert (AlertWithEvidence): An AlertWithEvidence datamodel object
            representing the alert.

        Returns:
            int: The modified time in milliseconds.
        """
        modified_time_utc_str = (
            alert.raw_data.get("lastUpdateDateTime")
            or alert.raw_data.get("createdDateTime")
        )
        if not modified_time_utc_str:
            return 0

        modified_time = parse_iso_datetime(modified_time_utc_str)
        if not modified_time:
            return 0

        return convert_datetime_to_unix_time(modified_time)

    def is_alert_and_product_closed(
        self,
        job_case: JobCase,
        product: AlertWithEvidence,
    ) -> bool:
        """Check if both the alert and the Microsoft Defender alert are closed.

        Args:
            job_case (JobCase): The SecOps case to check.
            product (AlertWithEvidence): The Microsoft Defender alert to check.

        Returns:
            bool: True if both the alert and the Microsoft Defender alert are closed,
            False otherwise.
        """
        alert = get_m365_alert_id_from_soar_alerts(self.soar_job, job_case)[
            product.alert_id
        ]

        if not alert:
            return False

        alert_closed = alert.status.lower() == "close"
        product_status = product.raw_data.get("status")
        product_closed = (
            product_status.lower() == constants.M365_STATUS_RESOLVED.lower()
        )

        return alert_closed and product_closed

    def _extract_product_ids_from_case(
        self,
        job_case: JobCase,
    ) -> list[str]:
        """Extracts product IDs from the SecOps case.

        Args:
            job_case (JobCase): The SecOps case to extract product IDs from.

        Returns:
            list[str]: A sorted list of unique product IDs extracted from the case.
        """
        alert_ids = list(
            get_m365_alert_id_from_soar_alerts(self.soar_job, job_case).keys()
        )
        return sorted(set(alert_ids))

    def alert_ids_to_case_map_builder(self) -> dict[str, str]:
        """Builds a map of Microsoft Defender alert IDs to SecOps case IDs.

        Returns:
            dict[str, str]: A dictionary mapping Microsoft Defender alert IDs to
            SecOps case IDs.
        """
        product_ids_to_case_map: dict[str, str] = {}
        for case_id, product_ids in self.processed_items.items():
            for product_id in product_ids:
                product_ids_to_case_map[product_id] = case_id

        return product_ids_to_case_map

    def map_product_data_to_case(self, job_case: JobCase) -> None:
        """Maps Defender Alert data into metadata.

        Args:
            job_case (JobCase): The SecOps case to map product data to.
        """
        mapping: dict[str, AlertCard] = get_m365_alert_id_from_soar_alerts(
            self.soar_job, job_case
        )
        product_ids_from_alerts = list(mapping.keys())
        job_case.product_ids_from_secops_alerts = mapping
        product_details = self._fetch_alerts_by_ids(product_ids_from_alerts)
        self._attach_comments_to_product_details(product_details)
        self._attach_product_details_to_case(job_case, product_details)
        self._populate_alert_metadata(job_case, product_details)
        self.remove_synced_data_from_db(job_case, product_details)

    def _attach_comments_to_product_details(
        self,
        product_details: list[AlertWithEvidence],
    ) -> None:
        """Attaches new comments to each product detail.

        Args:
            product_details (list[AlertWithEvidence]): A list of AlertWithEvidence
            datamodel objects representing the product details to attach comments to.
        """
        for product_detail in product_details:
            new_comments = self._get_new_m365_comments(product_detail)

            if isinstance(new_comments, list):
                product_detail.add_comments(new_comments)

    def _attach_product_details_to_case(
        self,
        job_case: JobCase,
        product_details: list[AlertWithEvidence],
    ) -> None:
        """Attaches product details to the SecOps case.

        Args:
            job_case (JobCase): The SecOps case to attach product details to.
            product_details (list[AlertWithEvidence]): A list of AlertWithEvidence
            datamodel objects representing the product details to attach to the case.
        """
        for product_detail in product_details:
            job_case.add_product_incident(product_detail, product_key="alert_id")

    def _populate_alert_metadata(
        self,
        job_case: JobCase,
        product_details: list[AlertWithEvidence],
    ) -> None:
        """Populates alert metadata for each alert in the case.

        Args:
            job_case (JobCase): The SecOps case to populate alert metadata for.
            product_details (list[AlertWithEvidence]): A list of AlertWithEvidence
            datamodel objects representing the product details to extract metadata from.
        """
        for product_detail in product_details:
            alert_identifier = job_case.get_alert_identifier_from_product_id(
                product_id=product_detail.alert_id,
            )

            job_case.alert_metadata[alert_identifier] = SyncMetadata(
                status=product_detail.raw_data.get("status"),
                assignee=product_detail.raw_data.get("assignedTo"),
                incident_number=product_detail.alert_id,
                closure_reason=product_detail.raw_data.get("classification"),
                determination=product_detail.raw_data.get("determination"),
            )

    def _get_new_m365_comments(self, m365_alert: AlertWithEvidence) -> list[str]:
        """Get new comments from a Microsoft Defender XDR Alert to be added to SOAR.

        Args:
            m365_alert: The Microsoft XDR Defender alert.

        Returns:
            list[str]: A list of new comments to be added to SOAR.
        """
        comments_to_add = []
        m365_comments: list = m365_alert.raw_data.get("comments", [])
        m365_comments.sort(key=lambda x: x.get("createdDateTime", ""))
        last_run_datetime = convert_unixtime_to_datetime(self.last_run_time)

        for comment in m365_comments:
            comment_text: str = comment.get("comment")

            if not comment_text or comment_text.startswith(
                constants.SECOPS_COMMENT_PREFIX
            ):
                continue

            comment_created_time: datetime.datetime | None = parse_iso_datetime(
                comment.get("createdDateTime")
            )

            if comment_created_time and comment_created_time > last_run_datetime:
                comment_to_add_str: str = (
                    f"{constants.M365_COMMENT_PREFIX} {m365_alert.alert_id}: "
                    f"{comment_text}"
                )
                comments_to_add.append(comment_to_add_str)

        return comments_to_add

    def _normalize_direction(
        self,
        val: Any,
        is_key_present: bool = True,
        default: str = "Bidirectional",
    ) -> str:
        """Normalizes direction string.

        Args:
            val (Any): The parameter direction value.
            is_key_present (bool): Whether the direction key exists in JSON.
            default (str): Default direction string.

        Returns:
            str: Normalized direction string.
        """
        if not is_key_present:
            return default

        if val is None:
            return "None"

        val_str = str(val).strip() if not isinstance(val, str) else val.strip()
        val_lower = val_str.lower()

        if val_lower in ("none", "null", ""):
            return "None"
        if val_lower == "bidirectional":
            return "Bidirectional"
        if val_lower == "toxdr":
            return "toXDR"
        if val_lower == "tosecops":
            return "toSecOps"

        self.logger.info(
            f"Invalid direction value '{val}' provided. "
            f"Supported values are: 'Bidirectional', 'toXDR', "
            f"'toSecOps', 'None'."
        )
        return val_str

    def _get_str_param(self, param_name: str) -> str:
        """Safely retrieves a string parameter value from self.params."""
        val = getattr(self.params, param_name, None)
        return val.strip() if isinstance(val, str) else ""

    def _parse_sync_directions_payload(
        self,
        raw_val: str,
    ) -> dict[str, str]:
        """Processes raw 'Sync Direction' string into direction map."""
        try:
            data = json.loads(raw_val)
            if not isinstance(data, dict):
                self.logger.info(
                    f"Invalid JSON format for 'Sync Direction' parameter: "
                    f"'{raw_val}'. Skipping synchronization."
                )
                return {"Status": "Invalid", "Comments": "Invalid"}

            status_present = "Status" in data
            comments_present = "Comments" in data

            return {
                "Status": self._normalize_direction(
                    data.get("Status"), is_key_present=status_present
                ),
                "Comments": self._normalize_direction(
                    data.get("Comments"), is_key_present=comments_present
                ),
            }
        except Exception as e:
            self.logger.info(
                f"Failed to parse 'Sync Direction' JSON parameter "
                f"'{raw_val}': {e}. Skipping synchronization."
            )
            return {"Status": "Invalid", "Comments": "Invalid"}

    def _parse_sync_directions(self) -> dict[str, str]:
        """Parses the 'Sync Direction' job parameter JSON string.

        Returns:
            dict[str, str]: Normalized directions for Status and Comments.
        """
        if getattr(self, "_cached_sync_directions", None) is not None:
            return self._cached_sync_directions

        raw_val = self._get_str_param("sync_direction")
        if not raw_val:
            res = {"Status": "Bidirectional", "Comments": "Bidirectional"}
            self._cached_sync_directions = res
            return res

        res = self._parse_sync_directions_payload(raw_val)
        self._cached_sync_directions = res
        return res

    def _load_closed_reason_mapping_raw_data(
        self,
        raw_val: str,
    ) -> SingleJson:
        """Loads and validates mapping raw data as a dictionary.

        Raises:
            Microsoft365DefenderException: If raw_val is invalid or not a dict.
        """
        try:
            raw_mapping = json.loads(raw_val)
        except Exception as e:
            self.logger.info(
                f"Failed to parse 'Closed Reason Mapping' JSON parameter "
                f"'{raw_val}': {e}."
            )
            raise Microsoft365DefenderException(
                f"Failed to parse 'Closed Reason Mapping' JSON: {e}."
            ) from e

        if not isinstance(raw_mapping, dict):
            self.logger.info(
                f"Invalid JSON format for 'Closed Reason Mapping' "
                f"parameter: '{raw_val}'."
            )
            raise Microsoft365DefenderException(
                "'Closed Reason Mapping' must be a JSON object."
            )

        return raw_mapping

    def _normalize_mapping_keys(
        self,
        raw_mapping: SingleJson,
    ) -> SingleJson:
        """Normalizes keys by stripping braces and handling pipe & reason spacing.

        Raises:
            Microsoft365DefenderException: If mandatory 'Fallback' key missing.
        """
        mapping = {}
        for key, val in raw_mapping.items():
            clean_key = key.replace("{", "").replace("}", "").strip()
            if not clean_key:
                clean_key = key.strip()

            if "|" in clean_key:
                parts = clean_key.split("|", 1)
                reason_part = parts[0].strip()
                root_cause_part = parts[1].strip()
                reason_without_spaces = reason_part.replace(" ", "")

                mapping[f"{reason_part} | {root_cause_part}"] = val
                mapping[f"{reason_part}|{root_cause_part}"] = val
                mapping[
                    f"{reason_without_spaces} | {root_cause_part}"
                ] = val
                mapping[
                    f"{reason_without_spaces}|{root_cause_part}"
                ] = val
            else:
                mapping[clean_key] = val
                mapping[clean_key.replace(" ", "")] = val

        if "Fallback" not in mapping:
            raise Microsoft365DefenderException(
                "'Closed Reason Mapping' JSON must explicitly include a "
                "'Fallback' entry."
            )

        return mapping

    def _parse_closed_reason_mapping(self) -> SingleJson:
        """Parses the 'Closed Reason Mapping' job parameter JSON string.

        Returns:
            SingleJson: Normalized mapping dictionary.

        Raises:
            Microsoft365DefenderException: If JSON format is invalid or
                missing 'Fallback' key.
        """
        if getattr(self, "_cached_closed_reason_mapping", None) is not None:
            return self._cached_closed_reason_mapping

        raw_val = self._get_str_param("closed_reason_mapping")
        if not raw_val:
            raw_val = constants.DEFAULT_CLOSED_REASON_MAPPING_JSON

        raw_mapping = self._load_closed_reason_mapping_raw_data(raw_val)
        mapping = self._normalize_mapping_keys(raw_mapping)
        self._cached_closed_reason_mapping = mapping
        return mapping

    def _to_camel_case(self, s: str) -> str:
        """Converts a spaced or comma-separated string into camelCase."""
        clean_s = s.replace(",", " ").strip()
        words = clean_s.split()
        if not words:
            return s
        if len(words) == 1:
            return words[0][0].lower() + words[0][1:]
        return words[0].lower() + "".join(w.capitalize() for w in words[1:])

    def _is_valid_mapping_value(self, value: Any) -> bool:
        """Checks if a mapping string value is valid and non-placeholder."""
        if value is None:
            return False
        return str(value).strip().lower() not in (
            "",
            "none",
            "null",
            "unclassified",
            "unknown",
            "unknownfuturevalue",
        )

    def _normalize_closure_classification_and_determination(
        self,
        classification: Any,
        determination: Any,
    ) -> tuple[str, str | None]:
        """Normalizes classification and determination strings to Graph API enums."""
        if classification is None or str(classification).lower() in (
            "none",
            "null",
            "",
        ):
            norm_class = "unknownFutureValue"
        else:
            class_str = str(classification).strip()
            class_key = class_str.lower().replace(",", "").replace(" ", "")
            norm_class = constants.CLASSIFICATION_MAP.get(class_key)
            if not norm_class:
                norm_class = self._to_camel_case(class_str)

        if determination is None or str(determination).lower() in (
            "none",
            "null",
            "",
        ):
            norm_det = None
        else:
            det_str = str(determination).strip()
            det_key = det_str.lower().replace(",", "").replace(" ", "")
            norm_det = constants.DETERMINATION_MAP.get(det_key)
            if not norm_det:
                norm_det = self._to_camel_case(det_str)

        if norm_class in ("unclassified", "unknown", "unknownFutureValue"):
            if (
                norm_class in ("unclassified", "unknown")
                or norm_det is None
                or norm_det == "other"
            ):
                norm_class = "unknownFutureValue"
                norm_det = "other"

        return (norm_class, norm_det)

    def _get_m365_fallback_closure_details(
        self,
    ) -> tuple[str | None, str | None]:
        """Gets the Fallback closure details from Closed Reason Mapping."""
        mapping = self._parse_closed_reason_mapping()
        entry = mapping.get("Fallback", {})
        classification = entry.get("classification")
        determination = entry.get("determination")

        return self._normalize_closure_classification_and_determination(
            classification, determination
        )

    def _find_closure_mapping_entry(
        self,
        mapping: SingleJson,
        clean_reason: str,
        clean_root_cause: str,
    ) -> tuple[SingleJson | None, str, str]:
        """Finds matching mapping entry based on closure reason and root cause.

        Returns:
            tuple[SingleJson | None, str, str]: Matched entry, key_with_spaces,
            and matched_key string.
        """
        key_with_spaces = (
            f"{clean_reason} | {clean_root_cause}"
            if clean_root_cause
            else clean_reason
        )
        key_without_spaces = (
            f"{clean_reason}|{clean_root_cause}"
            if clean_root_cause
            else clean_reason
        )

        mapping_lower = {k.lower(): v for k, v in mapping.items()}
        entry = None
        matched_key = ""

        if key_with_spaces.lower() in mapping_lower:
            entry = mapping_lower[key_with_spaces.lower()]
            matched_key = key_with_spaces
        elif key_without_spaces.lower() in mapping_lower:
            entry = mapping_lower[key_without_spaces.lower()]
            matched_key = key_without_spaces
        elif (
            self._is_valid_mapping_value(clean_reason)
            and clean_reason.lower() in mapping_lower
        ):
            entry = mapping_lower[clean_reason.lower()]
            matched_key = clean_reason

        return entry, key_with_spaces, matched_key

    def _resolve_closure_entry(
        self,
        mapping: SingleJson,
        key_with_spaces: str,
        clean_reason: str,
        entry: SingleJson | None,
        matched_key: str,
    ) -> tuple[SingleJson, bool]:
        """Validates entry and logs fallback or matched closure details.

        Returns:
            tuple[SingleJson, bool]: Resolved mapping entry dict and is_fallback flag.
        """
        has_valid_entry = (
            entry is not None
            and isinstance(entry, dict)
            and self._is_valid_mapping_value(entry.get("classification"))
            and self._is_valid_mapping_value(entry.get("determination"))
        )

        if not has_valid_entry:
            self.logger.info(
                f"No closure mapping entry found for '{key_with_spaces}'. "
                "Using Fallback mapping."
            )
            return mapping.get("Fallback", {}), True

        if matched_key != key_with_spaces and matched_key == clean_reason:
            self.logger.info(
                f"No exact closure mapping entry found for "
                f"'{key_with_spaces}'. Falling back to single reason "
                f"entry '{clean_reason}': "
                f"classification='{entry.get('classification')}', "
                f"determination='{entry.get('determination')}'."
            )
        else:
            self.logger.info(
                f"Found closure mapping entry for '{matched_key}': "
                f"classification='{entry.get('classification')}', "
                f"determination='{entry.get('determination')}'."
            )

        return entry, False

    def _get_m365_closure_details(
        self,
        soar_closure_reason: str,
        soar_root_cause: str = "",
    ) -> tuple[str | None, str | None, bool]:
        """Gets the Microsoft XDR Defender alert's closure details.

        Args:
            soar_closure_reason (str): Closure reason for SecOps case.
            soar_root_cause (str): Root cause for SecOps case.

        Returns:
            tuple[str | None, str | None, bool]: A tuple containing the
            classification, determination, and boolean for Fallback used.
        """
        mapping = self._parse_closed_reason_mapping()
        clean_reason = soar_closure_reason.strip()
        clean_root_cause = soar_root_cause.strip()

        entry, key_with_spaces, matched_key = self._find_closure_mapping_entry(
            mapping, clean_reason, clean_root_cause
        )
        resolved_entry, is_fallback = self._resolve_closure_entry(
            mapping, key_with_spaces, clean_reason, entry, matched_key
        )

        norm_class, norm_det = (
            self._normalize_closure_classification_and_determination(
                resolved_entry.get("classification"),
                resolved_entry.get("determination"),
            )
        )

        return (norm_class, norm_det, is_fallback)

    def _build_incident_to_alerts_map(
        self, job_case: JobCase
    ) -> dict[str, list[AlertCard]]:
        """Builds a map of parent incident ID to active open AlertCards."""
        incident_to_alerts_map: dict[str, list[AlertCard]] = {}
        for alert in job_case.case_detail.alerts:
            valid_ticket_id = (
                hasattr(alert, "ticket_id")
                and alert.ticket_id
                and str(alert.ticket_id).isdigit()
            )
            if valid_ticket_id and alert.status != CaseDataStatus.CLOSED.value:
                incident_to_alerts_map.setdefault(
                    str(alert.ticket_id),
                    []
                ).append(alert)
        return incident_to_alerts_map

    def _sync_parent_incident(
        self,
        job_case: JobCase,
        parent_incident_id: str,
        alerts: list[AlertCard],
        total_incidents: int,
    ) -> None:
        """Fetches parent incident details and syncs redirection or name changes."""
        try:
            parent_incident = self.manager.get_incident(parent_incident_id)

            parent_incident_status = parent_incident.raw_data.get("status", "")
            if parent_incident_status.lower() == constants.REDIRECTED_TAG:
                self._close_alerts_due_to_redirection(
                    job_case,
                    parent_incident_id,
                    alerts,
                )
                case_name = job_case.case_detail.name
                if (
                    parent_incident.incident_name
                    and case_name != parent_incident.incident_name
                ):
                    if total_incidents == 1:
                        self._sync_case_name(job_case, parent_incident)
                    else:
                        self.logger.info(
                            f"SOAR Case {job_case.case_detail.id_} name differs"
                            f" from parent incident {parent_incident_id} name"
                            f" '{parent_incident.incident_name}', but the case"
                            " contains active alerts from multiple parent"
                            " incidents. Skipping case renaming."
                        )

        except Exception as e:
            is_not_found = (
                isinstance(e, NotFoundItemException)
                or e.__class__.__name__ == "NotFoundItemException"
            )
            if is_not_found:
                self.logger.warn(
                    f"Parent incident {parent_incident_id} wasn't found in "
                    f"Microsoft 365 Defender: {e}"
                )
            else:
                self.logger.error(
                    "Failed to fetch or sync status for parent incident"
                    f" {parent_incident_id}: {e}"
                )

    def sync_status(self, job_case: JobCase) -> None:
        """Syncing status between Microsoft Defender alerts and SecOps cases/alerts.

        Args:
            job_case (JobCase): The SecOps case to sync status for.
        """
        directions = self._parse_sync_directions()
        status_dir = directions["Status"]

        if status_dir == "None":
            if not getattr(self, "_logged_disabled_status_sync", False):
                self.logger.info(
                    "Status synchronization is disabled (Sync Direction for "
                    f"'Status' is set to '{status_dir}')."
                )
                self._logged_disabled_status_sync = True
            return

        incident_to_alerts_map = self._build_incident_to_alerts_map(job_case)

        if status_dir in ("Bidirectional", "toSecOps"):
            for parent_incident_id, alerts in incident_to_alerts_map.items():
                self._sync_parent_incident(
                    job_case,
                    parent_incident_id,
                    alerts,
                    len(incident_to_alerts_map),
                )

        res = job_case.get_status_to_sync(constants.M365_STATUS_RESOLVED)

        if status_dir in ("Bidirectional", "toSecOps"):
            self._sync_product_status_to_case(res, job_case)

        if status_dir in ("Bidirectional", "toXDR"):
            self._sync_case_status_to_product(res, job_case)

    def _close_alerts_due_to_redirection(
        self,
        job_case: JobCase,
        parent_incident_id: str,
        alerts: list[AlertCard]
    ) -> None:
        """Closes only the specified alerts in the SOAR case because their
        parent incident was redirected."""
        self.logger.info(
            f"Parent incident {parent_incident_id} is redirected. "
            "Closing alerts associated with it: "
            f"{[alert.identifier for alert in alerts]}."
        )
        for alert in alerts:
            self.sync_product_status_to_case(
                job_case.case_detail.id_,
                alert.identifier,
                constants.REASON_RESOLVED,
                constants.ROOT_CAUSE_OTHER,
                f"{constants.M365_COMMENT_PREFIX}{parent_incident_id}: Closed because"
                " the incident was correlated/merged in Microsoft Defender XDR."
            )
            self._remove_synced_entries(
                synced_list=[
                    (
                        job_case.case_detail.id_,
                        get_m365_alert_id_from_soar_alert(self.soar_job, alert),
                    )
                ]
            )

    def _sync_case_name(self, job_case: JobCase, parent_incident: Incident) -> None:
        """Syncs the SOAR case name with the M365 parent incident name if it changed."""
        if not parent_incident.incident_name:
            return

        current_case_name = job_case.case_detail.name
        if current_case_name != parent_incident.incident_name:
            self.logger.info(
                f"Case {job_case.case_detail.id_} name '{current_case_name}' "
                f"differs from parent incident name '{parent_incident.incident_name}'. "
                "Renaming case."
            )
            rename_case(
                self.soar_job,
                job_case.case_detail.id_,
                parent_incident.incident_name,
            )

    def _sync_product_status_to_case(
        self,
        res: JobStatusResult,
        job_case: JobCase,
    ) -> None:
        """Syncs Microsoft Defender alert status to SecOps case/alert status.

        Args:
            res (JobStatusResult): The result object containing status sync information.
            job_case (JobCase): The SecOps case to sync status for.
        """
        for alert, meta in res.alerts_to_close_in_soar:
            reason, root_cause = self._get_secops_closure_details(meta.closure_reason)
            comment = (
                f"{constants.M365_COMMENT_PREFIX}{meta.incident_number}: "
                "Alert was closed"
            )
            self.sync_product_status_to_case(
                job_case.case_detail.id_,
                alert.identifier,
                reason,
                root_cause,
                comment,
            )
            self._remove_synced_entries(
                synced_list=[(job_case.case_detail.id_, f"{meta.incident_number}")],
            )

    def _sync_case_status_to_product(
        self,
        res: JobStatusResult,
        job_case: JobCase,
    ) -> None:
        """Syncs SecOps case/alert status to Microsoft Defender alert status.

        Args:
            res (JobStatusResult): The result object containing status sync information.
            job_case (JobCase): The SecOps case to sync status for.
        """
        if not res.incidents_to_close_in_product:
            self.logger.info(
                "No closed SecOps alerts/cases found to sync to Defender "
                f"XDR for case {job_case.case_detail.id_}."
            )
            return

        for req in res.incidents_to_close_in_product:
            if req["is_case_closed"]:
                case_details = self.soar_job.get_case_closure_details(
                    [job_case.case_detail.id_]
                )
                closure_details = case_details[0] if case_details else {}
                closure_reason = closure_details.get("reason", "")
                root_cause = (
                    closure_details.get("root_cause")
                    or closure_details.get("rootCause")
                    or ""
                )
            else:
                closure_reason = req.get("reason", "")
                root_cause = (
                    req.get("root_cause")
                    or req.get("rootCause")
                    or ""
                )

            classification, determination, _ = self._get_m365_closure_details(
                closure_reason, root_cause
            )
            comment = self.get_secops_closure_comment(job_case, req)
            comment = (
                f"{constants.SECOPS_COMMENT_PREFIX}{job_case.case_detail.id_}: "
                f"{comment}"
            )
            alert_id = req["meta"].incident_number
            try:
                self.manager.update_alert(
                    alert_id,
                    constants.M365_STATUS_RESOLVED,
                    classification,
                    determination,
                )
                self.manager.add_comment_to_alert(alert_id, comment)
                self.logger.info(
                    "Successfully updated alert status "
                    f"'{constants.M365_STATUS_RESOLVED}' for alert "
                    f"{alert_id} with classification '{classification}' and "
                    f"determination '{determination}'."
                )
            except Exception as e:
                is_not_found = (
                    isinstance(e, NotFoundItemException)
                    or e.__class__.__name__ == "NotFoundItemException"
                )
                if is_not_found:
                    self.logger.warn(
                        f"Alert {alert_id} wasn't found in Microsoft 365 Defender: {e}"
                    )
                else:
                    fb_class, fb_det = self._get_m365_fallback_closure_details()
                    self.logger.warn(
                        f"Failed to update alert {alert_id} with mapped classification "
                        f"'{classification}' and determination '{determination}': {e}. "
                        "Retrying with default Fallback mapping."
                    )
                    try:
                        self.manager.update_alert(
                            alert_id,
                            constants.M365_STATUS_RESOLVED,
                            fb_class,
                            fb_det,
                        )
                        self.manager.add_comment_to_alert(alert_id, comment)
                        self.logger.info(
                            "Successfully updated alert status "
                            f"'{constants.M365_STATUS_RESOLVED}' for alert "
                            f"{alert_id} using Fallback mapping (classification "
                            f"'{fb_class}', determination '{fb_det}')."
                        )
                    except Exception as fb_err:
                        self.logger.error(
                            f"Failed to update alert {alert_id} status using "
                            f"Fallback mapping: {fb_err}"
                        )
            self._remove_synced_entries(
                synced_list=[(job_case.case_detail.id_, f"{alert_id}")],
            )

    def _get_secops_closure_details(self, m365_classification: str) -> tuple[str, str]:
        """Gets the SecOps case's/alert's closure details.

        Args:
            m365_classification (str): The classification of the Microsoft Defender
            alert.

        Returns:
            tuple[str, str]: A tuple containing the closure reason and root cause
            for SecOps.
        """
        if m365_classification == constants.CLASSIFICATION_TRUE_POSITIVE:
            return (
                constants.REASON_MALICIOUS,
                CloseCaseOrAlertMaliciousRootCauses.OTHER.value,
            )

        if m365_classification == constants.CLASSIFICATION_FALSE_POSITIVE:
            return (
                constants.REASON_NOT_MALICIOUS,
                CloseCaseOrAlertNotMaliciousRootCauses.OTHER.value,
            )

        return (
            constants.REASON_RESOLVED,
            CloseCaseOrAlertInconclusiveRootCauses.NO_CLEAR_CONCLUSION.value,
        )


    def get_comments_to_sync(
        self,
        job_case: JobCase,
        product_comment_prefix: str,
        case_comment_prefix: str,
        product_incident_key="name",
    ) -> None:
        """Gets comments to sync between SecOps case and product alerts.

        Args:
            job_case (JobCase): The job case for which to sync comments.
            product_comment_prefix (str): The prefix for product comments.
            case_comment_prefix (str): The prefix for case comments.
            product_incident_key (str): The key for the product alert.
        """
        comments_to_sync = self.get_comment_to_sync(
            job_case,
            product_comment_prefix=product_comment_prefix,
            case_comment_prefix=case_comment_prefix,
            product_incident_key=product_incident_key,
        )

        return comments_to_sync

    def get_comment_to_sync(
        self,
        job_case: JobCase,
        product_comment_prefix: str,
        case_comment_prefix: str,
        product_incident_key="name",
    ) -> list[SingleJson]:
        """Gets comments to sync between SecOps case and product alerts.

        Args:
            job_case (JobCase): The job case for which to sync comments.
            product_comment_prefix (str): The prefix for product comments.
            case_comment_prefix (str): The prefix for case comments.
            product_incident_key (str): The key for the product alert.

        Returns:
            list[SingleJson]: A list of comments to sync.
        """
        case_comments_hashes = job_case.get_case_comments_hashes()
        product_comments_hashes = self.get_product_comments_hashes(job_case)

        product_comments_sync_to_case = self._get_product_comments_to_sync(
            job_case,
            product_comment_prefix,
            case_comment_prefix,
            product_incident_key,
            case_comments_hashes,
        )
        case_comments_sync_to_product = self._get_case_comments_to_sync(
            job_case,
            case_comment_prefix,
            product_comment_prefix,
            product_comments_hashes,
        )

        return JobCommentsResult(
            product_comments_sync_to_case=product_comments_sync_to_case,
            case_comments_sync_to_product=case_comments_sync_to_product,
        )

    def _get_product_comments_to_sync(
        self,
        job_case: JobCase,
        product_comment_prefix: str,
        case_comment_prefix: str,
        product_incident_key: str,
        case_comments_hashes: set,
    ) -> list[str]:
        """Gets product comments to sync to the SecOps case.

        Args:
            job_case (JobCase): The job case for which to sync comments.
            product_comment_prefix (str): The prefix for product comments.
            case_comment_prefix (str): The prefix for case comments.
            product_incident_key (str): The key for the product alert.
            case_comments_hashes (set): A set of hashes of the case comments for
            comparison.

        Returns:
            list[str]: A list of product comments to sync to the case.
        """
        product_comments_sync_to_case = []

        for alert in job_case.case_detail.alerts:
            if not self._is_valid_alert(alert):
                continue

            alert_identifier = alert.alert_group_identifier
            incident_identifier = getattr(alert.incident, product_incident_key)

            for product_comment in alert.incident.comments:
                comment_text = self._extract_comment_text(product_comment)
                comment_with_product_prefix = self._format_product_comment(
                    product_comment_prefix, incident_identifier, comment_text
                )
                comment_hash = job_case._generate_string_hash(
                    comment_with_product_prefix
                )
                if (
                    job_case._is_valid_product_comment(
                        comment_text, case_comment_prefix
                    )
                    and comment_hash not in case_comments_hashes
                ):
                    comment = f"{alert_identifier}: {comment_with_product_prefix}"
                    product_comments_sync_to_case.append(comment)

        return product_comments_sync_to_case

    def _is_valid_alert(self, alert: AlertCard) -> bool:
        """Checks if the SecOps alert is valid for comment syncing.

        Args:
            alert (AlertCard): The SecOps alert to check.

        Returns:
            bool: True if the alert is valid for comment syncing, False otherwise.
        """
        return (
            hasattr(alert, "incident")
            and alert.incident is not None
            and bool(getattr(alert.incident, "alert_id", None))
        )

    def _extract_comment_text(self, product_comment: str) -> str:
        """Extracts the text from a product comment.

        Args:
            product_comment (str): The product comment to extract text from.

        Returns:
            str: The extracted comment text.
        """
        raw_comment = str(product_comment).strip()

        if ":" in raw_comment:
            return raw_comment.rsplit(":", maxsplit=1)[-1].strip()

        return raw_comment

    def _format_product_comment(
        self,
        product_comment_prefix: str,
        incident_identifier: str,
        comment_text: str,
    ) -> str:
        """Formats a product comment with the appropriate prefix.

        Args:
            product_comment_prefix (str): The prefix for product comments.
            incident_identifier (str): The identifier for the product alert.
            comment_text (str): The text of the comment.

        Returns:
            str: The formatted product comment.
        """
        return f"{product_comment_prefix}{incident_identifier}: {comment_text}"

    def _get_case_comments_to_sync(
        self,
        job_case: JobCase,
        case_comment_prefix: str,
        product_comment_prefix: str,
        product_comments_hashes: set,
    ) -> list[str]:
        """Gets case comments to sync to the product.

        Args:
            job_case: The job case for which to sync comments.
            case_comment_prefix: The prefix for case comments.
            product_comment_prefix: The prefix for product comments.
            product_comments_hashes: A set of hashes of the product comments for
            comparison.

        Returns:
            list[str]: A list of case comments to sync to the product.
        """
        case_comments_sync_to_product = []
        for case_comment in job_case.case_comments:
            comment_text = case_comment["comment"]

            if product_comment_prefix in comment_text:
                continue

            comment_with_case_prefix = self._format_case_comment(
                case_comment_prefix, job_case.case_detail.id_, comment_text
            )
            comment_hash = job_case._generate_string_hash(comment_with_case_prefix)
            if (
                job_case._is_valid_secops_comment(case_comment, product_comment_prefix)
                and comment_hash not in product_comments_hashes
            ):
                case_comments_sync_to_product.append(comment_with_case_prefix)
        return case_comments_sync_to_product

    def _format_case_comment(
        self,
        case_comment_prefix: str,
        case_id: str,
        comment_text: str,
    ) -> str:
        """Formats a case comment with the appropriate prefix.

        Args:
            case_comment_prefix (str): The prefix for case comments.
            case_id (str): The identifier for the SecOps case.
            comment_text (str): The text of the comment.

        Returns:
            str: The formatted case comment.
        """
        return f"{case_comment_prefix}{case_id}: {comment_text}"

    def get_product_comments_hashes(self, job_case) -> list[str]:
        """Gets hashes of product comments for comparison.

        Args:
            job_case: The job case to extract product comment hashes from.

        Returns:
            list[str]: A list of hashes of the product comments.
        """
        comments_hashes = []

        for alert in job_case.case_detail.alerts:
            if not self._is_valid_alert(alert):
                continue
            for comment in alert.incident.comments:
                comments_hashes.append(
                    job_case._generate_string_hash(str(comment) or "")
                )

        return comments_hashes

    def sync_comments(self, job_case: JobCase) -> None:
        """Sync comments between SecOps and Microsoft Defender.

        Args:
            job_case (JobCase): The SecOps case to sync comments for.
        """
        directions = self._parse_sync_directions()
        comments_dir = directions["Comments"]

        if (
            comments_dir == "None"
            or job_case.case_detail.status == CaseDataStatus.CLOSED
        ):
            if comments_dir == "None":
                if not getattr(self, "_logged_disabled_comments_sync", False):
                    self.logger.info(
                        "Comment synchronization is disabled (Sync Direction "
                        f"for 'Comments' is set to '{comments_dir}')."
                    )
                    self._logged_disabled_comments_sync = True
            return

        comments_to_sync = self.get_comments_to_sync(
            job_case=job_case,
            product_comment_prefix=constants.M365_COMMENT_PREFIX,
            case_comment_prefix=constants.SECOPS_COMMENT_PREFIX,
            product_incident_key="alert_id",
        )

        if comments_dir in ("Bidirectional", "toSecOps"):
            self.sync_product_comments_to_case(
                case_id=job_case.case_detail.id_,
                comments=comments_to_sync.product_comments_sync_to_case,
            )

        if comments_dir in ("Bidirectional", "toXDR"):
            self.sync_case_comments_to_product(
                job_case=job_case,
                comments=comments_to_sync.case_comments_sync_to_product,
            )

    def sync_case_comments_to_product(
        self,
        job_case: JobCase,
        comments: list[str],
    ) -> None:
        """Syncs SecOps comments to Microsoft Defender.

        Args:
            job_case (JobCase): The SecOps case to sync comments for.
            comments (list[str]): A list of comments to sync to Microsoft Defender.
        """
        for alert in self._get_unique_alerts(job_case):
            for block in self._chunk_comments(comments):
                self._push_comment_to_alert(alert, block)

    def _get_unique_alerts(self, job_case: JobCase) -> list[AlertCard]:
        """Gets open alerts from the job case.

        Args:
            job_case (JobCase): The SecOps case to extract alerts from.

        Returns:
            list[AlertCard]: A list of unique open AlertCard objects from the case.
        """
        unique_alerts = []

        for alert in job_case.case_detail.alerts:
            if not self._is_valid_alert(alert):
                continue
            if alert.incident.raw_data.get("status") == constants.M365_STATUS_RESOLVED:
                continue
            unique_alerts.append(alert)

        return unique_alerts

    def _chunk_comments(self, comments: list[str]) -> list[str]:
        """Chunks comments into blocks of maximum allowed characters.

        Args:
            comments (list[str]): A list of comments to chunk.

        Returns:
            list[str]: A list of comment blocks, each within the character limit.
        """
        blocks, current, length = [], [], 0

        for comment in comments:
            extra_length = len(comment) + (1 if current else 0)
            if length + extra_length > constants.MAX_CHARS:
                blocks.append("\n".join(current))
                current, length = [comment], len(comment)
            else:
                current.append(comment)
                length += extra_length

        if current:
            blocks.append("\n".join(current))

        return blocks

    def _push_comment_to_alert(self, alert: AlertCard, text: str) -> None:
        """Pushes a comment block to the alert.

        Args:
            alert (AlertCard): The alert to push the comment to.
            text (str): The comment text to push.
        """
        try:
            self.manager.add_comment_to_alert(alert.incident.alert_id, text)
            self.logger.info(
                "Successfully synced comments from SecOps to Defender alert "
                f"{alert.incident.alert_id}."
            )
        except Exception as e:
            is_not_found = (
                isinstance(e, NotFoundItemException)
                or e.__class__.__name__ == "NotFoundItemException"
            )
            if is_not_found:
                self.logger.warn(
                    f"Alert {alert.incident.alert_id} wasn't found in "
                    f"Microsoft 365 Defender when adding comment: {e}"
                )
            else:
                self.logger.error(
                    "Failed to sync comments from SecOps to Defender alert "
                    f"{alert.incident.alert_id}: {e}"
                )

    def sync_assignee(self, job_case: JobCase) -> None:
        """Defender -> SecOps Assignee Sync.

        Args:
            job_case (JobCase): The SecOps case to sync assignee for.
        """
        if (
            not self.params.sync_assignee
            or job_case.case_detail.status == CaseDataStatus.CLOSED
        ):
            return

        res = self.get_assignee_to_sync(job_case)

        if res.target_user:
            current_case_user = self.get_secops_assignee(job_case)
            secops_assignee = (
                current_case_user.raw_data.get("email")
                if current_case_user and current_case_user.raw_data
                else ""
            )

            if secops_assignee != res.target_user.get("email"):
                self.sync_assignee_to_case(
                    res.alert.identifier,
                    job_case.case_detail.id_,
                    res.target_user.get("displayName"),
                )

    def sync_severity(self, job_case: JobCase) -> None:
        """Defender -> SecOps Priority Sync.

        Args:
            job_case (JobCase): The SecOps case to sync severity for.
        """

    def sync_tags(self, job_case: JobCase) -> None:
        """Bidirectional Tag Sync.

        Args:
            job_case (JobCase): The SecOps case to sync tags for.
        """

    def remove_synced_data_from_db(
        self,
        job_case: JobCase,
        product_details: list[AlertWithEvidence],
    ) -> None:
        """
        Removes synced entries from the DB if both the case alert and the product alert
        are closed.

        Args:
            job_case (JobCase): The SecOps case to check for closed alerts.
            product_details (list[AlertWithEvidence]): A list of AlertWithEvidence
            datamodel objects representing the product details to check for
            closed status.
        """
        for alert in job_case.case_detail.alerts:
            alert_id = get_m365_alert_id_from_soar_alert(self.soar_job, alert)
            if not alert_id:
                continue

            matching_product = next(
                (p for p in product_details if p.alert_id == alert_id),
                None,
            )

            case_id = job_case.case_detail.id_
            entry = (case_id, f"{alert_id}")

            if not matching_product:
                if (
                    self.manager
                    and alert_id in getattr(self.manager, "not_found_alert_ids", set())
                ):
                    self.logger.info(
                        f"Alert {alert_id} in case {case_id} was not found in "
                        "Defender details. Removing from synced tracking state."
                    )
                    self._remove_synced_entries([entry])
                else:
                    self.logger.warn(
                        f"Alert {alert_id} in case {case_id} was not returned from "
                        "Defender details (possibly due to fetch error)."
                        " Keeping in synced tracking state."
                    )
                continue

            if self.is_alert_and_product_closed(job_case, matching_product):
                self._remove_synced_entries([entry])


def main() -> NoReturn:
    SyncAlerts().start()


if __name__ == "__main__":
    main()
