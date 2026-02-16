from __future__ import annotations

from abc import abstractmethod
import itertools
import json
from typing import Generic, Iterator, Any
import math
from requests.exceptions import HTTPError, JSONDecodeError
from SiemplifyUtils import (
    convert_unixtime_to_datetime,
    unix_now,
)
from .base_job import Job
from .data_models import (
    JobCase,
    JobTagsResult,
    JobAssigneeResult,
    ProductTagsData,
)
from ..utils import nativemethod, is_native
from ...consts import (
    COMMENTS_MODIFICATION_TIME_FILTER,
    INCREMENT_CASE_UPDATED_TIME_BY_MS,
    JOB_SYNC_LIMIT,
    UNIX_FORMAT,
    CASE_ALERTS_LIMIT,
    TAGS,
)
from ..interfaces import ApiClient
from ...data_models import CaseDetails
from ...rest.soar_api import (
    add_tags_to_case_in_bulk,
    get_case_overview_details,
    get_case_close_comment,
    get_cases_by_timestamp_filter,
    remove_case_tag,
    set_alert_priority,
)
from ...soar_ops import get_user_by_id, get_users_profile_cards_with_pagination
from ...types import SingleJson
from ...utils import merge_and_sort

SyncItem = list[str]
SyncData = dict[str, SyncItem]


class BaseSyncJob(Job, Generic[ApiClient]):
    """
    A base template for creating stateful, bi-directional synchronization jobs.
    """

    def __init__(
        self,
        job_name: str,
        context_identifier: str,
        tags_identifiers: list[str],
    ):
        super().__init__(name=job_name)
        self.tags_identifiers: list[str] = tags_identifiers
        self.context_identifier: str = context_identifier
        self.sync_limit: int = JOB_SYNC_LIMIT
        self.product_alerts_limit: int = CASE_ALERTS_LIMIT
        self.processed_items: SyncData = {}
        self.last_run_time: int = 0
        self.current_run_latest_timestamp_ms: int = 0
        self.job_cases_to_sync: list[JobCase] = []
        self.failed_cases: list[JobCase] = []
        self._secops_user_list: list[dict] = []
        self.job_completed_successfully: bool = False
        self._cached_unix_now: int = 0

    def get_last_run_time(self) -> int:
        """
        Retrieves the last successful run time of the job.
        If it's the first run, it calculates a start time based on 
        'Max Hours Backwards'.
        """
        return self._get_job_last_success_time(
            offset_with_metric={"hours": self.params.max_hours_backwards},
            time_format=UNIX_FORMAT,
            print_value=True,
        )

    def _read_ids(self) -> SyncData:
        """Reads processed items data from a file or database.

        Note: Uses json.loads() here because the data is retrieved from a trusted source
        (get_job_context_property) and is not user-provided or external.
        """
        context_str: str = self.soar_job.get_job_context_property(
            self.name_id,
            self.context_identifier,
        )
        if context_str:
            return json.loads(context_str)
        return {}

    def _write_ids(self, updated_items: SyncData) -> None:
        """Writes processed items data to a file or database after filtering."""
        self.soar_job.set_job_context_property(
            identifier=self.name_id,
            property_key=self.context_identifier,
            property_value=json.dumps(updated_items),
        )

    def _remove_synced_entries(
        self,
        synced_list: list[tuple[str, int]],
    ) -> None:
        """Removes successfully synced alerts from the tracking dictionary."""
        for case_id, alert_id in synced_list:
            case_id = str(case_id)
            items = self.processed_items.get(case_id)
            if not items:
                continue
            try:
                items.remove(alert_id)
            except ValueError:
                continue
            if not items:
                del self.processed_items[case_id]

    def _get_cases_to_sync(self) -> list[JobCase]:
        final_prepared_cases: list[JobCase] = []
        cases_by_modified_timestamp = self._get_case_ids_by_timestamp()
        modified_synced_case_ids = self._get_case_ids_by_timestamp(
            list(self.processed_items)
        )
        sorted_modified_ids = merge_and_sort(
            cases_by_modified_timestamp,
            modified_synced_case_ids
        )
        if not is_native(self.modified_synced_case_ids_by_product):
            synced_incident_ids: Iterator[str] = itertools.chain.from_iterable(
                self.processed_items.values()
            )
            modified_synced_case_ids_by_product = (
                self.modified_synced_case_ids_by_product(
                    synced_incident_ids, sorted_modified_ids
                )
            )
            sorted_modified_ids = merge_and_sort(
                sorted_modified_ids, modified_synced_case_ids_by_product
            )
        potential_cases = sorted_modified_ids[: self.sync_limit]
        total_alerts_accumulated = 0
        final_prepared_ids = []
        for case_id, modification_time in potential_cases:
            try:
                case_details = get_case_overview_details(
                    self.soar_job,
                    case_id,
                    case_expand=["tags"],
                    alert_expand=["ClosureDetails"],
                )
                alert_count = len(case_details.alerts)
                if (
                    self.product_alerts_limit
                    and total_alerts_accumulated + alert_count > (
                        self.product_alerts_limit
                    )
                ):
                    if total_alerts_accumulated == 0:
                        self.logger.info(
                            f"Case {case_id} has {alert_count} alerts, exceeding "
                            f"the limit ({self.product_alerts_limit}) "
                            "alone. Processing anyway to ensure progress."
                        )
                    else:
                        self.logger.info(
                            "Alert limit reached "
                            f"({total_alerts_accumulated}/{self.product_alerts_limit})."
                            f" Skipping case {case_id} with {alert_count} "
                            "alerts for next run."
                        )
                        break
                case_details.alerts = list(reversed(case_details.alerts))
                total_alerts_accumulated += alert_count
                job_case = JobCase(
                    case_detail=case_details,
                    modification_time=modification_time
                )
                incident_ids = self._extract_product_ids_from_case(job_case)
                if incident_ids:
                    self.processed_items[case_id] = incident_ids
                    final_prepared_cases.append(job_case)
                    final_prepared_ids.append((case_id, modification_time))
            except (HTTPError, JSONDecodeError) as e:
                self.logger.info(
                    f"Could not retrieve details for new case {case_id}. "
                    f"Skipping. Error: {e}"
                )
                self.failed_cases.append((case_id, modification_time))
        self.sorted_modified_ids = final_prepared_ids
        return final_prepared_cases

    def _get_case_ids_by_timestamp(
        self,
        ids: list[str] | None = None
    ) -> list[tuple[str, int]]:
        """
        Fetches all relevant case IDs by timestamp range, filters them by tags,
        """
        start_time_ms = self.last_run_time + INCREMENT_CASE_UPDATED_TIME_BY_MS
        time_diff_ms = self._cached_unix_now - start_time_ms
        ms_per_day = 86400000.0
        duration_days = time_diff_ms / ms_per_day
        time_range_filter_value = max(1, math.ceil(duration_days))
        cases = get_cases_by_timestamp_filter(
            chronicle_soar=self.soar_job,
            start_time=self.last_run_time,
            end_time=self._cached_unix_now,
            time_range_filter=time_range_filter_value,
            environments=[self.params.environment_name],
            case_ids=[int(case_id) for case_id in ids] if ids is not None else None,
        )
        if not self.tags_identifiers:
            filtered_case_ids: list[str] = []
            for case in cases:
                if case.get("id"):
                    filtered_case_ids.append((str(case["id"]), case["updateTime"]))
            return filtered_case_ids
        return self._filter_cases_by_tags(cases)

    def _filter_cases_by_tags(
        self,
        cases: list[dict[str, Any]]
    ) -> list[tuple[str, int]]:
        """
        Filters a list of case dictionaries, returning only the IDs of cases
        that contain all of the required tags.
        """
        filtered_case_ids: list[str] = []
        for case in cases:
            case_tags_display_names = {
                tag_dict.get("displayName")
                for tag_dict in case.get("tags", [])
                if tag_dict and tag_dict.get("displayName")
            }
            case_id = case.get("id")
            if case_id and all(
                tag in case_tags_display_names for tag in self.tags_identifiers
            ):
                filtered_case_ids.append((str(case_id), case["updateTime"]))
        return filtered_case_ids

    # Abstract methods for standard synchronization actions
    @abstractmethod
    def _extract_product_ids_from_case(self, case_details: CaseDetails) -> SyncItem:
        """Fetches the IDs of the product from the case details object."""
        raise NotImplementedError

    @abstractmethod
    def sync_status(self, job_case: JobCase) -> None:
        """
        Sync status between source and target items.
        """
        raise NotImplementedError

    @abstractmethod
    def sync_comments(self, job_case: JobCase) -> None:
        """
        Sync comments between source and target items.
        """
        raise NotImplementedError

    @abstractmethod
    def sync_tags(self, job_case: JobCase) -> None:
        """
        Sync tags between source and target items.
        """
        raise NotImplementedError

    @abstractmethod
    def is_alert_and_product_closed(self, job_case: JobCase, product) -> bool:
        """
        Checks if both the alert and the product are closed.
        """
        raise NotImplementedError
    
    @abstractmethod
    def remove_synced_data_from_db(self, job_case: JobCase, product_details) -> None:
        """Removes synced data from db"""
        raise NotImplementedError

    @abstractmethod
    def sync_severity(self, source_item, target_item) -> None:
        """
        Sync severity between source and target items.
        """
        raise NotImplementedError

    @abstractmethod
    def sync_assignee(self, source_item, target_item) -> None:
        """
        Sync assignee between source and target items.
        """
        raise NotImplementedError

    @abstractmethod
    def map_product_data_to_case(self, job_case: JobCase) -> None:
        """Maps product data to the case."""
        raise NotImplementedError

    @nativemethod
    def modified_synced_case_ids_by_product(
        self,
        product_ids: list[str], 
        case_ids: list[tuple[str, int]]
    ) -> list[tuple[str, int]]:
        """
        Fetches modified synced case IDs based on the modified product IDs.
        """
        return []

    @nativemethod
    def sync_case_comments_to_product(
        self,
        job_case: JobCase,
        comments: list[str]
    ) -> None:
        """Sync case comments to the product."""
        raise NotImplementedError

    @nativemethod
    def get_comments_to_sync(
        self,
        job_case: JobCase,
        product_comment_prefix: str,
        case_comment_prefix: str,
        product_comment_key: str = "message",
        product_incident_key: str = "name",
    ) -> None:
        """Fetches comments from both the case and the product item."""
        comments_to_sync = job_case.get_comments_to_sync(
            product_comment_prefix=product_comment_prefix,
            case_comment_prefix=case_comment_prefix,
            product_comment_key=product_comment_key,
            product_incident_key=product_incident_key,
        )
        return comments_to_sync

    def sync_product_comments_to_case(self, case_id: int, comments: list[str]) -> None:
        """Sync product comments to the case."""
        for comment in comments:
            alert_identifier = comment.split(":")[0]
            comment = comment.replace(f"{alert_identifier}:", "", 1)
            self.soar_job.add_comment(
                case_id=case_id, comment=comment, alert_identifier=alert_identifier
            )
            self.logger.info(f"Successfully synced comments to case {case_id}.")

    def get_tags_to_sync(
        self,
        job_case: JobCase,
        product_tag_prefix: str,
        case_tag_prefix: str,
        product_properties_key: str = None,
        product_tags_key: str = TAGS,
    ) -> JobTagsResult:
        """Fetches tags from both the case and the product item."""
        return job_case.get_tags_to_sync(
            product_tag_prefix=product_tag_prefix,
            case_tag_prefix=case_tag_prefix,
            tag_to_exclude=self.tags_identifiers[0],
            product_properties_key=product_properties_key,
            product_tags_key=product_tags_key,
        )

    def sync_product_tags_to_case(self, case_id: int, tags: ProductTagsData) -> None:
        """Sync product tags to the case."""
        if tags.tags_to_add:
            add_tags_to_case_in_bulk(self.soar_job, [case_id], tags.tags_to_add)
            self.logger.info(f"Successfully added tags to case {case_id}.")
        if tags.tags_to_remove:
            for tag in tags.tags_to_remove:
                remove_case_tag(
                    chronicle_soar=self.soar_job,
                    case_id=case_id,
                    tag=tag,
                )
            self.logger.info(f"Successfully removed tags from case {case_id}.")

    @nativemethod
    def sync_case_tags_to_product(
        self,
        job_case: JobCase,
        tags: ProductTagsData,
    ) -> None:
        """Sync case tags to the product."""
        raise NotImplementedError

    def get_secops_assignee(self, job_case: JobCase) -> SingleJson:
        """
        Get assignee from source item.
        """
        return get_user_by_id(self.soar_job, job_case.case_detail.assigned_user)

    def sync_product_status_to_case(
        self,
        case_id: str,
        alert_id: str,
        reason: str,
        root_cause: str,
        comment: str
    ) -> None:
        """Sync product status to the case."""
        try:
            self.soar_job.close_alert(root_cause, comment, reason, case_id, alert_id)
            self.logger.info(f"Successfully closed alert {alert_id} in case {case_id}.")
        except Exception as e:
            error_message = str(e)
            if "You can not perform this action on a closed alert" in error_message:
                self.logger.warn(
                    f"Alert {alert_id} in case {case_id} was already closed "
                    "on the platform. "
                )

    def get_assignee_to_sync(self, job_case: JobCase) -> JobAssigneeResult:
        """Fetches assignee from the product item."""
        if not self._secops_user_list:
            self._secops_user_list = [
                user.raw_data for user in get_users_profile_cards_with_pagination(
                    self.soar_job
                )
            ]
        return job_case.get_assignee_to_sync(self._secops_user_list)

    def sync_assignee_to_case(
        self,
        user_display_name: str,
        case_id: str,
        alert_id: str
    ) -> None:
        """Sync assignee to the case."""
        self.soar_job.assign_case(user_display_name, case_id, alert_id)
        self.logger.info(f"Successfully synced assignee to case {case_id}.")

    def sync_severity_to_case(
        self,
        case_id: str,
        alert_identifier: str,
        alert_name: str,
        new_priority: str
    ) -> None:
        """Sync severity to the case."""
        try:
            set_alert_priority(
                self.soar_job, case_id, alert_identifier, alert_name, new_priority
            )
            self.logger.info(
                f"Successfully updated alert {alert_identifier} priority "
                f"to {new_priority}."
            )
        except Exception as e:
            self.logger.error(
                f"Failed to update priority for alert {alert_identifier}: {e}"
            )

    def get_secops_closure_comment(self, job_case: JobCase, sync_info: dict) -> str:
        """Fetches the closure comment for the Case/Alert."""
        if sync_info["is_case_closed"]:
            comment = get_case_close_comment(self.soar_job, job_case.case_detail.id_)
        else:
            comment = sync_info.get("comment")
        return comment or "Case or Alert was closed"

    def _perform_job(self) -> None:
        """Perform the main flow of the job"""
        try:
            self._cached_unix_now = unix_now()
            self.last_run_time: int = self.get_last_run_time()
            self.current_run_latest_timestamp_ms = self.last_run_time
            self.processed_items = self._read_ids()
            self.job_cases_to_sync = self._get_cases_to_sync()
            case_ids = [job_case.case_detail.id_ for job_case in self.job_cases_to_sync]
            self.logger.info(
                f"Found {len(self.job_cases_to_sync)} case ids to sync: {case_ids}"
            )
            for job_case in self.job_cases_to_sync:
                job_case.case_comments = self.soar_job.fetch_case_comments(
                    case_id=job_case.case_detail.id_,
                    time_filter_type=COMMENTS_MODIFICATION_TIME_FILTER,
                    from_timestamp=self.last_run_time,
                )
                self.map_product_data_to_case(job_case=job_case)
                self.sync_comments(job_case)
                self.sync_tags(job_case)
                self.sync_severity(job_case)
                self.sync_assignee(job_case)
                self.sync_status(job_case)
            self.job_completed_successfully = True
        except Exception as e:
            self.logger.exception(
                f"An unexpected error occurred during the sync cycle: {e}"
            )
            raise
        finally:
            self._finalize_job()

    def _finalize_job(self) -> None:
        """Perform final steps before the job script ends"""
        self._write_ids(self.processed_items)
        if self.job_completed_successfully and len(self.sorted_modified_ids) > 0:
            self.current_run_latest_timestamp_ms = self.sorted_modified_ids[-1][1]
        latest_time = self.current_run_latest_timestamp_ms
        self._save_timestamp_by_unique_id(new_timestamp=latest_time)
        self.logger.info(
            f"Saving timestamp: {latest_time} "
            f"[{convert_unixtime_to_datetime(latest_time)}]"
        )
