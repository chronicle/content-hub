"""BiDi Sync job SOAR <-> ServiceNow"""
from __future__ import annotations

from __future__ import annotations

import dataclasses
from collections import defaultdict
from datetime import datetime
from typing import Iterable, Mapping, Sequence

from soar_sdk.SiemplifyJob import SiemplifyJob
from TIPCommon import extraction
from TIPCommon import validation
from TIPCommon.consts import SOAR_COMMENT_PREFIX
from TIPCommon.smp_time import change_timezone

from scc_enterprise.core.BaseSoarItsmJob import SyncSoarITSM
from scc_enterprise.core.SCCEnterpriseConsts import SYNC_SCC_SNOW_TICKETS_SCRIPT_NAME
from scc_enterprise.core.SCCEnterpriseConsts import CLOSED_BY_SCCE_COMMENT
from scc_enterprise.core.SCCEnterpriseDatamodels import FindingContext, ITSMTicketDetailsForSCC
from scc_enterprise.core.SCCEnterpriseUtils import create_html_table, update_html_desc_table
from scc_enterprise.core.ServiceNowConsts import DATETIME_FORMAT, UTC_TZ
from scc_enterprise.core.ServiceNowConsts import INTEGRATION_NAME
from scc_enterprise.core.ServiceNowDatamodels import Incident
from scc_enterprise.core.ServiceNowExceptions import SNowRecordNotFoundException
from scc_enterprise.core.ServiceNowManager import ServiceNowManager
from scc_enterprise.core.ServiceNowUtils import convert_sn_time_to_unix_utc_timestamp


TICKETS_LIMIT_IN_REQUEST = 100
COMMENT_LIMIT_TO_FETCH = 100


@dataclasses.dataclass
class ServiceNowAuthParams:
    api_root: str
    username: str
    password: str
    verify_ssl: bool

    @classmethod
    def build_from_job(cls, chronicle_soar: SiemplifyJob) -> ServiceNowAuthParams:
        """Build integration auth params from SOAR job object."""
        return cls(
            api_root=extraction.extract_job_param(
                chronicle_soar, param_name="API Root", is_mandatory=True
            ),
            username=extraction.extract_job_param(
                chronicle_soar, param_name="Username", is_mandatory=True
            ),
            password=extraction.extract_job_param(
                chronicle_soar, param_name="Password", is_mandatory=True
            ),
            verify_ssl=extraction.extract_job_param(
                chronicle_soar,
                param_name="Verify SSL",
                is_mandatory=True,
                input_type=bool,
            ),
        )


class SyncSCCServiceNowTicketsJob(SyncSoarITSM[Incident, ServiceNowManager]):
    """Implementation of SyncSoarITSM using ServiceNow"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._timezone_mapping = {}

    def get_timezone_by_user(self, user_name: str) -> str:
        if user_name not in self._timezone_mapping:
            self._timezone_mapping[user_name] = (
                self.api_client.get_system_timezone_by_user_name(user_name)
            )

        return self._timezone_mapping[user_name]

    def _validate_params(self) -> None:
        validator = validation.ParameterValidator(self.soar_job)
        self.params.max_hours_backwards = validator.validate_non_negative(
            param_name="Max Hours Backwards", value=self.params.max_hours_backwards
        )

    def _init_api_clients(self) -> ServiceNowManager:
        """Initialize the ServiceNow manager."""
        service_now_auth_params = ServiceNowAuthParams.build_from_job(self.soar_job)
        return ServiceNowManager(
            api_root=service_now_auth_params.api_root,
            username=service_now_auth_params.username,
            password=service_now_auth_params.password,
            verify_ssl=service_now_auth_params.verify_ssl,
            siemplify_logger=self.soar_job.LOGGER,
        )

    def _get_environment_for_case_filter(self) -> str:
        return self.params.environment

    def _get_max_hours_backwards(self) -> int:
        return self.params.max_hours_backwards

    def _get_bulk_ticket_id_to_details_map(
        self,
        ticket_ids: Sequence[str] | None = None,
        last_run_timestamp: int | None = None,
    ) -> Mapping[str, Incident]:
        ticket_ids = ticket_ids or []
        read_mask = [
            "sys_id",
            "sys_created_by",
            "sys_updated_on",
            "u_overview",
            "u_status",
            "u_priority",
            "u_severity",
            "u_assigned_to",
            "u_source_link",
        ]

        if last_run_timestamp:
            tickets = self.api_client.get_incidents_with_pagination(
                updated_after=last_run_timestamp,
                fields=read_mask,
                page_size=TICKETS_LIMIT_IN_REQUEST,
            )

        else:
            tickets = self.api_client.get_incidents_by_sys_ids(
                numbers=ticket_ids, fields=read_mask, page_size=TICKETS_LIMIT_IN_REQUEST
            )

        return {str(ticket.sys_id): ticket for ticket in tickets}

    def _get_ticket_id_to_details_map(self, ticket_id: str) -> Mapping[str, Incident]:
        return self._get_bulk_ticket_id_to_details_map([ticket_id])

    def _get_bulk_ticket_id_to_comments_map(
        self, tickets: Iterable[Incident]
    ) -> Mapping[str, list[str]]:
        # API does not support filtering with (for creation time) with > or >=
        ticket_ids = [ticket.sys_id for ticket in tickets]
        ticket_id_to_ticket_comments = defaultdict(list)

        for index in range(0, len(ticket_ids), TICKETS_LIMIT_IN_REQUEST):
            try:
                itsm_comments = self.api_client.get_ticket_comments(
                    ticket_sys_ids=ticket_ids[index : index + TICKETS_LIMIT_IN_REQUEST],
                    page_size=COMMENT_LIMIT_TO_FETCH,
                    fields=["value", "sys_created_on", "element_id"],
                    order_by="sys_created_on",
                )
                for comment in itsm_comments:
                    ticket_sys_id = comment.element_id
                    (
                        ticket_id_to_ticket_comments[str(ticket_sys_id)].append(
                            comment.value
                        )
                    )

            except SNowRecordNotFoundException:
                self.logger.warn(
                    "Received status code 404 - no comments found, assuming tickets "
                    "have no comments."
                )

        return ticket_id_to_ticket_comments

    def _get_ticket_id_to_comments_map(
        self, ticket: Incident
    ) -> Mapping[str, list[str]]:
        return self._get_bulk_ticket_id_to_comments_map([ticket])

    def _add_comment_to_ticket(self, comment: str, ticket_id: str) -> None:
        self.api_client.add_comment_to_incident(ticket_id, comment, is_ticket_id=True)

    def _close_ticket(self, ticket_id: str) -> None:
        self.api_client.close_incident(
            ticket_number=ticket_id,
            close_reason=CLOSED_BY_SCCE_COMMENT,
            is_ticket_id=True,
        )

    def _get_ticket_case_uri(self, ticket: Incident) -> str:
        return ticket.case_uri

    def _get_ticket_status(self, ticket: Incident) -> str:
        return ticket.status

    def _set_ticket_status(self, ticket: Incident, new_status: str) -> None:
        ticket.status = new_status

    def _set_ticket_update_time(self, ticket: Incident, update_time: datetime) -> None:
        sn_tz = self.get_timezone_by_user(ticket.sys_created_by)
        ticket.raw_data["sys_updated_on"] = change_timezone(
            update_time, UTC_TZ, sn_tz
        ).strftime(DATETIME_FORMAT)

    def _update_ticket_description(self, ticket_id: str, description: str) -> None:
        self.api_client.update_incident(
            ticket_number=ticket_id,
            custom_fields={"u_overview": description},
            is_ticket_id=True,
        )

    def _update_ticket_severity(self, ticket_id: str, severity: str) -> None:
        self.api_client.update_incident(
            ticket_number=ticket_id,
            custom_fields={
                "u_severity": severity,
                "u_additional_comments": f"{SOAR_COMMENT_PREFIX}Synced severity",
            },
            is_ticket_id=True,
        )

    def _create_description_table(self, findings: list[FindingContext]) -> str:
        return create_html_table(findings, self._soar_job.platform_url)

    def _update_description_table(self, table: str, description: str) -> str:
        return update_html_desc_table(table, description)

    def _parse_ticket_details_for_scc(
        self, ticket: Incident, **additional_keys
    ) -> ITSMTicketDetailsForSCC:
        update_time_str = ticket.raw_data["sys_updated_on"]
        sn_tz = self.get_timezone_by_user(ticket.sys_created_by)
        update_time_ts = convert_sn_time_to_unix_utc_timestamp(
            sn_tz=sn_tz,
            ticket_time_field=update_time_str,
            ticket_time_format=self.params.time_format,
        )

        ticket_details = ITSMTicketDetailsForSCC(
            id_=ticket.sys_id,
            assignee=ticket.assignee,
            description=ticket.overview,
            uri=None,
            status=ticket.status,
            update_time=update_time_ts,
            **additional_keys,
        )

        # Updating the attr if exists or creating it if not
        ticket_details.additional_keys["priority"] = ticket.priority

        return ticket_details


def main() -> None:
    sync_job = SyncSCCServiceNowTicketsJob(
        script_name=SYNC_SCC_SNOW_TICKETS_SCRIPT_NAME, integration_name=INTEGRATION_NAME
    )
    sync_job.start()


if __name__ == "__main__":
    main()
