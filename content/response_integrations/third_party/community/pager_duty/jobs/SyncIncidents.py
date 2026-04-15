from __future__ import annotations

import uuid
from typing import Any

from TIPCommon.base.job.base_sync_job import BaseSyncJob
from TIPCommon.base.job.job_case import JobCase, JobStatusResult, SyncMetadata
from TIPCommon.data_models import AlertCard
from TIPCommon.types import SingleJson, SyncItem

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
            PagerDutyManager: The initialized API client.
        """
        api_key: str = self.params.api_key
        return PagerDutyManager(api_key=api_key)

    def _extract_product_id_from_alert(self, alert: AlertCard) -> str | None:
        """Extracts PagerDuty Incident ID from a single alert.

        Args:
            alert (AlertCard): The alert to extract the ID from.

        Returns:
            str | None: The extracted PagerDuty Incident ID, or None.
        """
        if alert.ticket_id is not None and not is_uuid(alert.ticket_id):
            return alert.ticket_id

        if hasattr(alert, "alert_group_identifier") and alert.alert_group_identifier:
            val: str | None = self.soar_job.get_context_property(
                2,  # ENTITY_TYPE
                alert.alert_group_identifier,
                "Alert_ID",  # CONTEXT_ALERT_ID_FIELD
            )
            if val:
                return val
                
        # Fallback: Extract from alert identifier if it ends with _<ID>
        if hasattr(alert, "identifier") and alert.identifier:
            parts: list[str] = alert.identifier.split("_")
            if len(parts) > 1:
                potential_id: str = parts[-1]
                if not is_uuid(potential_id) and potential_id.isalnum():
                    self.logger.info(
                        f"Extracted incident ID {potential_id} from alert identifier "
                        f"{alert.identifier}"
                    )
                    return potential_id

        return None

    def _extract_product_ids_from_case(self, job_case: JobCase) -> SyncItem:
        """Extracts PagerDuty Incident IDs from the case alerts.

        Args:
            job_case (JobCase): The case containing alerts.

        Returns:
            SyncItem: A list of extracted incident IDs.
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
            job_case (JobCase): The case to map data to.
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
            job_case (JobCase): The case to sync status for.
        """
        res: JobStatusResult = job_case.get_status_to_sync("resolved")
        
        synced_to_remove: list[tuple[str, str]] = []
        
        # 1. Synchronise PagerDuty with Google SecOps Alerts statuses (SOAR to PagerDuty)
        for req in res.incidents_to_close_in_product:
            incident_id: str = req["meta"].incident_number
            alert: AlertCard = req["alert"]
            
            reason: str = "Other"
            if hasattr(alert, "closure_details") and alert.closure_details:
                reason = alert.closure_details.get("reason", "Other")
                
            classification: str = "Other"
            if reason == "Malicious":
                classification = "True Positive"
            elif reason == "Not Malicious":
                classification = "False Positive"
                
            try:
                self.api_client.add_incident_note(incident_id, f"Classification: {classification}")
                self.api_client.resolve_incident(incident_id)
                self.logger.info(f"Resolved PagerDuty incident {incident_id} with classification {classification}")
                
                if alert.status.lower() == "close":
                    synced_to_remove.append((str(job_case.case_detail.id_), incident_id))
                    
            except Exception as e:
                self.logger.error(
                    f"Failed to resolve PagerDuty incident {incident_id}: {e}"
                )
                
        # 2. Synchronise Google SecOps Alerts with Pagerduty Incidents (PagerDuty to SOAR)
        for alert, meta in res.alerts_to_close_in_soar:
            reason_soar = "Resolved in PagerDuty"
            
            try:
                open_alerts = [a for a in job_case.case_detail.alerts if a.status.lower() == "open"]
                if len(open_alerts) == 1 and open_alerts[0].identifier == alert.identifier:
                    # It's the last open alert! Close the case.
                    self.soar_job.close_case(
                        root_cause="Other",
                        case_id=job_case.case_detail.id_,
                        reason=reason_soar,
                        comment=f"Closed case because last alert {alert.identifier} was resolved in PagerDuty.",
                        alert_identifier=None,
                    )
                    self.logger.info(f"Closed case {job_case.case_detail.id_} as it was the last open alert.")
                else:
                    self.sync_product_status_to_case(
                        case_id=job_case.case_detail.id_,
                        alert_id=alert.identifier,
                        reason=reason_soar,
                        root_cause="Other",
                        comment=f"PagerDuty incident {meta.incident_number} was resolved.",
                    )
                
                if meta.status == "resolved":
                    synced_to_remove.append((str(job_case.case_detail.id_), meta.incident_number))
            except Exception as e:
                self.logger.error(
                    f"Failed to close alert {alert.identifier} or case in SecOps: {e}"
                )

        # Remove synced entries if closed on either side
        self._remove_synced_entries(synced_to_remove)

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
        # Assume product is SyncMetadata or similar
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
        # Handled in sync_status directly or via _remove_synced_entries
        pass


def main() -> None:
    SyncIncidents().start()


if __name__ == "__main__":
    main()

