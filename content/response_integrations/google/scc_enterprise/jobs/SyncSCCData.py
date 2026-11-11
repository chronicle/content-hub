from __future__ import annotations

import dataclasses
from collections import defaultdict
from decimal import Decimal
import json
from requests import HTTPError
import urllib.parse
from scc_enterprise.core import SCCEnterpriseDatamodels
from soar_sdk.Siemplify import CASE_FILTER_MAX_RESULTS
from soar_sdk.SiemplifyDataModel import (
    CaseFilterOperatorEnum,
    CaseFilterSortByEnum,
    CaseFilterSortOrderEnum,
    CaseFilterStatusEnum,
)

from soar_sdk.SiemplifyJob import SiemplifyJob
from TIPCommon import extraction
from TIPCommon.base.job import Job
from TIPCommon.consts import UNIX_FORMAT
from TIPCommon.data_models import (
    CaseDataStatus,
    CASE_DATA_STATUS_VAL_NAME_MAP,
    CaseDetails,
)
from TIPCommon.exceptions import (
    BadGatewayError,
    DeadlineExceededError,
    ResourceExhaustedError,
    UnavailableError,
)
from TIPCommon.rest.soar_api import (
    get_case_overview_details,
    remove_case_tag,
    set_alert_priority,
    set_case_score_bulk,
)
from TIPCommon.smp_time import is_approaching_timeout, unix_now
from TIPCommon.utils import is_empty_string_or_none
from TIPCommon.validation import ParameterValidator

from scc_enterprise.core.BaseSoarItsmJob import CLOSE_CASE_REASON, CLOSE_CASE_ROOT_CAUSE
from scc_enterprise.core import GoogleSecurityCommandCenterConstants as GSCCConstants
from scc_enterprise.core import GoogleSecurityCommandCenterDatamodels as GSCCDatamodels
from scc_enterprise.core.GoogleSecurityCommandCenterExceptions import GoogleSecurityCommandCenterException
from scc_enterprise.core.GoogleSecurityCommandCenterManager import GoogleSecurityCommandCenterManager
from scc_enterprise.core.SCCEnterpriseConsts import (
    CLOSED_BY_SCCE_COMMENT,
    EXTERNAL_SCC_TICKET_INFO,
    FINDINGS_CONTEXT_KEY,
    INTERNAL_SCC_TICKET_INFO,
    SYNC_DATA_JOB_NAME,
    SCCE_COMMENT_PREFIX,
)
from scc_enterprise.core.SCCEnterpriseDatamodels import ExternalSCCTicketInfo, FindingContext
from scc_enterprise.core.SCCEnterpriseUtils import (
    build_case_details_for_scc,
    create_scc_finding_state_json,
    load_findings_context,
    soar_supports_scce_phase_2,
)


DEFAULT_HOURS_BACKWARDS = 0
UPDATE_CASE_MODIFICATION_TIME = (
    f"{SCCE_COMMENT_PREFIX} - Updated Case Modification Time"
)


@dataclasses.dataclass
class SecurityCommandCenterAuthParams:
    api_root: str
    user_service_account: str | None
    workload_identity_email: str | None
    pubsub_project_id: str | None
    quota_project_id: str | None
    organization_id: str
    location_id: str
    verify_ssl: bool

    @classmethod
    def build_from_job(
        cls, chronicle_soar: SiemplifyJob
    ) -> SecurityCommandCenterAuthParams:
        """Build integration auth params from SOAR job object."""
        return cls(
            api_root=extraction.extract_job_param(
                chronicle_soar, param_name="API Root", is_mandatory=True
            ),
            user_service_account=extraction.extract_job_param(
                chronicle_soar, param_name="User Service Account"
            ),
            workload_identity_email=extraction.extract_job_param(
                chronicle_soar, param_name="Workload Identity Email"
            ),
            pubsub_project_id=extraction.extract_job_param(
                chronicle_soar, param_name="PubSub Project ID"
            ),
            quota_project_id=extraction.extract_job_param(
                chronicle_soar, param_name="Quota Project ID"
            ),
            organization_id=extraction.extract_job_param(
                chronicle_soar, param_name="Organization ID", is_mandatory=True
            ),
            location_id=extraction.extract_job_param(
                chronicle_soar, param_name="Location ID"
            ),
            verify_ssl=extraction.extract_job_param(
                chronicle_soar,
                param_name="Verify SSL",
                is_mandatory=True,
                input_type=bool,
            ),
        )


class SyncSCCData(Job):
    def __init__(self, script_name: str) -> None:
        self._instance_url: str | None = None
        super().__init__(script_name)
        if not soar_supports_scce_phase_2(self.soar_job):
            raise GoogleSecurityCommandCenterException(
                f"This JOB is not supported by SOAR SDK in current version: "
                f"{self.soar_job.get_system_version()}. Please Upgrade your "
                "SOAR platform to latest version to execute this job."
            )

        self._fetched_cases_cache: dict[int, CaseDetails] = {}

    @property
    def instance_url(self) -> str:
        if self._instance_url is None:
            self._instance_url = self.soar_job.platform_url
        return self._instance_url

    def get_cases_overview_details(self, case_id: int) -> CaseDetails:
        if case_id not in self._fetched_cases_cache:
            self._fetched_cases_cache[case_id] = get_case_overview_details(
                chronicle_soar=self.soar_job, case_id=case_id
            )
        return self._fetched_cases_cache[case_id]

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_job)
        if not is_empty_string_or_none(self.params.user_service_account):
            validator.validate_json(
                param_name="User Service Account",
                json_string=self.params.user_service_account,
                print_value=False,
            )
        if not is_empty_string_or_none(self.params.workload_identity_email):
            validator.validate_email(
                "Workload Identity Email", self.params.workload_identity_email
            )

        self.params.max_hours_backwards = validator.validate_integer(
            param_name="Max Hours Backwards", value=str(self.params.max_hours_backwards)
        )
        self.params.max_hours_backwards = validator.validate_positive(
            param_name="Max Hours Backwards",
            value=str(self.params.max_hours_backwards),
            default_value=DEFAULT_HOURS_BACKWARDS,
        )

    def _init_api_clients(self) -> GoogleSecurityCommandCenterManager:
        scc_auth_params = SecurityCommandCenterAuthParams.build_from_job(self.soar_job)
        manager = GoogleSecurityCommandCenterManager(
            api_root=scc_auth_params.api_root,
            service_account_string=scc_auth_params.user_service_account,
            workload_identity_email=scc_auth_params.workload_identity_email,
            pubsub_project_id=scc_auth_params.pubsub_project_id,
            quota_project_id=scc_auth_params.quota_project_id,
            organization_id=scc_auth_params.organization_id,
            location_id=scc_auth_params.location_id,
            verify_ssl=scc_auth_params.verify_ssl,
            chronicle_soar=self.soar_job,
        )
        if is_empty_string_or_none(scc_auth_params.user_service_account):
            try:
                manager.test_connectivity()
            except GoogleSecurityCommandCenterException as e:
                raise GoogleSecurityCommandCenterException(
                    'Error executing "Sync SCC Data" Job. '
                    "Reason: Authentication with Workload Identity to Google"
                    "Security Command Center server resulted in failure. "
                    f"Error: {e}."
                ) from e

        identifier = urllib.parse.quote_plus(self.soar_job.unique_identifier)
        notifications_config_name = (
            GSCCConstants.JOB_NOTIFICATIONS_CONFIG_FORMAT.format(identifier=identifier)
        )
        topic_name = GSCCConstants.JOB_TOPIC_NAME_FORMAT.format(identifier=identifier)
        subscription_name = GSCCConstants.JOB_SUB_NAME_FORMAT.format(
            identifier=identifier
        )

        # Using the script timout threshold as the ack_deadline for each
        # message pulled by the pubsub subscription
        self.subscription = manager.get_pubsub_subscription(
            notifications_config_name=notifications_config_name,
            pubsub_topic_name=topic_name,
            subscription_name=subscription_name,
            query_filter=(
                GSCCConstants.JOB_QUERY_FILTER.format(platform_uri=self.instance_url)
            ),
            ack_deadline=GSCCConstants.JOB_ACK_DEADLINE,
        )

        return manager

    def sync_soar_to_scc_for_external(self, last_run_timestamp: int):
        """Sync updated SOAR cases with external tag (has ITSM) data to SCC.

        Args:
            last_run_timestamp: Last run timestamp of the job
        """
        # Check all updated cases that have tag EXTERNAL-SCC-TICKET-INFO
        updated_cases: list[int] = self.soar_job.get_cases_ids_by_filter(
            status=CaseFilterStatusEnum.BOTH,
            update_time_from_unix_time_in_ms=last_run_timestamp,
            start_time_from_unix_time_in_ms=last_run_timestamp,
            operator=CaseFilterOperatorEnum.OR,
            sort_by=CaseFilterSortByEnum.UPDATE_TIME,
            sort_order=CaseFilterSortOrderEnum.ASC,
            max_results=CASE_FILTER_MAX_RESULTS,
            tags=[EXTERNAL_SCC_TICKET_INFO],
            environments=[self.params.environment_name],
        )
        self.logger.info(
            f"Fetched {len(updated_cases)} updated cases with ITSM data from SOAR."
        )

        # Extract all finding ids from the case. Finding ID = Ticket ID of Alert
        case_findings_mapping: dict[int, list] = {
            case_id: self.soar_job.get_alerts_ticket_ids_by_case_id(case_id)
            for case_id in updated_cases
        }
        self.logger.info(
            f"Found {sum(map(len, case_findings_mapping.values()))} "
            "findings related to updated cases in total"
        )

        # Update External Systems Info on those findings
        for case_id in updated_cases:
            try:
                self.logger.info(f"Fetching case {case_id} details")
                case_context = self._get_case_context_property(
                    case_id=str(case_id), property_key=EXTERNAL_SCC_TICKET_INFO
                )
                ext_context = ExternalSCCTicketInfo.from_json(json.loads(case_context))
                ext_sys_json = ext_context.to_context_json()

            except Exception as e:
                self.logger.error(
                    f"Could not sync findings to case {case_id} with External "
                    "System info because it is missing crucial data. "
                    "Please Run ITSM Job to populate the needed data fields."
                )
                self.logger.exception(e)
                continue

            findings = case_findings_mapping[case_id]
            updated = True
            for finding_name in findings:
                updated &= self.update_external_systems_object(
                    case_id=case_id,
                    finding_name=finding_name,
                    external_systems_obj=ext_sys_json,
                )

            if (
                ext_context.case.status
                == CASE_DATA_STATUS_VAL_NAME_MAP[CaseDataStatus.CLOSED]
                and updated
            ):
                remove_case_tag(
                    chronicle_soar=self.soar_job,
                    case_id=case_id,
                    tag=EXTERNAL_SCC_TICKET_INFO,
                )

    def sync_soar_to_scc_for_internal(self, last_run_timestamp: int):
        """Sync updated SOAR cases with internal tag (no ITSM) data to SCC.

        Args:
            last_run_timestamp: Last run timestamp of the job
        """
        # Check all updated cases that have tag INTERNAL-SCC-TICKET-INFO
        updated_cases: list[int] = self.soar_job.get_cases_ids_by_filter(
            status=CaseFilterStatusEnum.BOTH,
            update_time_from_unix_time_in_ms=last_run_timestamp,
            start_time_from_unix_time_in_ms=last_run_timestamp,
            operator=CaseFilterOperatorEnum.OR,
            sort_by=CaseFilterSortByEnum.UPDATE_TIME,
            sort_order=CaseFilterSortOrderEnum.ASC,
            max_results=CASE_FILTER_MAX_RESULTS,
            tags=[INTERNAL_SCC_TICKET_INFO],
            environments=[self.params.environment_name],
        )
        self.logger.info(
            f"Fetched {len(updated_cases)} updated cases without ITSM data from SOAR."
        )

        # Extract all finding ids from the case. Finding ID = Ticket ID of Alert
        case_findings_mapping: dict[int, list] = {
            case_id: self.soar_job.get_alerts_ticket_ids_by_case_id(case_id)
            for case_id in updated_cases
        }
        self.logger.info(
            f"Found {sum(map(len, case_findings_mapping.values()))} "
            "findings related to updated cases in total"
        )

        # Update External Systems Info on those findings
        for case_id in updated_cases:
            case_details = self.get_cases_overview_details(case_id)
            scc_case_details = build_case_details_for_scc(
                soar_job=self.soar_job, case=case_details
            )

            updated = True
            for finding_name in case_findings_mapping[case_id]:
                updated &= self.update_external_systems_object(
                    case_id=case_id,
                    finding_name=finding_name,
                    external_systems_obj=scc_case_details.to_scc_json(),
                )

            if (
                scc_case_details.status
                == CASE_DATA_STATUS_VAL_NAME_MAP[CaseDataStatus.CLOSED]
                and updated
            ):
                remove_case_tag(
                    chronicle_soar=self.soar_job,
                    case_id=case_id,
                    tag=INTERNAL_SCC_TICKET_INFO,
                )

    def update_external_systems_object(
        self, case_id: int, finding_name: str, external_systems_obj: dict
    ) -> bool:
        """Update externalsSystemsObject for SCC finding."""

        try:
            ext_sys_name = f"{finding_name}/externalSystems/chronicle_soar"
            self.logger.info(
                f"Syncing Case {case_id} to Finding Resource {ext_sys_name}"
            )
            self.api_client.update_finding_external_systems(
                external_system_name=ext_sys_name, **external_systems_obj
            )
            self.logger.info(f"successfully Synced case {case_id} details to SCC")
            return True

        except DeadlineExceededError:
            self.logger.error(
                f"Received an deadline exceeded when syncing External System data of "
                f"finding: {finding_name}, the finding will be synced in next iteration."
            )
            soar_case = self.get_cases_overview_details(case_id)
            self._update_case_modification_time(soar_case)

        except (BadGatewayError, ResourceExhaustedError, UnavailableError):
            raise

        except Exception as e:
            self.logger.error(
                f"Could not sync External System data of finding: {finding_name}. "
                f"Error: {e}"
            )
            self.logger.exception(e)

        return False

    def _update_case_modification_time(self, case: CaseDetails):
        """Update case modification time with NOOP change.

        Setting the same priority

        Args:
            case: soar case details for scc object
        """
        if case.status == CASE_DATA_STATUS_VAL_NAME_MAP[CaseDataStatus.OPENED]:
            self.soar_job.change_case_priority(
                priority=case.priority, case_id=case.id_, alert_identifier=None
            )

        else:
            self.soar_job.add_comment(
                comment=UPDATE_CASE_MODIFICATION_TIME,
                case_id=case.id_,
                alert_identifier=None,
            )

    def _check_status_transition(
        self,
        case_id: int,
        current_finding_context: SCCEnterpriseDatamodels.FindingContext | None,
        updated_finding_context: SCCEnterpriseDatamodels.FindingContext,
    ) -> None:
        """Check for status transition and add comment if it happened.

        Args:
            case_id (int): Chronicle SOAR case ID
            current_finding_context: Current Finding Context from Case context
            updated_finding_context: New Finding Context build from notification
        """
        if current_finding_context.status is None:
            return

        reopened_finding_comment = GSCCConstants.REOPENED_FINDING_COMMENT.format(
            id=updated_finding_context.finding_id,
            resource_name=updated_finding_context.resource_name,
        )
        closed_finding_comment = GSCCConstants.CLOSED_FINDING_COMMENT.format(
            id=updated_finding_context.finding_id,
            resource_name=updated_finding_context.resource_name,
        )

        if updated_finding_context.is_active and not current_finding_context.is_active:
            # finding was set to Inactive, then again to active
            # add reopened comment to case
            self.logger.info(
                f"Finding {updated_finding_context.finding_id} was reopened - "
                f"updating case {case_id}"
            )
            self.soar_job.add_comment(
                comment=reopened_finding_comment, case_id=case_id, alert_identifier=None
            )
        elif (
            not updated_finding_context.is_active and current_finding_context.is_active
        ):
            # finding was set to Inactive
            # add closed comment to case
            self.logger.info(
                f"Finding {updated_finding_context.finding_id} was set to Inactive - "
                f"updating case {case_id}"
            )
            self.soar_job.add_comment(
                comment=closed_finding_comment, case_id=case_id, alert_identifier=None
            )

    def _check_mute_transition(
        self,
        case_id: int,
        current_finding_context: SCCEnterpriseDatamodels.FindingContext | None,
        updated_finding_context: SCCEnterpriseDatamodels.FindingContext,
    ) -> None:
        """Check for mute transition and add comment if it happened.

        Args:
            case_id (int): Chronicle SOAR case ID
            current_finding_context: Current Finding Context from Case context
            updated_finding_context: New Finding Context build from notification
        """
        if current_finding_context.mute is None:
            return

        unmuted_finding_comment = GSCCConstants.UNMUTED_FINDING_COMMENT.format(
            id=updated_finding_context.finding_id,
            resource_name=updated_finding_context.resource_name,
        )
        muted_finding_comment = GSCCConstants.MUTED_FINDING_COMMENT.format(
            id=updated_finding_context.finding_id,
            resource_name=updated_finding_context.resource_name,
        )

        if updated_finding_context.is_muted and not current_finding_context.is_muted:
            # finding was not muted, now is muted add 'muted' comment to case
            self.logger.info(
                f"Finding {updated_finding_context.finding_id} was muted - "
                f"updating case {case_id}"
            )
            self.soar_job.add_comment(
                comment=muted_finding_comment, case_id=case_id, alert_identifier=None
            )
        elif not updated_finding_context.is_muted and current_finding_context.is_muted:
            # finding was muted, now is not muted add 'unmuted' comment to case
            self.logger.info(
                f"Finding {updated_finding_context.finding_id} was unmuted - "
                f"updating case {case_id}"
            )
            self.soar_job.add_comment(
                comment=unmuted_finding_comment, case_id=case_id, alert_identifier=None
            )

    def _check_tc_count_transition(
        self,
        case_id: int,
        current_finding_context: SCCEnterpriseDatamodels.FindingContext | None,
        updated_finding_context: SCCEnterpriseDatamodels.FindingContext,
    ) -> None:
        """Check for tc_count transition and add comment if it happened.

        Args:
            case_id (int): Chronicle SOAR case ID
            current_finding_context: Current Finding Context from Case context
            updated_finding_context: New Finding Context build from notification
        """
        if current_finding_context.tc_count is None:
            return

        increased_finding_comment = GSCCConstants.TC_COUNT_INCREASED_COMMENT.format(
            id=updated_finding_context.finding_id,
            number=updated_finding_context.tc_count,
        )
        decreased_finding_comment = GSCCConstants.TC_COUNT_DECREASED_COMMENT.format(
            id=updated_finding_context.finding_id,
            number=updated_finding_context.tc_count,
        )

        if current_finding_context.tc_count < updated_finding_context.tc_count:
            # finding's tc_count has increased add 'increased' comment to case
            self.logger.info(
                f"Finding {updated_finding_context.finding_id} tc_count has increased "
                f"- updating case {case_id}"
            )
            self.soar_job.add_comment(
                comment=increased_finding_comment,
                case_id=case_id,
                alert_identifier=None,
            )
        elif current_finding_context.tc_count > updated_finding_context.tc_count:
            # finding's tc_count has decreased add 'decreased' comment to case
            self.logger.info(
                f"Finding {updated_finding_context.finding_id} tc_count has decreased "
                f"- updating case {case_id}"
            )
            self.soar_job.add_comment(
                comment=decreased_finding_comment,
                case_id=case_id,
                alert_identifier=None,
            )

    def _check_severity_transition(
        self,
        case_id: int,
        finding_category: str,
        current_finding_context: FindingContext,
        updated_finding_context: FindingContext,
    ) -> None:
        """Check if finding's severity has changed, update alert if it did.

        Args:
            case_id (int): Case ID
            finding_category (str): Finding's category
            current_finding_context (FindingContext): Previous finding's context
            updated_finding_context (FindingContext): New finding's context
        """
        if updated_finding_context.severity == current_finding_context.severity:
            return

        self.logger.info(
            f"Finding's {updated_finding_context.finding_id} severity has changed "
            f"from {current_finding_context.severity} "
            f"to {updated_finding_context.severity}. Updating corresponding alert."
        )

        if updated_finding_context.alert_identifier is None:
            soar_case = self.get_cases_overview_details(case_id)
            alert = next(
                filter(
                    lambda al: (
                        updated_finding_context.name_without_location.upper()
                        in al.identifier
                    ),
                    soar_case.alerts,
                )
            )
            updated_finding_context.alert_identifier = alert.identifier

        try:
            set_alert_priority(
                self.soar_job,
                case_id=case_id,
                alert_identifier=updated_finding_context.alert_identifier,
                alert_name=finding_category,
                priority=GSCCConstants.ALERT_SEVERITY_MAPPING[
                    updated_finding_context.severity
                ],
            )
        except HTTPError as e:
            self.logger.error(
                "Failed changing priority of the alert "
                f"{updated_finding_context.alert_identifier} in the case {case_id}. "
                f"Error is: {e}"
            )

    def _check_aps_score_transition(
        self,
        case_id: int,
        current_finding_context: FindingContext,
        updated_finding_context: FindingContext,
    ) -> None:
        """Check if finding's Attack Exposure Score has changed, update case if it did.

        Note: Currently we do that check only for Toxic Combination cases, so
        it is assumed that such case will have one and only one finding at all times.

        Args:
            case_id (int): Case ID
            current_finding_context (FindingContext): Previous finding's context
            updated_finding_context (FindingContext): New finding's context
        """
        if updated_finding_context.aps_score is None:
            return

        if current_finding_context.aps_score is not None and Decimal(
            current_finding_context.aps_score
        ) == Decimal(updated_finding_context.aps_score):
            return

        self.logger.info(
            f"Finding's {updated_finding_context.finding_id} Attack Exposure Score has "
            f"changed from {current_finding_context.aps_score} "
            f"to {updated_finding_context.aps_score}. Updating corresponding TC case."
        )

        try:
            response_json = set_case_score_bulk(
                self.soar_job,
                case_score_mapping=[
                    {"caseId": str(case_id), "score": updated_finding_context.aps_score}
                ],
            )

            error_msg = ""
            if response_json.get("invalidScoreCaseIds"):
                invalid_ids = ",".join(
                    str(id_) for id_ in response_json["invalidScoreCaseIds"]
                )
                error_msg += f"Invalid scores provided for cases: {invalid_ids}. "
            if response_json.get("notFoundCaseIds"):
                not_found_ids = ",".join(
                    str(id_) for id_ in response_json["notfoundCaseIds"]
                )
                error_msg += f"Not found cases: {not_found_ids}."

            if error_msg:
                raise HTTPError(error_msg)

        except HTTPError as e:
            self.logger.error(
                f"Failed updating aps_score for case {case_id}. " f"Error is: {e}"
            )

    def _check_case_closure(
        self, case_id: int, findings_context: set[FindingContext]
    ) -> None:
        """Close case if it hasn't any active and not muted findings.

        Args:
            case_id (int): Case ID
            findings_context (set[FindingContext]): Fresh Findings Context for this case
        """

        if any(not fc.is_muted and fc.is_active for fc in findings_context):
            return

        # All SCC findings within the case, were set to Inactive or Muteda
        finding_names = self.soar_job.get_alerts_ticket_ids_by_case_id(case_id)
        if len(finding_names) > len(findings_context):
            self.logger.info(
                f"Case {case_id} has some findings that are not synced yet. "
                "Aborting closure..."
            )
            return

        self.logger.info(
            f"All of case's {case_id} related findings are Inactive or muted."
            "Closing Case..."
        )

        alert_identifier = next(
            (
                fc.alert_identifier
                for fc in findings_context
                if fc.alert_identifier is not None
            ),
            self.get_cases_overview_details(case_id).alerts[0].identifier,
        )
        try:
            self.soar_job.close_case(
                case_id=case_id,
                reason=CLOSE_CASE_REASON,
                comment=CLOSED_BY_SCCE_COMMENT,
                root_cause=CLOSE_CASE_ROOT_CAUSE,
                alert_identifier=alert_identifier,
            )
            self.soar_job.add_comment(
                comment=GSCCConstants.ALL_FINDING_CLOSED_COMMENT,
                case_id=case_id,
                alert_identifier=None,
            )
        except Exception as e:
            self.logger.info(
                f"Encountered an error while closing case {case_id}. " f"Reason: {e}"
            )

    def _perform_job(self) -> None:
        last_run_timestamp = self._get_job_last_success_time(
            offset_with_metric={"hours": self.params.max_hours_backwards},
            time_format=UNIX_FORMAT,
        )
        self.logger.info(f"Last successful execution timestamp: {last_run_timestamp}")

        # SOAR -> SCC sync
        self.logger.info("Starting Sync SOAR -> SCC")
        try:
            # Appending new 'external' cases to opened cases
            self.sync_soar_to_scc_for_external(last_run_timestamp=last_run_timestamp)
            # Appending new 'internal' cases to opened cases
            self.sync_soar_to_scc_for_internal(last_run_timestamp=last_run_timestamp)
        except (BadGatewayError, ResourceExhaustedError, UnavailableError) as e:
            self.logger.error(
                f"SCC services are temporarily unavailable, received error: {e}. "
                f"The job will gracefully exit and retry on next iteration."
            )
            return

        self._save_timestamp_by_unique_id(self.job_start_time)

        # SCC -> SOAR sync
        self.logger.info("Starting Sync SCC -> SOAR")
        scc_soar_sync_start = unix_now()
        case_to_finding_details = defaultdict(set)
        ack_ids = []

        try:
            self.logger.info(
                "Fetching new notifications for finding updates "
                "from SCC related to open cases"
            )
            findings: list[GSCCDatamodels.PostureFindingAlert] = (
                self.api_client.get_posture_alerts(
                    self.subscription,
                    max_alerts_to_fetch=GSCCConstants.MAX_ALERTS_TO_FETCH,
                )
            )
            for finding_ in sorted(
                findings, key=lambda f: f.last_update_time, reverse=True
            ):
                case_findings = case_to_finding_details[
                    int(finding_.external_systems.case_id)
                ]
                if finding_ in case_findings:
                    ack_ids.append(finding_.ack_id)
                    continue

                case_findings.add(finding_)

            self.logger.info(f"Found {len(case_to_finding_details)} cases to process.")
        except (
            BadGatewayError,
            DeadlineExceededError,
            ResourceExhaustedError,
            UnavailableError,
        ) as e:
            self.logger.error(
                f"SCC services are temporarily unavailable, received error: {e}. "
                f"The job will gracefully exit and retry on next iteration."
            )
            return

        for case_id, findings in case_to_finding_details.items():
            self.logger.info(f"Processing SOAR case {case_id}")

            if is_approaching_timeout(
                connector_starting_time=scc_soar_sync_start,
                python_process_timeout=GSCCConstants.JOB_ACK_DEADLINE,
            ):
                self.logger.info("Timeout is approaching. Job will gracefully exit.")
                break

            # Update case finding context
            findings_context_str = self._get_case_context_property(
                case_id=case_id, property_key=FINDINGS_CONTEXT_KEY
            )
            _, current_findings_context = load_findings_context(findings_context_str)
            self.logger.info(
                f"Fetched {len(current_findings_context)} context findings. "
            )
            findings_context_map = {
                fc.name_without_location: fc for fc in current_findings_context
            }
            updated_findings_context = set()

            for finding in findings:
                # Build Finding Context object from finding data model
                current_finding_context = findings_context_map.get(
                    finding.name_without_location
                )
                previous_update_time = getattr(
                    current_finding_context, "last_update_time", None
                )

                if (
                    previous_update_time is not None
                    and previous_update_time > finding.last_update_time
                ):
                    self.logger.info(
                        f"Update to finding {finding.id} is outdated, skipping..."
                    )
                    continue

                updated_finding_context = FindingContext(
                    finding_id=finding.id,
                    status=finding.state,
                    mute=finding.mute,
                    aps_score=finding.aps_score,
                    severity=finding.severity,
                    resource_name=finding.resource.asset_resource_name,
                    cloud_provider=(
                        current_finding_context.cloud_provider
                        if current_finding_context is not None
                        else finding.resource.cloud_provider
                    ),
                    project_display_name=(
                        current_finding_context.project_display_name
                        if current_finding_context is not None
                        else None
                    ),
                    alert_identifier=(
                        current_finding_context.alert_identifier
                        if current_finding_context is not None
                        else None
                    ),
                    tc_count=sum(
                        group_data["groupType"] == GSCCConstants.TOXIC_COMBINATION_GROUP
                        for group_data in finding.group_memberships
                    ),
                    last_update_time=finding.last_update_time,
                )

                try:
                    if current_finding_context is not None:
                        self._check_severity_transition(
                            case_id=case_id,
                            finding_category=finding.category,
                            current_finding_context=current_finding_context,
                            updated_finding_context=updated_finding_context,
                        )
                        self._check_status_transition(
                            case_id=case_id,
                            current_finding_context=current_finding_context,
                            updated_finding_context=updated_finding_context,
                        )
                        self._check_mute_transition(
                            case_id=case_id,
                            current_finding_context=current_finding_context,
                            updated_finding_context=updated_finding_context,
                        )
                        self._check_tc_count_transition(
                            case_id=case_id,
                            current_finding_context=current_finding_context,
                            updated_finding_context=updated_finding_context,
                        )
                        if finding.is_toxic_combination:
                            self._check_aps_score_transition(
                                case_id=case_id,
                                current_finding_context=current_finding_context,
                                updated_finding_context=updated_finding_context,
                            )

                # pylint: disable=broad-exception-caught
                except Exception as e:
                    self.logger.error(f"Failed to sync case {case_id}, error is: {e}")

                updated_findings_context.add(updated_finding_context)
                ack_ids.append(finding.ack_id)

            # FIXME: need to introduce some kind of context size management
            #        to not overflow
            updated_findings_context.update(current_findings_context)
            self.logger.info(
                f"Saving {len(updated_findings_context)} updated findings to context"
            )
            finding_context_json = create_scc_finding_state_json(
                updated_findings_context, instance_url=self.instance_url
            )
            self._set_case_context_property(
                case_id=case_id,
                property_key=FINDINGS_CONTEXT_KEY,
                property_value=json.dumps(finding_context_json),
            )

            self._check_case_closure(
                case_id=case_id, findings_context=updated_findings_context
            )

        self.api_client.ack_pubsub_findings(
            sub_name=self.subscription.name, ack_ids=ack_ids
        )


def main() -> None:
    SyncSCCData(SYNC_DATA_JOB_NAME).start()


if __name__ == "__main__":
    main()
