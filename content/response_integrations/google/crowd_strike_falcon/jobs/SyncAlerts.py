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

from typing import TYPE_CHECKING

from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime

from TIPCommon.base.action.data_models import (
    CloseCaseOrAlertInconclusiveRootCauses,
    CloseCaseOrAlertMaliciousRootCauses,
    CloseCaseOrAlertNotMaliciousRootCauses,
)
from TIPCommon.base.job.base_sync_job import BaseSyncJob
from TIPCommon.base.job.job_case import (
    JobCase,
    JobCommentsResult,
    JobStatusResult,
    SyncMetadata,
)
from TIPCommon.data_models import AlertCard, CaseDataStatus
from crowd_strike_falcon.core import constants
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core.datamodels import AlertDetails
from crowd_strike_falcon.core import utils

if TYPE_CHECKING:
    from typing import NoReturn, TypeAlias

    from TIPCommon.types import SingleJson


CaseIdModifiedTimeList: TypeAlias = list[tuple[str, int]]

class SyncAlerts(BaseSyncJob[CrowdStrikeManager]):
    def __init__(self) -> None:
        super().__init__(
            job_name=constants.SYNC_ALERTS_JOB_NAME,
            context_identifier=constants.SYNC_ALERTS_CONTEXT_IDENTIFIER,
            tags_identifiers=[constants.SECOPS_CASE_TAG],
        )
        self.sync_limit: int = constants.CASES_SYNC_LIMIT
        self.fetched_product_details = {}


    def _init_api_clients(self) -> None:
        """Initializes the API clients."""
        self.manager = CrowdStrikeManager(
            api_root=self.params.api_root,
            client_id=self.params.client_id,
            client_secret=self.params.client_secret,
            use_ssl=self.params.verify_ssl,
            force_check_connectivity=True,
        )

    def modified_synced_case_ids_by_product(
        self,
        alert_ids: list[str],
        sorted_modified_ids: CaseIdModifiedTimeList,
    ) -> CaseIdModifiedTimeList:
        """Fetches modified alerts from Crowdstrike and maps them to SecOps
        case IDs.

        Args:
            alert_ids (list[str]): list of alert IDs to check for modifications.
            sorted_modified_ids (CaseIdModifiedTimeList): list of tuples containing
            case IDs and their last modified timestamps, sorted by timestamp in
            descending order.

        Returns:
            CaseIdModifiedTimeList: A list of tuples containing SecOps case IDs and
            their last modified times.
        """
        product_ids_to_case_map: dict[str, str] = self.alert_ids_to_case_map_builder()
        alert_ids = [id for id in alert_ids if id is not None]
        alerts_data = self._fetch_product_details(alert_ids)
        modified_alerts: list[AlertDetails] = []
        for alerts_response in alerts_data:
            if not alerts_response:
                continue
            if alerts_response.updated_timestamp >= self.last_run_time:
                modified_alerts.append(alerts_response)

        return self._map_alerts_to_cases(
            modified_alerts,
            product_ids_to_case_map,
            sorted_modified_ids,
        )

    def _map_alerts_to_cases(
        self,
        alerts: list[AlertDetails],
        product_ids_to_case_map: dict[str, str],
        sorted_modified_ids: CaseIdModifiedTimeList,
    ) -> CaseIdModifiedTimeList:
        """Maps modified alerts to their corresponding SecOps case IDs and determines
        the latest modified time.

        Args:
            alerts (list[AlertDetails]): List of modified alerts.
            product_ids_to_case_map (dict[str, str]): Mapping of product alert IDs to
            SecOps case IDs.
            sorted_modified_ids (CaseIdModifiedTimeList): List of tuples containing case
            IDs and their last modified timestamps, sorted by timestamp in descending
            order.

        Returns:
            CaseIdModifiedTimeList: A list of tuples containing SecOps case IDs and
            their last modified times.
        """
        results = []
        for alert in alerts:
            alert_id = alert.composite_id
            case_id = product_ids_to_case_map.get(alert_id)

            if not case_id:
                self.logger.info(
                    f"Skipping alert sync for CrowdStrike alert ID {alert_id} "
                    "as no matching SecOps case/alert ID was found in the map."
                )
                continue

            modified_time_ms = alert.updated_timestamp
            case_time_ms = next(
                (t for cid, t in sorted_modified_ids if cid == case_id), 0
            )
            results.append((case_id, max(modified_time_ms, case_time_ms)))

        return results

    def is_alert_and_product_closed(
        self,
        job_case: JobCase,
        product: AlertDetails,
    ) -> bool:
        """Checks if both the SecOps alert and the corresponding CrowdStrike alert are
        closed.

        Args:
            job_case (JobCase): The SecOps case containing the alert.
            product (AlertDetails): The CrowdStrike alert details.

        Returns:
            bool: True if both the SecOps alert and the CrowdStrike alert are closed,
            False otherwise.
        """
        alert = next(
            (
                alert
                for alert in job_case.case_detail.alerts
                if product.composite_id in utils.get_alert_id_from_alert(
                    self.soar_job,
                    alert
                )
            ),
            None,
        )

        if not alert:
            return False

        alert_closed = alert.status.lower() == "close"
        product_closed = (
            product.raw_data.get("status").lower()
            == constants.ALERT_CLOSED_STATUS.lower()
        )

        return alert_closed and product_closed

    def _extract_product_ids_from_case(self, job_case: JobCase) -> list[str]:
        """Extracts product alert IDs from the SecOps case alerts.

        Args:
            job_case (JobCase): The SecOps case containing the alerts.

        Returns:
            list[str]: A list of unique product alert IDs extracted from the case
            alerts.
        """
        alert_ids: list[str] = []

        for alert in job_case.case_detail.alerts:
            ticket_ids = utils.get_alert_id_from_alert(self.soar_job, alert)
            if ticket_ids:
                alert_ids.extend(ticket_ids)

        return sorted(set(alert_ids))

    def alert_ids_to_case_map_builder(self) -> dict[str, str]:
        """Builds a mapping of product alert IDs to SecOps case IDs.

        Returns:
            dict[str, str]: A dictionary mapping product alert IDs to their
            corresponding SecOps case IDs.
        """
        product_ids_to_case_map: dict[str, str] = {}

        for case_id, product_ids in self.processed_items.items():
            for product_id in product_ids:
                product_ids_to_case_map[product_id] = case_id

        return product_ids_to_case_map

    def map_product_data_to_case(self, job_case: JobCase) -> None:
        """Maps Crowdstrike Alert data into metadata

        Args:
            job_case (JobCase): The SecOps case to map data for.
        """
        try:
            for alert in job_case.case_detail.alerts:
                alert_ids = utils.get_alert_id_from_alert(self.soar_job, alert)
                if alert_ids:
                    self.logger.info(
                        f"Alert ID(s) '{alert_ids}' extracted for Alert "
                        f"'{alert.identifier}' are valid."
                    )
                else:
                    self.logger.error(
                        "Failed to extract a valid Alert ID for Alert "
                        f"'{alert.identifier}'."
                    )

            mapping: dict[str, AlertCard] = utils.get_alert_ids_from_soar_alerts(
                self.soar_job, job_case
            )
            product_ids_from_alerts = list(mapping.keys())
            self.logger.info(
                "Found product IDs from alerts in Case "
                f"{job_case.case_detail.id_}: {product_ids_from_alerts}"
            )

            if not product_ids_from_alerts:
                self.logger.error(
                    f"Case {job_case.case_detail.id_} wasn't synced due to missing "
                    "alert context."
                )
                return

            job_case.product_ids_from_secops_alerts = mapping
            product_details = self._fetch_product_details(product_ids_from_alerts)

            fetched_ids = [detail.composite_id for detail in product_details]
            case_id = str(job_case.case_detail.id_)
            if fetched_ids:
                self.processed_items[case_id] = fetched_ids
            else:
                if case_id in self.processed_items:
                    del self.processed_items[case_id]

            self._attach_comments_to_product_details(product_details)
            self._attach_product_details_to_case(job_case, product_details)
            self._populate_alert_metadata(job_case, product_details)
            self.remove_synced_data_from_db(job_case, product_details)
        except Exception as error:
            self.logger.error(
                "Failed to map CrowdStrike alert data to SecOps Case "
                f"{job_case.case_detail.id_}. Error: {error}"
            )
            case_id = str(job_case.case_detail.id_)
            if case_id in self.processed_items:
                del self.processed_items[case_id]


    def _is_valid_crowdstrike_comment(self, comment: str) -> bool:
        """Checks if a CrowdStrike comment should be synced to SecOps.

        Args:
            comment (str): The comment text from CrowdStrike.

        Returns:
            bool: True if the comment should be synced to SecOps, False if it
                is a SecOps-originated comment and should be skipped.
        """
        return not comment.startswith(constants.SECOPS_COMMENT_PREFIX)

    def _get_crowdstrike_alert_comments(
        self,
        product_detail: AlertDetails,
    ) -> list[str]:
        """Gets comments from CrowdStrike alert.

        Args:
            product_detail (AlertDetails): The CrowdStrike alert details.

        Returns:
            list[str]: A list of new comments to be added to SOAR.
        """
        alert_comments = product_detail.raw_data.get("comments", [])

        return [
            self._format_crowdstrike_comment(
                product_detail.composite_id,
                comment.get("value", ""),
            )
            for comment in alert_comments
            if self._is_new_crowdstrike_comment(comment)
        ]

    def _is_new_crowdstrike_comment(self, comment: dict[str, str]) -> bool:
        """Checks if the CrowdStrike comment should be synced based on prefix
        and timestamp.

        Args:
            comment (dict[str, str]): CrowdStrike comment dictionary.

        Returns:
            bool: True if comment should be synced, False otherwise.
        """
        comment_str = comment.get("value", "")
        if not self._is_valid_crowdstrike_comment(comment_str):
            return False

        timestamp = comment.get("timestamp")
        if not timestamp:
            return False

        comment_datetime = datetime.datetime.fromisoformat(
            timestamp.replace("Z", "")[: constants.COMMENT_CHARACTER_LIMIT] + "+00:00"
        )

        return comment_datetime >= convert_unixtime_to_datetime(self.last_run_time)

    def _format_crowdstrike_comment(
        self,
        composite_id: str,
        comment_text: str,
    ) -> str:
        """Formats a CrowdStrike comment for SOAR.

        Args:
            composite_id (str): The CrowdStrike alert ID.
            comment_text (str): The comment text.

        Returns:
            str: Formatted comment string for SOAR.
        """
        return f"{constants.CROWDSTRIKE_COMMENT_PREFIX}{composite_id}: {comment_text}"

    def _attach_comments_to_product_details(
        self,
        product_details: list[AlertDetails],
    ) -> None:
        """Attaches new CrowdStrike comments to each product detail object.

        Args:
            product_details (list[AlertDetails]): List of CrowdStrike alert detail
            objects to attach new comments to.
        """
        for product_detail in product_details:
            new_comments = self._get_crowdstrike_alert_comments(product_detail)

            if isinstance(new_comments, list):
                product_detail.add_comments(new_comments)

    def _fetch_product_details(self, product_ids: list[str]) -> list[AlertDetails]:
        """Fetches CrowdStrike alert details for given product IDs.

        Args:
            product_ids (list[str]): List of CrowdStrike alert composite IDs.

        Returns:
            list[AlertDetails]: The fetched CrowdStrike alert detail objects.
        """
        try:
            return self.manager.get_alerts_details(product_ids)
        except Exception as error:
            if len(product_ids) <= 1:
                raise error

            product_details = []
            for product_id in product_ids:
                try:
                    details = self.manager.get_alerts_details([product_id])
                    if details:
                        product_details.extend(details)
                except Exception as api_error:
                    self.logger.error(
                        f"Failed to fetch details for alert {product_id}. "
                        f"Error: {api_error}"
                    )
            return product_details

    def _attach_product_details_to_case(
        self,
        job_case: JobCase,
        product_details: list[SingleJson],
    ) -> None:
        """Adds product incident details to the SecOps case.

        Args:
            job_case (JobCase): The SecOps case to attach product incidents to.
            product_details (list[SingleJson]): The product incident details.
        """
        case_id = str(job_case.case_detail.id_)
        self.fetched_product_details[case_id] = product_details
        for product_detail in product_details:
            job_case.add_product_incident(product_detail, product_key="composite_id")

    def _populate_alert_metadata(
        self,
        job_case: JobCase,
        product_details: list[AlertDetails],
    ) -> None:
        """Populates sync metadata for each SecOps alert from product alert details.

        Args:
            job_case (JobCase): The SecOps case object being synced.
            product_details (list[AlertDetails]): The CrowdStrike alert details.
        """
        for alert in job_case.case_detail.alerts:
            for product_detail in product_details:
                if product_detail.composite_id in utils.get_alert_id_from_alert(
                    self.soar_job, alert
                ):
                    verdict = None
                    if (
                        product_detail.raw_data.get("status")
                        == constants.ALERT_CLOSED_STATUS.lower()
                    ):
                        tags = product_detail.raw_data.get("tags", [])

                        if constants.CROWDSTRIKE_TRUE_POSITIVE in tags:
                            verdict = constants.CROWDSTRIKE_TRUE_POSITIVE
                        elif constants.CROWDSTRIKE_FALSE_POSITIVE in tags:
                            verdict = constants.CROWDSTRIKE_FALSE_POSITIVE
                        elif constants.CROWDSTRIKE_IGNORED in tags:
                            verdict = constants.CROWDSTRIKE_IGNORED

                    job_case.alert_metadata[alert.identifier] = SyncMetadata(
                        status=product_detail.raw_data.get("status"),
                        incident_number=product_detail.composite_id,
                        closure_reason=verdict,
                    )
                    break

    def sync_status(self, job_case: JobCase) -> None:
        """Syncs closure status between SecOps case alerts and CrowdStrike alerts.

        Args:
            job_case (JobCase): The SecOps case being synced.
        """
        res = job_case.get_status_to_sync(constants.ALERT_CLOSED_STATUS.lower())
        self._sync_product_status_to_case(res, job_case)
        self._sync_case_status_to_product(res, job_case)

    def _sync_product_status_to_case(
        self,
        res: JobStatusResult,
        job_case: JobCase,
    ) -> None:
        """Syncs closures from product to SecOps case alerts.

        Args:
            res (JobStatusResult): Status result containing lists of alerts to close.
            job_case (JobCase): The SecOps case being synced.
        """
        for alert, meta in res.alerts_to_close_in_soar:
            cs_ids = self._get_crowdstrike_ids_for_alert(job_case, alert)

            open_cs_ids = []
            case_id = str(job_case.case_detail.id_)
            for cs_id in cs_ids:
                detail = next(
                    (
                        x
                        for x in self.fetched_product_details.get(case_id, [])
                        if x.composite_id == cs_id
                    ),
                    None,
                )
                if detail:
                    status = detail.raw_data.get("status")
                    if (
                        status
                        and status.lower()
                        != constants.ALERT_CLOSED_STATUS.lower()
                    ):
                        open_cs_ids.append(cs_id)

            if open_cs_ids:
                self.logger.info(
                    f"CrowdStrike alert(s) {open_cs_ids} are still open. Parent "
                    f"SecOps alert '{alert.identifier}' will remain open until "
                    f"all its mapped CrowdStrike alerts are closed."
                )
                continue

            if len(cs_ids) > 1:
                reason = "Inconclusive"
                root_cause = "Other"
                comment = (
                    "All crowdstrike alerts mapped with this SecOps alert are closed."
                )
            else:
                reason, root_cause = self._get_secops_closure_details(
                    meta.closure_reason
                )
                comment = (
                    f"{constants.CROWDSTRIKE_COMMENT_PREFIX}{meta.incident_number}: "
                    "Alert was closed"
                )

            self.sync_product_status_to_case(
                case_id=job_case.case_detail.id_,
                alert_id=alert.identifier,
                reason=reason,
                root_cause=root_cause,
                comment=comment,
            )
            self._remove_synced_entries(
                synced_list=[(job_case.case_detail.id_, f"{meta.incident_number}")],
            )

    def _sync_case_status_to_product(
        self,
        res: JobStatusResult,
        job_case: JobCase,
    ) -> None:
        """Syncs case closure status from SecOps to CrowdStrike product alerts.

        Args:
            res (JobStatusResult): sync result containing incidents to close in product.
            job_case (JobCase): The SecOps case from which closure status is pulled.
        """
        if not res.incidents_to_close_in_product:
            return

        for req in res.incidents_to_close_in_product:
            self._sync_case_status_request_to_product(job_case, req)

    def _get_crowdstrike_ids_for_alert(
        self,
        job_case: JobCase,
        alert: AlertCard
    ) -> list[str]:
        """Gets all CrowdStrike composite IDs mapped to a given SOAR alert card.

        Args:
            job_case (JobCase): The job case object.
            alert (AlertCard): The SOAR alert card.

        Returns:
            list[str]: The list of mapped CrowdStrike composite IDs.
        """
        mapping = getattr(job_case, "product_ids_from_secops_alerts", {})
        return [
            cs_id
            for cs_id, soar_alert in mapping.items()
            if soar_alert.identifier == alert.identifier
        ]

    def _sync_case_status_request_to_product(
        self,
        job_case: JobCase,
        req: SingleJson,
    ) -> None:
        """Syncs a single closure request from SecOps to CrowdStrike alert.

        Args:
            job_case (JobCase): The SecOps case being synced.
            req (SingleJson): Individual close incident request containing
            closure status.
        """
        closure_reason = self._get_closure_reason_from_request(job_case, req)
        verdict = self._get_crowdstrike_closure_details(closure_reason)

        alert_id = req["meta"].incident_number
        alert_card = job_case.product_ids_from_secops_alerts.get(alert_id)

        if alert_card:
            cs_ids = self._get_crowdstrike_ids_for_alert(job_case, alert_card)
            for cs_id in cs_ids:
                self._apply_case_closure_to_product(job_case, req, verdict, cs_id)
        else:
            self._apply_case_closure_to_product(job_case, req, verdict, alert_id)

    def _get_closure_reason_from_request(
        self,
        job_case: JobCase,
        req: SingleJson,
    ) -> str:
        """Gets the closure reason from a case closure request.

        Args:
            job_case (JobCase): The SecOps case being processed.
            req (SingleJson): The closure request data from the sync status.

        Returns:
            str: The closure reason string from case closure details or request.
        """
        if req["is_case_closed"]:
            return self.soar_job.get_case_closure_details([job_case.case_detail.id_])[
                0
            ].get("reason", "")
        return req["reason"]

    def _apply_case_closure_to_product(
        self,
        job_case: JobCase,
        req: SingleJson,
        verdict: str,
        alert_id: str,
    ) -> None:
        """Applies closure verdict/comment to the CrowdStrike alert and tracks success.

        Args:
            job_case (JobCase): The SecOps case being synced.
            req (SingleJson): The closure request data including incident metadata.
            verdict (str): The CrowdStrike verdict to set on the alert.
            alert_id (str): The Crowdstrike Alert ID to close.
        """
        comment = self.get_secops_closure_comment(job_case, req)
        comment = (
            f"{constants.SECOPS_COMMENT_PREFIX}{job_case.case_detail.id_}: {comment}"
        )
        self.manager.update_alert(
            alert_id=alert_id,
            status=constants.ALERT_CLOSED_STATUS,
            verdict=verdict,
        )
        self.manager.add_comment_to_alert(alert_id, comment)
        self.logger.info(
            "Successfully updated alert status "
            f"'{constants.ALERT_CLOSED_STATUS}' for the alert {alert_id}."
        )
        self._remove_synced_entries(
            synced_list=[(job_case.case_detail.id_, f"{alert_id}")],
        )

    def _get_secops_closure_details(self, alert_verdict: str) -> tuple[str, str]:
        """Maps a CrowdStrike verdict to SecOps case closure status and root cause.

        Args:
            alert_verdict (str): The verdict from CrowdStrike status metadata.

        Returns:
            tuple[str, str]: SecOps closure status and root cause code.
        """
        mapping: dict[str, tuple[str, str]] = {
            constants.CROWDSTRIKE_TRUE_POSITIVE: (
                "Malicious",
                CloseCaseOrAlertMaliciousRootCauses.OTHER.value,
            ),
            constants.CROWDSTRIKE_FALSE_POSITIVE: (
                "NotMalicious",
                CloseCaseOrAlertNotMaliciousRootCauses.OTHER.value,
            ),
        }
        closure_details: tuple[str, str] = mapping.get(alert_verdict)
        if closure_details:
            return closure_details

        self.logger.warn(
            f"Could not find a closure mapping for crowdstrike verdict: "
            f"'{alert_verdict}'. Defaulting to 'Inconclusive'."
        )

        return (
            "Inconclusive",
            CloseCaseOrAlertInconclusiveRootCauses.NO_CLEAR_CONCLUSION.value,
        )

    def _get_crowdstrike_closure_details(self, secops_reason: str) -> str:
        """Maps a SecOps closure reason to CrowdStrike verdict string.

        Args:
            secops_reason (str): SecOps case closure reason.

        Returns:
            str: CrowdStrike verdict corresponding to closure reason.
        """
        mapping = {
            "Malicious": "True Positive",
            "NotMalicious": "False Positive",
        }
        return mapping.get(secops_reason, "Ignored")

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

            product_comments_sync_to_case.extend(
                self._build_product_comments_for_alert(
                    job_case=job_case,
                    alert=alert,
                    product_comment_prefix=product_comment_prefix,
                    case_comment_prefix=case_comment_prefix,
                    product_incident_key=product_incident_key,
                    case_comments_hashes=case_comments_hashes,
                )
            )

        return product_comments_sync_to_case

    def _build_product_comments_for_alert(
        self,
        job_case: JobCase,
        alert: AlertCard,
        product_comment_prefix: str,
        case_comment_prefix: str,
        product_incident_key: str,
        case_comments_hashes: set,
    ) -> list[str]:
        """Builds product comments for a single alert that should be synced.

        Args:
            job_case (JobCase): The job case for which to sync comments.
            alert (AlertCard): The alert to process.
            product_comment_prefix (str): Prefix used for product comments.
            case_comment_prefix (str): Prefix used for case comments.
            product_incident_key (str): The key for the product incident field.
            case_comments_hashes (set): Set of existing case comment hashes.

        Returns:
            list[str]: A list of formatted product comments to sync.
        """
        product_comments_sync_to_case = []
        alert_identifier = alert.alert_group_identifier
        cs_ids = self._get_crowdstrike_ids_for_alert(job_case, alert)
        case_id = str(job_case.case_detail.id_)

        for cs_id in cs_ids:
            product_detail = next(
                (
                    x
                    for x in self.fetched_product_details.get(case_id, [])
                    if x.composite_id == cs_id
                ),
                None,
            )
            if not product_detail:
                continue

            product_comments_sync_to_case.extend(
                self._build_product_comments_from_detail(
                    job_case=job_case,
                    product_detail=product_detail,
                    alert_identifier=alert_identifier,
                    product_comment_prefix=product_comment_prefix,
                    case_comment_prefix=case_comment_prefix,
                    product_incident_key=product_incident_key,
                    case_comments_hashes=case_comments_hashes,
                )
            )

        return product_comments_sync_to_case

    def _build_product_comments_from_detail(
        self,
        job_case: JobCase,
        product_detail: AlertDetails,
        alert_identifier: str,
        product_comment_prefix: str,
        case_comment_prefix: str,
        product_incident_key: str,
        case_comments_hashes: set,
    ) -> list[str]:
        """Builds and formats comments for a single CrowdStrike alert detail.

        Args:
            job_case (JobCase): The job case for which to sync comments.
            product_detail (AlertDetails): The CrowdStrike alert details.
            alert_identifier (str): The identifier of the SOAR alert.
            product_comment_prefix (str): Prefix used for product comments.
            case_comment_prefix (str): Prefix used for case comments.
            product_incident_key (str): The key for the product incident field.
            case_comments_hashes (set): Set of existing case comment hashes.

        Returns:
            list[str]: List of formatted comments to sync.
        """
        comments = []
        incident_identifier = getattr(product_detail, product_incident_key)

        for product_comment in product_detail.comments:
            comment_text = self._extract_comment_text(product_comment)
            comment_with_product_prefix = self._format_product_comment(
                product_comment_prefix,
                incident_identifier,
                comment_text
            )
            comment_hash = job_case._generate_string_hash(
                comment_with_product_prefix
            )

            if (
                job_case._is_valid_product_comment(
                    comment_text,
                    case_comment_prefix,
                )
                and comment_hash not in case_comments_hashes
            ):
                comment = f"{alert_identifier}: {comment_with_product_prefix}"
                if constants.SECOPS_CASE_TAG in alert_identifier:
                    alert_identifier_prefix = comment.split(":", maxsplit=1)[0]
                    comment = comment.replace(
                        f"{alert_identifier_prefix}:", "", 1
                    )
                comments.append(comment)

        return comments

    def _is_valid_alert(self, alert: AlertCard) -> bool:
        """Checks if the SecOps alert is valid for comment syncing.

        Args:
            alert (AlertCard): The SecOps alert to check.

        Returns:
            bool: True if the alert is valid for comment syncing, False otherwise.
        """
        return hasattr(alert, "incident") and alert.incident is not None

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
        job_case,
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
        case_id = str(job_case.case_detail.id_)

        for alert in job_case.case_detail.alerts:
            if not self._is_valid_alert(alert):
                continue

            cs_ids = self._get_crowdstrike_ids_for_alert(job_case, alert)
            for cs_id in cs_ids:
                product_detail = next(
                    (
                        x
                        for x in self.fetched_product_details.get(case_id, [])
                        if x.composite_id == cs_id
                    ),
                    None,
                )
                if product_detail:
                    for comment in product_detail.comments:
                        comments_hashes.append(
                            job_case._generate_string_hash(str(comment) or "")
                        )

        return comments_hashes

    def sync_comments(self, job_case: JobCase) -> None:
        """Sync comments between SecOps and CrowdStrike.

        Args:
            job_case (JobCase): The SecOps case containing alerts to sync.
        """

        if job_case.case_detail.status == CaseDataStatus.CLOSED:
            return

        comments_to_sync = self.get_comments_to_sync(
            job_case,
            product_comment_prefix=constants.CROWDSTRIKE_COMMENT_PREFIX,
            case_comment_prefix=constants.SECOPS_COMMENT_PREFIX,
            product_incident_key="composite_id",
        )

        self.sync_product_comments_to_case(
            case_id=job_case.case_detail.id_,
            comments=comments_to_sync.product_comments_sync_to_case,
        )

        self.sync_case_comments_to_product(
            job_case=job_case,
            comments=comments_to_sync.case_comments_sync_to_product,
        )

    def sync_case_comments_to_product(
        self,
        job_case: JobCase,
        comments: list[str],
    ) -> None:
        """Syncs comments from SecOps case to CrowdStrike alerts.

        Args:
            job_case (JobCase): The SecOps case containing alerts to sync.
            comments (list[str]): The list of comments to push to product alerts.
        """
        for alert in job_case.case_detail.alerts:
            if not self._is_valid_alert(alert):
                continue

            cs_ids = self._get_crowdstrike_ids_for_alert(job_case, alert)
            case_id = str(job_case.case_detail.id_)
            for cs_id in cs_ids:
                detail = next(
                    (
                        x
                        for x in self.fetched_product_details.get(case_id, [])
                        if x.composite_id == cs_id
                    ),
                    None,
                )
                if (
                    detail
                    and detail.raw_data.get("status")
                    == constants.ALERT_CLOSED_STATUS.lower()
                ):
                    continue
                for comment in comments:
                    self._push_comment_to_id(cs_id, comment)

    def _push_comment_to_id(self, cs_id: str, text: str) -> None:
        """Pushes a comment to a specific CrowdStrike alert ID.

        Args:
            cs_id (str): The CrowdStrike composite ID.
            text (str): The comment text to push.
        """
        try:
            self.manager.add_comment_to_alert(cs_id, text)
            self.logger.info(
                "Successfully synced comments from SecOps to CrowdStrike "
                f"alert {cs_id}."
            )
        except Exception as error:
            self.logger.error(
                f"Failed to push comment to CrowdStrike alert {cs_id}. "
                f"Error: {error}"
            )

    def sync_severity(self, job_case: JobCase) -> None:
        """Crowdstrike -> SecOps Priority Sync.

        Args:
            job_case (JobCase): The SecOps case to sync severity for.
        """

    def sync_assignee(self, job_case: JobCase) -> None:
        """Crowdstrike -> SecOps Assignee Sync.

        Args:
            job_case (JobCase): The SecOps case to sync assignee for.
        """

    def sync_tags(self, job_case: JobCase) -> None:
        """Bidirectional Tag Sync.

        Args:
            job_case (JobCase): The SecOps case to sync tags for.
        """

    def remove_synced_data_from_db(
        self,
        job_case: JobCase,
        product_details: list[AlertDetails],
    ) -> None:
        """Removes entries from synchronization tracking when both alert and product
        are closed.

        Args:
            job_case (JobCase): The SecOps case currently being processed.
            product_details (list[AlertDetails]): Product alert details fetched from
            CrowdStrike.
        """
        for alert in job_case.case_detail.alerts:
            alert_ids = utils.get_alert_id_from_alert(self.soar_job, alert)

            for alert_id in alert_ids:
                matching_product = None

                for product in product_details:
                    if product.composite_id == alert_id:
                        matching_product = product
                        break

                if not matching_product:
                    continue

                if self.is_alert_and_product_closed(job_case, matching_product):
                    self._remove_synced_entries([(job_case.case_detail.id_, alert_id)])


def main() -> NoReturn:
    SyncAlerts().start()


if __name__ == "__main__":
    main()
