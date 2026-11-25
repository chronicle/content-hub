"""Sync Alerts — populate SecOps case description from Vega incidentSummary."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from TIPCommon.base.job.base_sync_job import BaseSyncJob
from TIPCommon.base.job.job_case import JobCase
from TIPCommon.rest.custom_types import HttpMethod
from TIPCommon.rest.soar_api import change_case_description, validate_response
from TIPCommon.rest.soar_platform_clients.api_client_factory import get_soar_client
from TIPCommon.rest.soar_platform_clients.one_platform_soar_api import OnePlatformSoarApi

from ..core import constants
from ..core.case_insight import incident_ids_from_soar_alert
from ..core.VegaManager import VegaClientConfig, VegaManager

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class SyncAlerts(BaseSyncJob[VegaManager]):
    """Write Vega incidentSummary onto tagged SecOps cases as case description."""

    def __init__(self) -> None:
        super().__init__(
            job_name=constants.SYNC_ALERTS_SCRIPT_NAME,
            context_identifier=constants.SYNC_ALERTS_IDENTIFIER,
            tags_identifiers=[constants.SYNC_ALERTS_TAG],
        )
        self.sync_limit = constants.CASES_SYNC_LIMIT
        # tipcommon default (30) blocks large Vega cases after small tagged cases burn the budget
        self.product_alerts_limit = 0
        self.manager: VegaManager | None = None

    def _init_api_clients(self) -> None:
        self.manager = VegaManager(
            VegaClientConfig(
                api_root=self.params.api_root,
                access_key_id=self.params.access_key_id,
                access_key=self.params.access_key,
                verify_ssl=bool(self.params.verify_ssl),
            ),
            logger_instance=self.logger,
        )

    def _extract_product_ids_from_case(self, job_case: JobCase) -> list[str]:
        """Incident UUID from alert ticket_id / grouping: ``Vega:incident:<uuid>``."""
        ids: set[str] = set()
        for alert in job_case.case_detail.alerts or []:
            ids.update(incident_ids_from_soar_alert(alert))
        return sorted(ids)

    def modified_synced_case_ids_by_product(
        self,
        incident_ids: list[str],
        sorted_modified_ids: list[tuple[str, int]],
    ) -> list[tuple[str, int]]:
        if not self.manager or not incident_ids:
            return []
        id_map: dict[str, str] = {}
        for case_id, product_ids in self.processed_items.items():
            for product_id in product_ids or []:
                id_map[str(product_id)] = str(case_id)
        case_time = dict(sorted_modified_ids)
        results: list[tuple[str, int]] = []
        for incident_id in incident_ids:
            case_id = id_map.get(str(incident_id))
            if not case_id:
                continue
            try:
                incident = self.manager.get_incident(str(incident_id))
            except Exception as exc:
                self.logger.warn(f"Unable to fetch Vega incident {incident_id}: {exc}")
                continue
            if incident:
                results.append((case_id, max(case_time.get(case_id, 0), self.last_run_time or 0)))
        return results

    def map_product_data_to_case(self, job_case: JobCase) -> None:
        if not self.manager:
            return
        incident_ids = self._extract_product_ids_from_case(job_case)
        if not incident_ids:
            return
        incident: SingleJson = {}
        for incident_id in incident_ids:
            try:
                incident = self.manager.get_incident(incident_id) or {}
            except Exception as exc:
                self.logger.warn(f"Unable to fetch Vega incident {incident_id}: {exc}")
                continue
            if incident:
                break
        if not incident:
            return
        self._sync_case_description(job_case, incident)

    def _update_case_description(self, case_id: int, description: str) -> None:
        client = get_soar_client(self.soar_job)
        if isinstance(client, OnePlatformSoarApi):
            response = client._make_request(
                HttpMethod.PATCH,
                f"/cases/{case_id}",
                params={"updateMask": "description"},
                json_payload={"description": description},
            )
            validate_response(response, validate_json=False)
            return
        change_case_description(self.soar_job, case_id, description)

    def _sync_case_description(self, job_case: JobCase, incident: SingleJson) -> None:
        description = str(incident.get("incidentSummary") or "").strip()
        if not description:
            return
        current = str(getattr(job_case.case_detail, "description", None) or "").strip()
        if description == current:
            return
        case_id = int(job_case.case_detail.id_)
        try:
            self._update_case_description(case_id, description)
            self.logger.info(f"Updated description on case {case_id}.")
        except Exception as exc:
            self.logger.warn(f"Unable to set description on case {case_id}: {exc}")

    def is_alert_and_product_closed(self, job_case: JobCase, product: Any) -> bool:
        return False


def main() -> None:
    SyncAlerts().start()


if __name__ == "__main__":
    main()
