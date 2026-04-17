from __future__ import annotations

import re
import uuid
from typing import Any

from TIPCommon.base.job.base_sync_job import BaseSyncJob
from TIPCommon.base.job.job_case import JobCase, JobStatusResult, SyncMetadata
from TIPCommon.data_models import AlertCard
from TIPCommon.transformation import convert_comma_separated_to_list
from TIPCommon.types import SingleJson, SyncItem

from ..core.constants import (
    CLASSIFICATION_FALSE_POSITIVE,
    CLASSIFICATION_OTHER,
    CLASSIFICATION_TRUE_POSITIVE,
    CONTEXT_KEY,
    PAGERDUTY_COMMENT_PREFIX,
    REASON_MALICIOUS,
    REASON_NOT_MALICIOUS,
    REASON_RESOLVED_IN_PAGERDUTY,
    SIEM_COMMENT_PREFIX,
)
from ..core.PagerDutyManager import PagerDutyManager


def is_uuid(value: str) -> bool:
    """Checks if a string value is a valid UUID."""
    if not isinstance(value, str):
        return False
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


ENTITY_TYPE_TICKET = 2


class SyncIncidents(BaseSyncJob[PagerDutyManager]):
    def __init__(self) -> None:
        """Initializes the SyncIncidents job."""
        super().__init__(
            job_name="PagerDuty Sync Incidents",
            context_identifier="pagerduty_sync",
            tags_identifiers=["Pagerduty Ticket"],
        )

    def _init_api_clients(self) -> PagerDutyManager:
        """Initializes the PagerDuty API client.

        Returns:
            The initialized API client.
        """
        verify_ssl: bool = getattr(self.params, "Verify SSL", True)
        from_email: str | None = getattr(self.params, "from_email", None)
        return PagerDutyManager(
            api_key=self.params.api_key,
            verify_ssl=verify_ssl,
            from_email=from_email,
        )

    def _extract_product_id_from_ticket(self, ticket: AlertCard) -> str | None:
        """Extracts PagerDuty Incident ID from a single ticket.

        Args:
            ticket: The ticket to extract the ID from.

        Returns:
            The extracted PagerDuty Incident ID, or None.
        """
        if ticket.ticket_id is not None and not is_uuid(ticket.ticket_id):
            return ticket.ticket_id

        if hasattr(ticket, "alert_group_identifier") and ticket.alert_group_identifier:
            val: str | None = self.soar_job.get_context_property(
                ENTITY_TYPE_TICKET,
                ticket.alert_group_identifier,
                CONTEXT_KEY,
            )
            if val:
                return val

        if hasattr(ticket, "identifier") and ticket.identifier:
            parts: list[str] = ticket.identifier.split("_")
            if len(parts) > 1:
                potential_id: str = parts[-1]
                if re.match(r"^[A-Z0-9]{14}$", potential_id):
                    self.logger.info(
                        f"Extracted incident ID {potential_id} from ticket identifier "
                        f"{ticket.identifier}"
                    )
                    return potential_id

        return None

    def _extract_product_ids_from_case(self, job_case: JobCase) -> SyncItem:
        """Extracts PagerDuty Incident IDs from the case context and tickets.

        Args:
            job_case: The case containing tickets.

        Returns:
            A list of extracted incident IDs.
        """
        incident_ids: list[str] = []

        val: str | None = self.soar_job.get_context_property(
            1,
            str(job_case.case_detail.id_),
            "TICKET_ID",
        )
        if val:
            incident_ids.extend(convert_comma_separated_to_list(val))

        for ticket in job_case.case_detail.alerts:
            incident_id: str | None = self._extract_product_id_from_ticket(ticket)
            if incident_id:
                incident_ids.append(incident_id)

        return list(set(incident_ids))

    def map_product_data_to_case(self, job_case: JobCase) -> None:
        """Maps product data to the case.

        Args:
            job_case: The case to map data to.
        """
        for ticket in job_case.case_detail.alerts:
            incident_id: str | None = self._extract_product_id_from_ticket(ticket)
            if incident_id:
                try:
                    incident: SingleJson = self.api_client.get_incident(incident_id)

                    job_case.alert_metadata[ticket.identifier] = SyncMetadata(
                        status=incident.get("status"),
                        incident_number=incident_id,
                        closure_reason=None,
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to fetch PagerDuty incident {incident_id}: {e}"
                    )

    def _get_classification(self, ticket: AlertCard) -> str:
        """Determines classification based on ticket closure details."""
        reason: str = CLASSIFICATION_OTHER
        if hasattr(ticket, "closure_details") and ticket.closure_details:
            reason = ticket.closure_details.get("reason", CLASSIFICATION_OTHER)

        if reason == REASON_MALICIOUS:
            return CLASSIFICATION_TRUE_POSITIVE
        elif reason == REASON_NOT_MALICIOUS:
            return CLASSIFICATION_FALSE_POSITIVE
        return CLASSIFICATION_OTHER

    def _resolve_pagerduty_incident(
        self, incident_id: str, classification: str
    ) -> None:
        """Adds a note and resolves the incident in PagerDuty."""
        note_content = (
            f"Classification: {classification}\n"
            f"Incident closed from Google SecOps"
        )
        self.api_client.add_incident_note(incident_id, note_content)
        self.api_client.resolve_incident(incident_id)
        self.logger.info(
            f"Resolved PagerDuty incident {incident_id} "
            f"with classification {classification}"
        )

    def _close_incidents_in_pagerduty(
        self, job_case: JobCase, res: JobStatusResult
    ) -> list[tuple[str, str]]:
        """Closes incidents in PagerDuty based on job status result."""
        synced_to_remove: list[tuple[str, str]] = []
        for req in res.incidents_to_close_in_product:
            incident_id: str = req["meta"].incident_number
            ticket: AlertCard = req["alert"]

            classification = self._get_classification(ticket)

            try:
                self._resolve_pagerduty_incident(incident_id, classification)

                if ticket.status.lower() == "close":
                    synced_to_remove.append(
                        (str(job_case.case_detail.id_), incident_id)
                    )

            except Exception as e:
                self.logger.error(
                    f"Failed to resolve PagerDuty incident {incident_id}: {e}"
                )
        return synced_to_remove

    def _get_open_tickets(
        self, job_case: JobCase, closed_ticket_ids: set[str]
    ) -> list[AlertCard]:
        """Returns a list of open tickets in the case that are not yet closed."""
        return [
            t
            for t in job_case.case_detail.alerts
            if t.status.lower() == "open"
            and t.identifier not in closed_ticket_ids
        ]

    def _close_case_or_ticket(
        self,
        job_case: JobCase,
        ticket: AlertCard,
        meta: Any,
        open_tickets: list[AlertCard],
    ) -> bool:
        """Closes either the full case or just the specific ticket in SecOps."""
        reason_soar = REASON_RESOLVED_IN_PAGERDUTY
        if len(open_tickets) == 1 and open_tickets[0].identifier == ticket.identifier:
            self.soar_job.close_case(
                root_cause=CLASSIFICATION_OTHER,
                case_id=job_case.case_detail.id_,
                reason=reason_soar,
                comment=(
                    f"Closed case because last ticket {ticket.identifier} was "
                    "resolved in PagerDuty."
                ),
                alert_identifier=None,
            )
            self.logger.info(
                f"Closed case {job_case.case_detail.id_} as it was the last "
                "open ticket."
            )
            return False
        else:
            self.sync_product_status_to_case(
                case_id=job_case.case_detail.id_,
                alert_id=ticket.identifier,
                reason=reason_soar,
                root_cause="Other",
                comment=(
                    f"PagerDuty incident {meta.incident_number} was resolved."
                ),
            )
            return True

    def _close_tickets_in_soar(
        self, job_case: JobCase, res: JobStatusResult
    ) -> list[tuple[str, str]]:
        """Closes tickets or cases in SecOps based on job status result."""
        synced_to_remove: list[tuple[str, str]] = []
        closed_ticket_ids: set[str] = set()
        for ticket, meta in res.alerts_to_close_in_soar:
            try:
                open_tickets = self._get_open_tickets(job_case, closed_ticket_ids)

                if self._close_case_or_ticket(job_case, ticket, meta, open_tickets):
                    closed_ticket_ids.add(ticket.identifier)

                if meta.status == "resolved":
                    synced_to_remove.append(
                        (str(job_case.case_detail.id_), meta.incident_number)
                    )
            except Exception as e:
                self.logger.error(
                    f"Failed to close ticket {ticket.identifier} or case in SecOps: {e}"
                )
        return synced_to_remove

    def sync_status(self, job_case: JobCase) -> None:
        """Syncs status between PagerDuty and SecOps.

        Args:
            job_case: The case to sync status for.
        """
        res: JobStatusResult = job_case.get_status_to_sync("resolved")

        synced_to_remove: list[tuple[str, str]] = []

        synced_to_remove.extend(self._close_incidents_in_pagerduty(job_case, res))
        synced_to_remove.extend(self._close_tickets_in_soar(job_case, res))

        self._remove_synced_entries(synced_to_remove)
        self._sync_untracked_incidents_status(job_case)

        self.logger.info(f"Case {job_case.case_detail.id_} successfully synced.")

    def _sync_untracked_incidents_status(self, job_case: JobCase) -> None:
        """Fallback sync for cases not tracked by standard metadata."""
        incident_ids = self._extract_product_ids_from_case(job_case)
        is_case_closed = job_case.case_detail.status == "Closed"

        for incident_id in incident_ids:
            try:
                incident = self.api_client.get_incident(incident_id)
                product_status = incident.get("status")

                if product_status == "resolved" and not is_case_closed:
                    self.soar_job.close_alert(
                        root_cause=CLASSIFICATION_OTHER,
                        case_id=job_case.case_detail.id_,
                        reason=REASON_RESOLVED_IN_PAGERDUTY,
                        comment=(
                            f"Closed case because PagerDuty incident "
                            f"{incident_id} was resolved."
                        ),
                        alert_identifier=None,
                    )
                    self.logger.info(
                        f"Closed case {job_case.case_detail.id_} due to "
                        f"resolved PagerDuty incident {incident_id}"
                    )
                elif product_status != "resolved" and is_case_closed:
                    self._resolve_pagerduty_incident(incident_id, CLASSIFICATION_OTHER)

            except Exception as e:
                self.logger.error(
                    f"Failed to sync status for PagerDuty incident "
                    f"{incident_id}: {e}"
                )

    def is_alert_and_product_closed(self, job_case: JobCase, product: Any) -> bool:
        """Checks if alert and product are closed.

        Args:
            job_case (JobCase): The case.
            product (Any): The product data.

        Returns:
            bool: True if closed, False otherwise.
        """

        if isinstance(product, SyncMetadata):
            return product.status == "resolved"
        return False

    def sync_comments(self, job_case: JobCase) -> None:
        """Syncs comments between PagerDuty and SecOps."""
        incident_ids = self._extract_product_ids_from_case(job_case)
        if not incident_ids:
            return

        for incident_id in incident_ids:
            try:
                notes = self.api_client.get_incident_notes(incident_id)
            except Exception as e:
                self.logger.error(
                    f"Failed to get PagerDuty notes for {incident_id}: {e}"
                )
                continue

            try:
                case_comments = self.soar_job.fetch_case_comments(
                    job_case.case_detail.id_
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to fetch SOAR comments for case "
                    f"{job_case.case_detail.id_}: {e}"
                )
                case_comments = []

            for note in notes:
                content = note.get("content", "")
                if content.startswith(SIEM_COMMENT_PREFIX):
                    continue

                already_exists = False
                for c in case_comments:
                    if c.get("comment", "").endswith(content):
                        already_exists = True
                        break

                if not already_exists:
                    self.soar_job.add_comment(
                        comment=f"{PAGERDUTY_COMMENT_PREFIX} {content}",
                        case_id=job_case.case_detail.id_,
                        alert_identifier=None,
                    )

            for comment in case_comments:
                content = comment.get("comment", "")
                if content.startswith(PAGERDUTY_COMMENT_PREFIX):
                    continue

                already_exists = False
                for note in notes:
                    if note.get("content", "").endswith(content):
                        already_exists = True
                        break

                if not already_exists:
                    try:
                        self.api_client.add_incident_note(
                            incident_id,
                            f"{SIEM_COMMENT_PREFIX} {content}"
                        )
                    except Exception as e:
                        self.logger.error(
                            f"Failed to add note to PagerDuty incident "
                            f"{incident_id}: {e}"
                        )

    def remove_synced_data_from_db(self, job_case: JobCase, product_details: Any) -> None:
        """Removes synced data from db."""
        pass

    def sync_assignee(self, job_case: JobCase) -> None:
        """Syncs assignee."""
        pass

    def sync_severity(self, job_case: JobCase) -> None:
        """Syncs severity."""
        pass

    def sync_tags(self, job_case: JobCase) -> None:
        """Syncs tags."""
        pass


def main() -> None:
    SyncIncidents().start()


if __name__ == "__main__":
    main()
