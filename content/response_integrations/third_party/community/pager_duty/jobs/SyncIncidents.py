from __future__ import annotations

from datetime import datetime
from email.utils import parseaddr
from types import SimpleNamespace
from typing import Any

from TIPCommon.base.job.base_sync_job import BaseSyncJob
from TIPCommon.base.job.job_case import (
    JobCase,
    JobStatusResult,
    SyncMetadata,
)
from TIPCommon.data_models import AlertCard
from TIPCommon.transformation import convert_comma_separated_to_list

from ..core.constants import (
    CONTEXT_KEY,
    ENTITY_TYPE_ALERT,
    ENTITY_TYPE_TICKET,
    PAGERDUTY_COMMENT_PREFIX,
    SIEM_COMMENT_PREFIX,
)
from ..core.PagerDutyManager import PagerDutyManager

MS_IN_SECOND: int = 1000


class SyncIncidents(BaseSyncJob[PagerDutyManager]):
    def __init__(self) -> None:
        super().__init__(
            job_name="PagerDuty Sync Incidents",
            context_identifier="Pagerduty Ticket",
            tags_identifiers=["Pagerduty Ticket"],
        )

    def _init_api_clients(self) -> PagerDutyManager:
        """Initializes the API client.

        Returns:
            The initialized API client.
        """
        verify_ssl: bool = self.params.verify_ssl
        from_email: str = self.params.from_email
        max_hours_backwards: int = int(self.params.max_hours_backwards)
        if max_hours_backwards <= 0:
            raise ValueError("'Max Hours Backwards' must be a positive integer.")

        if not from_email:
            raise ValueError("'From Email' must be provided.")

        realname, email = parseaddr(from_email)
        if not email or "@" not in email:
            raise ValueError("'From Email' must be a valid email address.")

        return PagerDutyManager(
            api_key=self.params.api_key,
            verify_ssl=verify_ssl,
            from_email=from_email,
        )

    def modified_synced_case_ids_by_product(
        self,
        alert_ids: list[str],
        sorted_modified_ids: list[tuple[str, int]],
    ) -> list[tuple[str, int]]:
        """Fetches modified incidents from PagerDuty and maps them to SecOps case IDs.

        Args:
            alert_ids: list of alert IDs to check for modifications.
            sorted_modified_ids: list of tuples containing case IDs and their
                last modified timestamps.

        Returns:
            A list of tuples containing SecOps case IDs and their last modified times.
        """
        if not alert_ids:
            return []

        product_ids_to_case_map: dict[str, str] = {}
        for case_id, product_ids in self.processed_items.items():
            for product_id in product_ids:
                product_ids_to_case_map[product_id] = case_id

        from_timestamp = getattr(self, "last_run_time", 0)
        if not from_timestamp:
            return []

        self.logger.info(
            "Checking synced PagerDuty incidents for updates and new notes."
        )
        modified_cases = []

        for incident_id, case_id in product_ids_to_case_map.items():
            is_modified, latest_timestamp = self._is_incident_modified(
                incident_id, from_timestamp
            )
            if is_modified:
                self.logger.info(
                    f"Found update or new note for incident {incident_id}, "
                    f"triggering sync for case {case_id}"
                )
                modified_cases.append((case_id, latest_timestamp))

        return modified_cases

    def _get_incident_latest_timestamp(self, incident_id: str) -> int:
        """Gets the latest timestamp of the incident itself.

        Returns:
            The timestamp in milliseconds, or 0 if failed/not found.
        """
        try:
            incident = self.api_client.get_incident(incident_id)
            updated_at_str = incident.get("updated_at")
            if updated_at_str:
                dt = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                return int(dt.timestamp() * MS_IN_SECOND)
        except Exception as e:
            self.logger.debug(
                f"Failed to get incident timestamp for {incident_id}: {e}"
            )
        return 0

    def _get_notes_latest_timestamp(self, incident_id: str) -> int:
        """Gets the latest timestamp among all incident notes.

        Returns:
            The timestamp in milliseconds, or 0 if failed/not found.
        """
        latest_timestamp = 0
        try:
            notes = self.api_client.get_incident_notes(incident_id)
            for note in notes:
                created_at_str = note.get("created_at")
                if created_at_str:
                    try:
                        dt = datetime.fromisoformat(
                            created_at_str.replace("Z", "+00:00")
                        )
                        created_at_ms = int(dt.timestamp() * MS_IN_SECOND)
                        latest_timestamp = max(latest_timestamp, created_at_ms)
                    except Exception as e:
                        self.logger.debug(
                            f"Failed to parse created_at for note in "
                            f"incident {incident_id}: {e}"
                        )
                        continue
        except Exception as e:
            self.logger.debug(f"Failed to get notes timestamp for {incident_id}: {e}")
        return latest_timestamp

    def _is_incident_modified(
        self, incident_id: str, from_timestamp: int
    ) -> tuple[bool, int]:
        """Checks if an incident or its notes have been modified since
        from_timestamp.
        """
        incident_ts = self._get_incident_latest_timestamp(incident_id)
        notes_ts = self._get_notes_latest_timestamp(incident_id)

        latest_timestamp = max(incident_ts, notes_ts)
        is_modified = latest_timestamp > from_timestamp

        if latest_timestamp == 0:
            latest_timestamp = from_timestamp

        return is_modified, latest_timestamp

    def _extract_product_ids_from_case(self, job_case: JobCase) -> list[str]:
        """Extracts product incident IDs from the SecOps case alerts and context.
        Args:
            job_case: The SecOps case containing the alerts.
        Returns:
            A list of unique product incident IDs extracted from the case.
        """
        incident_ids: list[str] = []

        context_value: str | None = self.soar_job.get_context_property(
            ENTITY_TYPE_TICKET,
            str(job_case.case_detail.id_),
            CONTEXT_KEY,
        )
        if context_value:
            ids = convert_comma_separated_to_list(context_value)
            incident_ids.extend(ids)
            first_alert = job_case.get_first_alert(open_only=False)
            if first_alert:
                for incident_id in ids:
                    job_case.product_ids_from_secops_alerts[incident_id] = first_alert

        for alert in job_case.case_detail.alerts:
            incident_id: str | None = self._extract_product_id_from_ticket(alert)
            if incident_id:
                incident_ids.append(incident_id)
                job_case.product_ids_from_secops_alerts[incident_id] = alert

        return sorted(set(incident_ids))

    def _extract_product_id_from_ticket(self, ticket: AlertCard) -> str | None:
        """Extracts PagerDuty Incident ID from a single ticket.
        Args:
            ticket: The ticket to extract ID from.
        Returns:
            The incident ID if found, None otherwise.
        """
        if ticket.ticket_id:
            return ticket.ticket_id

        return self.soar_job.get_context_property(
            ENTITY_TYPE_ALERT, ticket.alert_group_identifier, CONTEXT_KEY
        )

    def map_product_data_to_case(self, job_case: JobCase) -> None:
        """Maps PagerDuty incident data into metadata.

        Args:
            job_case: The SecOps case to map data for.
        """
        product_ids = self._extract_product_ids_from_case(job_case)
        product_details = self._fetch_product_details(product_ids)
        self._attach_comments_to_product_details(product_details)
        self._attach_product_details_to_case(job_case, product_details)
        self._populate_alert_metadata(job_case, product_details)
        self.remove_synced_data_from_db(job_case, product_details)

    def _fetch_product_details(self, product_ids: list[str]) -> list[dict[str, Any]]:
        """Fetches PagerDuty incident details for given IDs."""
        results = []
        for product_id in product_ids:
            try:
                incident = self.api_client.get_incident(product_id)
                if incident:
                    results.append(incident)
            except Exception as e:
                self.logger.error(f"Failed to fetch incident {product_id}: {e}")
        return results

    def _attach_comments_to_product_details(
        self, product_details: list[dict[str, Any]]
    ) -> None:
        """Attaches PagerDuty notes as comments to product details."""
        for detail in product_details:
            incident_id = detail.get("id")
            try:
                notes = self.api_client.get_incident_notes(incident_id)
                detail["comments"] = [
                    SimpleNamespace(message=note.get("content", "")) for note in notes
                ]
            except Exception as e:
                self.logger.error(
                    f"Failed to fetch notes for incident {incident_id}: {e}"
                )

    def _attach_product_details_to_case(
        self, job_case: JobCase, product_details: list[dict[str, Any]]
    ) -> None:
        """Adds product incident details to the SecOps case."""
        for product_detail in product_details:
            job_case.add_product_incident(
                SimpleNamespace(**product_detail), product_key="id"
            )

    def _populate_alert_metadata(
        self, job_case: JobCase, product_details: list[dict[str, Any]]
    ) -> None:
        """Populates sync metadata for each SecOps alert."""
        product_map = {pd.get("id"): pd for pd in product_details}
        case_id = str(job_case.case_detail.id_)
        mapped_ids = self.processed_items.get(case_id, [])
        for alert in job_case.case_detail.alerts:
            product_id = self._extract_product_id_from_ticket(alert)
            matching_product = None
            if product_id:
                matching_product = product_map.get(product_id)
            else:
                for pid in mapped_ids:
                    if pid in product_map:
                        matching_product = product_map[pid]
                        break

            if matching_product:
                comments = matching_product.get("comments", [])
                closure_reason = None
                if comments:
                    closure_reason = getattr(comments[-1], "message", "")
                
                job_case.alert_metadata[alert.identifier] = SyncMetadata(
                    status=matching_product.get("status"),
                    incident_number=matching_product.get("id"),
                    closure_reason=closure_reason,
                )

    def sync_status(self, job_case: JobCase) -> None:
        """Syncs closure status between SecOps case alerts and PagerDuty incidents."""
        res = job_case.get_status_to_sync(product_closed_status="resolved")
        self.sync_product_status_to_case(res, job_case)
        self._sync_case_status_to_product(res, job_case)

    def sync_product_status_to_case(
        self, res: JobStatusResult, job_case: JobCase
    ) -> None:
        """Syncs closures from PagerDuty to SecOps case alerts."""
        for alert, meta in res.alerts_to_close_in_soar:
            reason = "Maintenance"
            root_cause = "Other"
            open_alerts = [
                a
                for a in job_case.case_detail.alerts
                if a.status.lower() not in ["close", "closed"]
            ]
            comment = meta.closure_reason or "Ticket was closed"
            if len(open_alerts) <= 1:
                try:
                    self.soar_job.close_case(
                        root_cause=root_cause,
                        comment=comment,
                        reason=reason,
                        case_id=job_case.case_detail.id_,
                        alert_identifier=alert.identifier,
                    )
                    self.logger.info(
                        f"Successfully closed case {job_case.case_detail.id_} "
                        f"because alert {alert.identifier} was the last open alert "
                        f"and PagerDuty incident {meta.incident_number} was resolved."
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to close case {job_case.case_detail.id_}: {e}"
                    )
            else:
                try:
                    self.soar_job.close_alert(
                        root_cause=root_cause,
                        comment=comment,
                        reason=reason,
                        case_id=job_case.case_detail.id_,
                        alert_id=alert.identifier,
                    )
                    self.logger.info(
                        f"Successfully closed alert {alert.identifier} in case "
                        f"{job_case.case_detail.id_} because PagerDuty incident "
                        f"{meta.incident_number} was resolved."
                    )
                except Exception as e:
                    self.logger.error(f"Failed to close alert {alert.identifier}: {e}")

            self._remove_synced_entries(
                synced_list=[(job_case.case_detail.id_, f"{meta.incident_number}")],
            )

    def _sync_case_status_to_product(
        self, res: JobStatusResult, job_case: JobCase
    ) -> None:
        """Syncs case closure status from SecOps to PagerDuty."""
        if not res.incidents_to_close_in_product:
            return

        for req in res.incidents_to_close_in_product:
            meta = req.get("meta")
            if not meta or not meta.incident_number:
                continue

            try:
                closing_comment = self.get_secops_closure_comment(job_case, req)

                if closing_comment:
                    self.api_client.add_incident_note(
                        meta.incident_number, closing_comment
                    )
                self.api_client.resolve_incident(meta.incident_number)
                self.logger.info(
                    f"Successfully resolved PagerDuty incident {meta.incident_number}."
                )
                self._remove_synced_entries(
                    synced_list=[
                        (job_case.case_detail.id_, f"{meta.incident_number}")
                    ],
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to resolve PagerDuty incident "
                    f"{meta.incident_number}: {e}"
                )

    def sync_comments(self, job_case: JobCase) -> None:
        """Syncs comments between SecOps and PagerDuty."""
        if job_case.case_detail.status == "Closed":
            return

        comments_to_sync = self.get_comments_to_sync(
            job_case,
            product_comment_prefix=PAGERDUTY_COMMENT_PREFIX,
            case_comment_prefix=SIEM_COMMENT_PREFIX,
            product_comment_key="message",
            product_incident_key="id",
        )

        self.sync_product_comments_to_case(
            case_id=job_case.case_detail.id_,
            comments=comments_to_sync.product_comments_sync_to_case,
        )
        if comments_to_sync.product_comments_sync_to_case:
            count = len(comments_to_sync.product_comments_sync_to_case)
            self.logger.info(
                f"Successfully synced {count} "
                f"comments from PagerDuty to SecOps case {job_case.case_detail.id_}."
            )

        self.sync_case_comments_to_product(
            job_case=job_case,
            comments=comments_to_sync.case_comments_sync_to_product,
        )

    def sync_case_comments_to_product(
        self, job_case: JobCase, comments: list[str]
    ) -> None:
        """Syncs comments from SecOps case to PagerDuty incidents."""
        incident_ids = self._extract_product_ids_from_case(job_case)
        for incident_id in incident_ids:
            for comment in comments:
                try:
                    self.api_client.add_incident_note(
                        incident_id, f"{SIEM_COMMENT_PREFIX} {comment}"
                    )
                    self.logger.info(
                        f"Successfully added comment to PagerDuty incident "
                        f"{incident_id}."
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to add note to PagerDuty incident {incident_id}: {e}"
                    )

    def is_alert_and_product_closed(
        self,
        job_case: JobCase,
        product: dict[str, Any],
    ) -> bool:
        """Checks if both the SecOps alert and the corresponding PagerDuty
        incident are closed.
        """
        product_id = product.get("id")

        alert = next(
            (
                alert
                for alert in job_case.case_detail.alerts
                if self._extract_product_id_from_ticket(alert) == product_id
            ),
            None,
        )

        if not alert:
            return False

        alert_status = getattr(alert, "status", "")
        alert_closed = False
        if isinstance(alert_status, str):
            alert_closed = alert_status.lower() in ["close", "closed"]
        else:
            alert_closed = str(alert_status).lower() in ["close", "closed"]

        product_closed = product.get("status") == "resolved"

        return alert_closed and product_closed

    def remove_synced_data_from_db(
        self, job_case: JobCase, product_details: list[dict[str, Any]]
    ) -> None:
        """Removes entries from synchronization tracking when both alert and
        product are closed.
        """
        for alert in job_case.case_detail.alerts:
            alert_id = self._extract_product_id_from_ticket(alert)
            if not alert_id:
                continue

            matching_product = None
            for product in product_details:
                if product.get("id") == alert_id:
                    matching_product = product
                    break

            if not matching_product:
                continue

            if self.is_alert_and_product_closed(job_case, matching_product):
                self._remove_synced_entries([(job_case.case_detail.id_, alert_id)])

    def sync_assignee(self, job_case: JobCase) -> None:
        pass

    def sync_severity(self, job_case: JobCase) -> None:
        pass

    def sync_tags(self, job_case: JobCase) -> None:
        pass


def main() -> None:
    SyncIncidents().start()


if __name__ == "__main__":
    main()
