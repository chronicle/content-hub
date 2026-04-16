from __future__ import annotations

import re
import uuid
from typing import Any

from TIPCommon.base.job.base_sync_job import BaseSyncJob
from TIPCommon.base.job.job_case import JobCase, JobStatusResult, SyncMetadata
from TIPCommon.data_models import AlertCard
from TIPCommon.types import SingleJson, SyncItem

from ..core.constants import (
    CLASSIFICATION_FALSE_POSITIVE,
    CLASSIFICATION_OTHER,
    CLASSIFICATION_TRUE_POSITIVE,
    REASON_MALICIOUS,
    REASON_NOT_MALICIOUS,
    REASON_RESOLVED_IN_PAGERDUTY,
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


ENTITY_TYPE_ALERT = 2


class SyncIncidents(BaseSyncJob[PagerDutyManager]):
    def __init__(self) -> None:
        """Initializes the SyncIncidents job."""
        super().__init__(
            job_name="PagerDuty Sync Incidents",
            context_identifier="pagerduty_sync",
            tags_identifiers=["Pagerduty Alert"],
        )

    def _init_api_clients(self) -> PagerDutyManager:
        """Initializes the PagerDuty API client.

        Returns:
            The initialized API client.
        """
        verify_ssl: bool = getattr(self.params, "verify_ssl", True)
        from_email: str | None = getattr(self.params, "from_email", None)
        return PagerDutyManager(
            api_key=self.params.api_key,
            verify_ssl=verify_ssl,
            from_email=from_email,
        )

    def _extract_product_id_from_alert(self, alert: AlertCard) -> str | None:
        """Extracts PagerDuty Incident ID from a single alert.

        Args:
            alert: The alert to extract the ID from.

        Returns:
            The extracted PagerDuty Incident ID, or None.
        """
        if alert.ticket_id is not None and not is_uuid(alert.ticket_id):
            return alert.ticket_id

        if hasattr(alert, "alert_group_identifier") and alert.alert_group_identifier:
            val: str | None = self.soar_job.get_context_property(
                ENTITY_TYPE_ALERT,
                alert.alert_group_identifier,
                "Alert_ID",
            )
            if val:
                return val

        if hasattr(alert, "identifier") and alert.identifier:
            parts: list[str] = alert.identifier.split("_")
            if len(parts) > 1:
                potential_id: str = parts[-1]
                if re.match(r"^[A-Z0-9]{14}$", potential_id):
                    self.logger.info(
                        f"Extracted incident ID {potential_id} from alert identifier "
                        f"{alert.identifier}"
                    )
                    return potential_id

        return None

    def _extract_product_ids_from_case(self, job_case: JobCase) -> SyncItem:
        """Extracts PagerDuty Incident IDs from the case alerts.

        Args:
            job_case: The case containing alerts.

        Returns:
            A list of extracted incident IDs.
        """
        incident_ids: list[str] = []
        for alert in job_case.case_detail.alerts:
            incident_id: str | None = self._extract_product_id_from_alert(alert)
            if incident_id:
                incident_ids.append(incident_id)

        return incident_ids

    def map_product_data_to_case(self, job_case: JobCase) -> None:
        """Maps product data to the case.

        Args:
            job_case: The case to map data to.
        """
        for alert in job_case.case_detail.alerts:
            incident_id: str | None = self._extract_product_id_from_alert(alert)
            if incident_id:
                try:
                    incident: SingleJson = self.api_client.get_incident(incident_id)

                    job_case.alert_metadata[alert.identifier] = SyncMetadata(
                        status=incident.get("status"),
                        incident_number=incident_id,
                        closure_reason=None,
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to fetch PagerDuty incident {incident_id}: {e}"
                    )

    def sync_status(self, job_case: JobCase) -> None:
        """Syncs status between PagerDuty and SecOps.

        Args:
            job_case: The case to sync status for.
        """
        res: JobStatusResult = job_case.get_status_to_sync("resolved")

        synced_to_remove: list[tuple[str, str]] = []

        for req in res.incidents_to_close_in_product:
            incident_id: str = req["meta"].incident_number
            alert: AlertCard = req["alert"]

            reason: str = CLASSIFICATION_OTHER
            if hasattr(alert, "closure_details") and alert.closure_details:
                reason = alert.closure_details.get("reason", CLASSIFICATION_OTHER)

            classification: str = CLASSIFICATION_OTHER
            if reason == REASON_MALICIOUS:
                classification = CLASSIFICATION_TRUE_POSITIVE
            elif reason == REASON_NOT_MALICIOUS:
                classification = CLASSIFICATION_FALSE_POSITIVE

            try:
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

                if alert.status.lower() == "close":
                    synced_to_remove.append(
                        (str(job_case.case_detail.id_), incident_id)
                    )

            except Exception as e:
                self.logger.error(
                    f"Failed to resolve PagerDuty incident {incident_id}: {e}"
                )

        closed_alert_ids: set[str] = set()
        for alert, meta in res.alerts_to_close_in_soar:
            reason_soar = REASON_RESOLVED_IN_PAGERDUTY

            try:
                open_alerts = [
                    a
                    for a in job_case.case_detail.alerts
                    if a.status.lower() == "open"
                    and a.identifier not in closed_alert_ids
                ]
                if (
                    len(open_alerts) == 1
                    and open_alerts[0].identifier == alert.identifier
                ):
                    self.soar_job.close_case(
                        root_cause=CLASSIFICATION_OTHER,
                        case_id=job_case.case_detail.id_,
                        reason=reason_soar,
                        comment=(
                            f"Closed case because last alert {alert.identifier} was "
                            "resolved in PagerDuty."
                        ),
                        alert_identifier=None,
                    )
                    self.logger.info(
                        f"Closed case {job_case.case_detail.id_} as it was the last "
                        "open alert."
                    )
                else:
                    self.sync_product_status_to_case(
                        case_id=job_case.case_detail.id_,
                        alert_id=alert.identifier,
                        reason=reason_soar,
                        root_cause="Other",
                        comment=f"PagerDuty incident {meta.incident_number} was resolved.",
                    )
                    closed_alert_ids.add(alert.identifier)

                if meta.status == "resolved":
                    synced_to_remove.append(
                        (str(job_case.case_detail.id_), meta.incident_number)
                    )
            except Exception as e:
                self.logger.error(
                    f"Failed to close alert {alert.identifier} or case in SecOps: {e}"
                )

        self._remove_synced_entries(synced_to_remove)
        self.logger.info(f"Case {job_case.case_detail.id_} successfully synced.")

    def sync_comments(self, job_case: JobCase) -> None:
        """Syncs comments.

        Args:
            job_case (JobCase): The case to sync comments for.
        """
        pass

    def sync_tags(self, job_case: JobCase) -> None:
        """Syncs tags.

        Args:
            job_case (JobCase): The case to sync tags for.
        """
        pass

    def sync_severity(self, job_case: JobCase) -> None:
        """Syncs severity.

        Args:
            job_case (JobCase): The case to sync severity for.
        """
        pass

    def sync_assignee(self, job_case: JobCase) -> None:
        """Syncs assignee.

        Args:
            job_case (JobCase): The case to sync assignee for.
        """
        pass

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

    def remove_synced_data_from_db(
        self, job_case: JobCase, product_details: Any
    ) -> None:
        """Removes synced data from DB.

        Args:
            job_case (JobCase): The case.
            product_details (Any): The product details.
        """

        pass


def main() -> None:
    SyncIncidents().start()


if __name__ == "__main__":
    main()
