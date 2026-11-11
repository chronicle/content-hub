"""
Module that defines and abstract class for an ITSM job that will be
implemented by different products
"""
from __future__ import annotations

from __future__ import annotations

import collections
import json
from abc import abstractmethod
from datetime import datetime
from typing import Generic, Iterable, Mapping, MutableMapping, Sequence, TypeVar

import requests

from soar_sdk.Siemplify import CASE_FILTER_MAX_RESULTS
from soar_sdk.SiemplifyDataModel import (
    CaseFilterOperatorEnum,
    CaseFilterSortByEnum,
    CaseFilterSortOrderEnum,
    CaseFilterStatusEnum,
)
from soar_sdk.SiemplifyUtils import unix_now, utc_now, validate_property_value

from TIPCommon.base.action.data_models import CloseCaseOrAlertMaintenanceRootCauses
from TIPCommon.base.job import Job
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC, UNIX_FORMAT
from TIPCommon.data_models import (
    CASE_DATA_STATUS_VAL_NAME_MAP,
    CASE_PRIORITY_VAL_NAME_MAP,
    CaseDataStatus,
    CaseDetails,
)
from TIPCommon.exceptions import GeneralJobException, InternalJSONDecoderError
from TIPCommon.rest.soar_api import SoarApiServerError, get_case_overview_details
from TIPCommon.smp_io import read_ids, write_ids_with_timestamp
from TIPCommon.soar_ops import (
    create_slo_message,
    get_soar_case_comments,
    get_user_by_id,
    is_slo_comment,
    remove_prefix_from_comments,
)
from TIPCommon.types import JSON
from TIPCommon.utils import get_unique_items_by_difference, none_to_default_value

from scc_enterprise.core.SCCEnterpriseConsts import (
    BACKLOG_RETRIES_LIMIT,
    CASE_FAILURE_BACKLOG_DB_KEY,
    CASE_FAILURE_BACKLOG_FILE_NAME,
    CASE_PRIORITY_TO_TICKET_SEVERITY,
    CASE_SLO_DAYS_INTERVALS,
    CASE_TICKET_MAP_DB_KEY,
    CASE_TICKET_MAP_FILE_NAME,
    CLOSED_BY_SCCE_COMMENT,
    CLOSED_STATUSES,
    EXTERNAL_SCC_TICKET_INFO,
    FINDINGS_CONTEXT_KEY,
    SCCE_COMMENT_PREFIX,
    NOT_AVAILABLE,
    RESOLVED_STATUS,
)
from scc_enterprise.core.SCCEnterpriseDatamodels import (
    CaseIterationResult,
    CaseIterationSetup,
    ExternalSCCTicketInfo,
    FindingContext,
    ITSMTicketDetailsForSCC,
    SOARCaseDetailsForSCC,
    TicketIterationResult,
    TicketIterationSetup,
)
from scc_enterprise.core.SCCEnterpriseUtils import construct_soar_case_url, soar_supports_scce_phase_2


CLOSE_CASE_ROOT_CAUSE = CloseCaseOrAlertMaintenanceRootCauses.OTHER.value
CLOSE_CASE_REASON = "Maintenance"
UPDATE_CASE_CONTEXT_COMMENT = f"{SCCE_COMMENT_PREFIX}Updated case context."

DEFAULT_HOURS_BACKWARDS = 0

_Ticket = TypeVar("_Ticket")
_Manager = TypeVar("_Manager")


class SyncCommentError(GeneralJobException):
    """Sync comments error"""


class SyncSoarITSM(Job, Generic[_Ticket, _Manager]):
    """Abstract class that defines the flow of an SCC Enterprise ITSM sync job"""

    def __init__(self, script_name: str, integration_name: str) -> None:
        super().__init__(script_name)

        if not soar_supports_scce_phase_2(self.soar_job):
            raise GeneralJobException(
                f"This JOB is not supported by SOAR SDK in current version: "
                f"{self.soar_job.get_system_version()}. Please Upgrade your "
                "SOAR platform to latest version to execute this job."
            )

        self.itsm_comment_prefix = f"{integration_name}: "
        self._case_ids_to_context_mapping = {}

    # ==================== Abstract Methods ==================== #

    @abstractmethod
    def _get_ticket_id_to_comments_map(
        self, ticket: _Ticket
    ) -> Mapping[str, list[str]]:
        """Creates a map of ticket ID -> ticket comments for a single ticket

        The mapping should follow this structure:
        {
            "ticket_id": [
                "comment 1",
                "comment 2",
                "comment 3"
            ]
        }

        Args:
            ticket:
                A ticket containing the relevant ticket details.
                (The type of ticket is the same type the following
                _get_ticket_id_to_details_map and
                _get_bulk_ticket_id_to_details_map methods return as the
                values for each ticket ID)

        Raises:
            NotImplementedError: If not overridden

        Returns:
            A mapping that takes a specific ticket ID to its comments
        """
        raise NotImplementedError

    @abstractmethod
    def _get_bulk_ticket_id_to_comments_map(
        self, tickets: Iterable[_Ticket]
    ) -> Mapping[str, list[str]]:
        """Creates a map of ticket ID -> ticket comments for multiple ticket IDs

        The comment in the list should be ordered by creation time (old->new)
        to make sure the comments will be added one by one on the same order

        The mapping should follow this structure:
        {
            "ticket_id 1": [
                "comment 1",
                "comment 2",
                "comment 3"
            ],
            "ticket_id 2": [
                "comment 1",
                "comment 2",
                "comment 3"
            ]
        }

        Args:
            tickets:
                An iterable obj containing tickets with ticket details.
                (The type of each ticket is the same type that the following
                _get_ticket_id_to_details_map and
                _get_bulk_ticket_id_to_details_map methods return as the
                values for each ticket ID)

        Raises:
            NotImplementedError: If not overridden

        Returns:
            A mapping that takes each specific ticket ID to its comments
        """
        raise NotImplementedError

    @abstractmethod
    def _get_ticket_id_to_details_map(self, ticket_id: str) -> Mapping[str, _Ticket]:
        """Creates a map of ticket ID -> ticket details for a single ticket ID

        The type of the values in the returned mapping could be anything,
        and is the value that will be passed and is expected from the following
        _get_ticket_id_to_comments_map() and
        _get_bulk_ticket_id_to_comments_map() methods as their argument.
        Please make sure they are aligned

        Args:
            ticket_id: The ticket ID whose details should be requested

        Raises:
            NotImplementedError: If not overridden

        Returns:
            A mapping that takes a specific ticket ID to its correlating details
        """
        raise NotImplementedError

    @abstractmethod
    def _get_bulk_ticket_id_to_details_map(
        self,
        ticket_ids: Sequence[str] | None = None,
        last_run_timestamp: int | None = None,
    ) -> Mapping[str, _Ticket]:
        """Creates a map of ticket ID -> ticket details for multiple ticket IDs

        The type of the values in the mapping could be anything, and is the
        value that will be passed and is expected from the
        _get_ticket_id_to_comments_map and
        _get_bulk_ticket_id_to_comments_map methods as an argument.
        Please make sure they are aligned

        Args:
            ticket_ids:
                An iterable object containing the IDs that their details should
                be requested in bulk
            last_run_timestamp: The last successful start timestamp of the job

        Raises:
            NotImplementedError: If not overridden

        Returns:
            A mapping that takes all ticket IDs to their correlating details
        """
        raise NotImplementedError

    @abstractmethod
    def _add_comment_to_ticket(self, comment: str, ticket_id: str) -> None:
        """Send a comment to a ticket by the ticket ID

        Args:
            comment: The comment to add to the ticket
            ticket_id: The ticket ID that the comment should be added to

        Raises:
            NotImplementedError: If not overridden
        """
        raise NotImplementedError

    @abstractmethod
    def _parse_ticket_details_for_scc(
        self, ticket: _Ticket, **additional_keys
    ) -> ITSMTicketDetailsForSCC:
        """Parse a ticket to it's correlating ITSMTicketDetailsForSCC object

        This is done to update the external SCC info with new updates about
        the ticket details.

        Args:
            ticket:
            The ticket that has the ticket's relevant data
            (The type of ticket is the same type that the following
            _get_ticket_id_to_details_map and
            _get_bulk_ticket_id_to_details_map methods return as the
            values for each ticket ID)

        Raises:
            NotImplementedError: If not overridden

        Returns:
            An object that will be used for updating external SCC info
        """
        raise NotImplementedError

    @abstractmethod
    def _close_ticket(self, ticket_id: str) -> None:
        """Close a ticket by its ticket ID

        Args:
            ticket_id: The ID of the ticket that should be closed

        Raises:
            NotImplementedError: If not overridden
        """
        raise NotImplementedError

    @abstractmethod
    def _get_ticket_status(self, ticket: _Ticket) -> str:
        """Extract the ticket status from the ticket object

        Args:
            ticket:
                The ticket that has the ticket's relevant data
                (The type of ticket is the same type that the following
                _get_ticket_id_to_details_map and
                _get_bulk_ticket_id_to_details_map methods return as the
                values for each ticket ID)

        Raises:
            NotImplementedError: If not overridden

        Returns:
            The ticket's status - should match the statuses format in the
            "Closing Statuses" parameter values
        """
        raise NotImplementedError

    @abstractmethod
    def _set_ticket_status(self, ticket: _Ticket, new_status: str) -> None:
        """Set the ticket's status

        Args:
            ticket:
                The ticket that has the ticket's relevant data
                (The type of ticket is the same type that the following
                _get_ticket_id_to_details_map and
                _get_bulk_ticket_id_to_details_map methods return as the
                values for each ticket ID)
            new_status: The new state to set to the ticket

        Raises:
            NotImplementedError: If not overridden
        """
        raise NotImplementedError

    @abstractmethod
    def _get_ticket_case_uri(self, ticket: _Ticket) -> str:
        """Extract the ticket's case uri from the ticket object

        Args:
            ticket:
                The ticket that has the ticket's relevant data
                (The type of ticket is the same type that the following
                _get_ticket_id_to_details_map and
                _get_bulk_ticket_id_to_details_map methods return as the
                values for each ticket ID)

        Raises:
            NotImplementedError: If not overridden

        Returns:
            The ticket's case uri as string or empty string
        """
        raise NotImplementedError

    @abstractmethod
    def _set_ticket_update_time(self, ticket: _Ticket, update_time: datetime) -> None:
        """Set the ticket's status

        Args:
            ticket:
                The ticket that has the ticket's relevant data
                (The type of ticket is the same type that the following
                _get_ticket_id_to_details_map and
                _get_bulk_ticket_id_to_details_map methods return as the
                values for each ticket ID)
            update_time:
                The new update time to set, datetime.datetime object
                using SiemplifyUtils.utc_now()

        Raises:
            NotImplementedError: If not overridden
        """
        raise NotImplementedError

    @abstractmethod
    def _get_environment_for_case_filter(self) -> str | None:
        """Get an environment to filter cases by.

        If None is returned, it will not filter by environments

        Raises:
            NotImplementedError: If not overridden

        Returns:
            A str representing the environment if a case filter by env is needed
            Return None if noe case filter by env is needed
        """
        raise NotImplementedError

    @abstractmethod
    def _get_max_hours_backwards(self) -> int | None:
        """Get the job's max hours backwards.

        If None is returned, it will use 0 for hours backward time lookup

        Raises:
            NotImplementedError: If not overridden

        Returns:
            The max hours backwards to look for cases
        """
        raise NotImplementedError

    @abstractmethod
    def _update_ticket_description(self, ticket_id: str, description: str) -> None:
        """Update a ticket's description

        Args:
            ticket_id (str): The Ticket's ID
            description (str): The description to update
        """
        raise NotImplementedError

    @abstractmethod
    def _update_ticket_severity(self, ticket_id: str, severity: str) -> None:
        """Update a ticket's description

        Args:
            ticket_id (str): The Ticket's ID
            severity (str): The ticket's new severity
        """
        raise NotImplementedError

    @abstractmethod
    def _create_description_table(self, findings: list[FindingContext]) -> str:
        """Create finding resource table for ticket description

        Args:
            findings: A list of FindingContext objects that the table would
                summarize

        Returns:
            str: A table for the descriptions that summarize all case findings
        """
        raise NotImplementedError

    @abstractmethod
    def _update_description_table(self, table: str, description: str) -> str:
        """Update a ticket's description with a new table

        Args:
            table: The new table the description should be updated with
            description: The description which table should be updated

        Returns:
            str: A new description updated with the provided table
        """
        raise NotImplementedError

    # ==================== Job Protected Methods ==================== #

    def _perform_job(self) -> None:
        """Perform the main flow of an SCC <-> ITSM job

        Steps:
        1) Fetch timestamps
        2) Read values from the database (e.g. cached IDs, backlog etc.)
        3) Perform case iterations setup
        4) Perform case iterations
        5) Perform ticket iterations setup
        6) Perform ticket iteration
        7) Save timestamp
        8) Write to database if necessary
        """
        max_hours_backwards = none_to_default_value(
            value_to_check=self._get_max_hours_backwards(),
            value_to_return_if_none=DEFAULT_HOURS_BACKWARDS,
        )

        last_run_timestamp = self._get_job_last_success_time(
            offset_with_metric={"hours": max_hours_backwards}, time_format=UNIX_FORMAT
        )
        self.logger.info(f"Last successful execution timestamp: {last_run_timestamp}")

        self.logger.info("Reading IDs")
        case_id_to_ticket_ids_mapping: dict[str, str] = read_ids(
            self.soar_job,
            db_key=CASE_TICKET_MAP_DB_KEY,
            ids_file_name=CASE_TICKET_MAP_FILE_NAME,
            default_value_to_return={},
        )
        cached_case_ids = set(case_id_to_ticket_ids_mapping)
        self.logger.info("Reading Backlog")
        case_failure_backlog: dict[str, int] = read_ids(
            self.soar_job,
            db_key=CASE_FAILURE_BACKLOG_DB_KEY,
            ids_file_name=CASE_FAILURE_BACKLOG_FILE_NAME,
            default_value_to_return={},
        )

        case_iter_setup = self._case_iteration_setup(
            last_run_timestamp=last_run_timestamp,
            case_id_to_ticket_ids_mapping=case_id_to_ticket_ids_mapping,
        )

        checked_tickets = set()
        case_iter_result = self._case_iteration(
            case_iter_setup=case_iter_setup,
            checked_tickets=checked_tickets,
            case_id_to_ticket_ids_mapping=case_id_to_ticket_ids_mapping,
            last_run_timestamp=last_run_timestamp,
            backlog=case_failure_backlog,
        )

        # Sync tickets that are correlated to cases that weren't modified
        ticket_iter_setup = self._ticket_iteration_setup(
            checked_tickets=checked_tickets,
            case_id_to_ticket_ids_mapping=case_id_to_ticket_ids_mapping,
            last_run_timestamp=last_run_timestamp,
        )

        ticket_iter_result = self._ticket_iteration(
            ticket_iter_setup=ticket_iter_setup,
            case_id_to_ticket_ids_mapping=case_id_to_ticket_ids_mapping,
            backlog=case_failure_backlog,
        )

        self.logger.info("----------------- Finished Syncing -----------------")
        self.logger.info("Saving timestamp")
        self._save_timestamp_by_unique_id(self.job_start_time)

        if (
            cached_case_ids.symmetric_difference(case_id_to_ticket_ids_mapping)
            or case_iter_result.added_cases
            or ticket_iter_result.closed_cases
            or case_iter_result.closed_cases
        ):
            self.logger.info("Writing IDs since cases were added or removed")
            case_ids_in_order = collections.deque(case_id_to_ticket_ids_mapping)
            while not validate_property_value(case_id_to_ticket_ids_mapping):
                del case_id_to_ticket_ids_mapping[case_ids_in_order.popleft()]

            write_ids_with_timestamp(
                self.soar_job,
                ids=case_id_to_ticket_ids_mapping,
                db_key=CASE_TICKET_MAP_DB_KEY,
                ids_file_name=CASE_TICKET_MAP_FILE_NAME,
            )

        if ticket_iter_result.failed_cases or case_iter_result.failed_cases:
            self.logger.info("Writing backlog since there were failed cases")
            write_ids_with_timestamp(
                self.soar_job,
                ids=case_failure_backlog,
                db_key=CASE_FAILURE_BACKLOG_DB_KEY,
                ids_file_name=CASE_FAILURE_BACKLOG_FILE_NAME,
            )

    def _ticket_iteration_setup(
        self,
        checked_tickets: set[str],
        case_id_to_ticket_ids_mapping: Mapping[str, str],
        last_run_timestamp: int,
    ) -> TicketIterationSetup:
        """Setup stages for ticket iteration

        The setup includes:
            1) Creating a map {ticket_id -> case_id} for relevant tickets
            2) Fetching ticket details
            3) Fetching ticket comments

        Args:
            checked_tickets: The tickets that were checked in the previous
                case iteration step of the sync job and shouldn't be checked
                again.
            case_id_to_ticket_ids_mapping: A stored mapping of
                {case_id -> ticket_id} that is used to cache cases and tickets
            last_run_timestamp: The last successful start timestamp of the job

        Returns:
            TicketIterationSetup: A named tuple object that contains the
                {ticket_id -> case_id} mapping, a {ticket_id -> ticket_details}
                mapping and {ticket_id -> ticket_comments} mapping
        """
        # Sync tickets that are correlated to cases that weren't modified
        self.logger.info("Getting bulk ticket details")
        ticket_id_to_details = self._get_bulk_ticket_id_to_details_map(
            last_run_timestamp=last_run_timestamp
        )
        ticket_id_to_details = {
            ticket_id: ticket
            for ticket_id, ticket in ticket_id_to_details.items()
            if (
                self._get_ticket_case_uri(ticket).startswith(self.soar_job.platform_url)
                and ticket_id not in checked_tickets
            )
        }

        self.logger.info("Getting bulk ticket comments")
        ticket_id_to_comments = self._get_bulk_ticket_id_to_comments_map(
            tickets=ticket_id_to_details.values()
        )

        self.logger.info(
            f"Found {len(ticket_id_to_details)} cached tickets which their "
            f"correlated case was not updated since {last_run_timestamp}."
        )

        return TicketIterationSetup(
            ticket_id_to_case_id={
                ticket_id: case_id
                for case_id, ticket_id in case_id_to_ticket_ids_mapping.items()
            },
            ticket_id_to_details=ticket_id_to_details,
            ticket_id_to_comments=ticket_id_to_comments,
        )

    def get_case_external_ticket_info(
        self, case_id: str
    ) -> ExternalSCCTicketInfo | None:
        """Fetch External-SCC-Ticket info from case data."""
        if case_id not in self._case_ids_to_context_mapping:
            case_context_raw = self._get_case_context_property(
                case_id=case_id, property_key=EXTERNAL_SCC_TICKET_INFO
            )
            if case_context_raw is None:
                return None

            case_context = self._parse_case_context(case_context_raw)
            ext_scc_ticket_info = ExternalSCCTicketInfo.from_json(case_context)
            self._case_ids_to_context_mapping[case_id] = ext_scc_ticket_info

        return self._case_ids_to_context_mapping[case_id]

    def _case_iteration_setup(
        self, case_id_to_ticket_ids_mapping: dict[str, str], last_run_timestamp: int
    ) -> CaseIterationSetup:
        """Setup stages for case iteration.

        The setup includes:
            1) Fetch case IDs based on filters
            2) For fetched cases, fetch ticket details
            3) For fetched tickets, fetch ticket comments

        Args:
            case_id_to_ticket_ids_mapping: A mapping of {case_id -> ticket_id}
                that is sorted in the database
            last_run_timestamp: The last successful start timestamp of the job

        Returns:
            CaseIterationSetup: A named tuple object that contains the case IDs,
                a {ticket_id -> ticket_details} mapping and
                {ticket_id -> ticket_comments} mapping
        """
        self.logger.info("Fetching filtered SOAR case IDs")
        env = self._get_environment_for_case_filter()
        envs = [env] if env else None
        case_ids: list[int] = self.soar_job.get_cases_ids_by_filter(
            status=CaseFilterStatusEnum.BOTH,
            update_time_from_unix_time_in_ms=last_run_timestamp,
            start_time_from_unix_time_in_ms=last_run_timestamp,
            operator=CaseFilterOperatorEnum.OR,
            sort_by=CaseFilterSortByEnum.UPDATE_TIME,
            sort_order=CaseFilterSortOrderEnum.ASC,
            max_results=CASE_FILTER_MAX_RESULTS,
            tags=[EXTERNAL_SCC_TICKET_INFO],
            environments=envs,
        )
        self.logger.info(f"Fetched {len(case_ids)} cases that were modified")

        if not case_ids:
            return CaseIterationSetup(
                case_ids=case_ids,
                ticket_id_to_ticket_details={},
                ticket_id_to_ticket_comments={},
            )

        ticket_id_to_ticket_details, ticket_id_to_ticket_comments = (
            self.collect_tickets_for_cases(case_ids, case_id_to_ticket_ids_mapping)
        )
        return CaseIterationSetup(
            case_ids=case_ids,
            ticket_id_to_ticket_details=ticket_id_to_ticket_details,
            ticket_id_to_ticket_comments=ticket_id_to_ticket_comments,
        )

    def collect_tickets_for_cases(
        self, case_ids: Sequence[int], case_id_to_ticket_ids_mapping: dict[str, str]
    ) -> tuple[Mapping[str, _Ticket], Mapping[str, list[str]]]:
        """Fetch tickets and ticket comments for given sequence of case IDs.

        Args:
            case_ids: The sequence of case IDs
            case_id_to_ticket_ids_mapping: A mapping of {case_id -> ticket_id}
                that is sorted in the database


        Returns:
            A tuple containing the tickets and ticket comments mapped to ticket IDs
        """

        cached_ticket_ids = []
        for case_id in case_ids:
            case_id = str(case_id)
            if case_id not in case_id_to_ticket_ids_mapping:
                case_context = self.get_case_external_ticket_info(case_id)
                if not case_context:
                    self.logger.info("Case has not context available. Skipping...")
                    continue

                case_id_to_ticket_ids_mapping[case_id] = case_context.ticket.id_

            cached_ticket_ids.append(case_id_to_ticket_ids_mapping[case_id])

        ticket_id_to_ticket_details = self._get_bulk_ticket_id_to_details_map(
            ticket_ids=cached_ticket_ids
        )
        self.logger.info(
            f"Fetched {len(ticket_id_to_ticket_details)} bulk ITSM tickets details"
        )

        ticket_id_to_ticket_comments = self._get_bulk_ticket_id_to_comments_map(
            tickets=ticket_id_to_ticket_details.values()
        )
        self.logger.info(
            f"Fetched {len(ticket_id_to_ticket_comments)} bulk ITSM "
            f"tickets comments"
        )

        return ticket_id_to_ticket_details, ticket_id_to_ticket_comments

    def _ticket_iteration(
        self,
        ticket_iter_setup: TicketIterationSetup,
        case_id_to_ticket_ids_mapping: MutableMapping[str, str],
        backlog: MutableMapping[str, int],
    ) -> TicketIterationResult:
        """Perform sync iteration over all tickets

        Iteration steps:
            Go over each ticket and case from the setup stage mapping:
                1) Get context property from the database
                2) Get case comments and ticket
                3) Sync comments
                4) Check SLO and send notification in needed
                5) Sync closure based on ticket-case status combination
                6) Update database context
                7) If any case has failed - perform backlog operations

        Args:
            ticket_iter_setup: The result object from the
                _ticket_iteration_setup method
            case_id_to_ticket_ids_mapping: A mapping of {case_id -> ticket_id}
                that is sorted in the database
            backlog: A mapping of {case_id -> number_of_retries} from the
                database to perform backlog operations on failed cases

        Returns:
            TicketIterationResult: A named tuple object containing close_case
                and failed_case booleans that indicate whether cases were
                closed or failed during this stage
        """
        closed_cases = False
        failed_cases = False
        for ticket_id, ticket in ticket_iter_setup.ticket_id_to_details.items():
            self.logger.info(f"==> Going over ticket ID {ticket_id}")
            case_id = str(
                ticket_iter_setup.ticket_id_to_case_id.get(ticket_id)
                or self._get_ticket_case_uri(ticket).split("/")[-1]
            )
            if not case_id:
                self.logger.warn(
                    f"Ticket ID {ticket_id} was not found in Job's context. Skipping..."
                )
                continue

            try:
                self.logger.info("Reading case context property")
                ext_scc_ticket_info = self.get_case_external_ticket_info(case_id)
                if ext_scc_ticket_info is None:
                    self.logger.info("No case context was found. Skipping...")
                    continue

                if ext_scc_ticket_info.case.sync_case is False:
                    self.logger.info(
                        "Case context is marked with sync_case=False. Skipping..."
                    )
                    case_id_to_ticket_ids_mapping.pop(case_id, None)
                    closed_cases = True
                    continue

                og_ext_scc_info = ExternalSCCTicketInfo.from_obj(ext_scc_ticket_info)
                # Sync ticket comments
                self.logger.info(f"Getting comments for case No {case_id}")
                case_comments = get_soar_case_comments(self.soar_job, case_id)

                self.logger.info(
                    f"Syncing comments for case with ID {case_id} and ticket "
                    f"with ID {ticket_id}"
                )
                ticket_comments = ticket_iter_setup.ticket_id_to_comments[ticket_id]
                self._sync_soar_case_and_itsm_ticket_comments(
                    case_id=case_id,
                    itsm_ticket_id=ticket_id,
                    soar_comments=[c.comment for c in case_comments],
                    itsm_comments=ticket_comments,
                )

                try:
                    self.logger.info("Fetching case overview details")
                    case_details = get_case_overview_details(self.soar_job, case_id)
                except requests.HTTPError as e:
                    raise SoarApiServerError(
                        "Failed to get case overview data. "
                        "If the case is a merged case this error is expected "
                        f"and can be ignored.\n The error: {e}"
                    ) from e

                # Check correlated case SLO
                self._check_and_send_slo_warning(
                    case_details=case_details,
                    itsm_ticket_id=ticket_id,
                    itsm_comments=ticket_comments,
                )

                # Check if ticket status is changed
                if self._is_ticket_closed(ticket) and case_details.is_open:
                    self.logger.info(
                        "The ticket is closed but the case is still open, "
                        "closing the correlated case"
                    )
                    self._close_case(case_id, case_details.alerts[0].identifier)
                    self._align_objects_with_closed_case_state(
                        case_details=case_details,
                        ext_scc_ticket_info=ext_scc_ticket_info,
                        case_id_to_ticket_ids_mapping=case_id_to_ticket_ids_mapping,
                    )
                    closed_cases = True

                # Check if ticket SCC data was updated
                self._update_case_and_ticket_ext_info(
                    case=case_details,
                    ticket=ticket,
                    ext_scc_ticket_info=ext_scc_ticket_info,
                    og_ext_scc_info=og_ext_scc_info,
                )

            except Exception as e:
                self.logger.error("------- Failed to sync ticket -------")
                self.logger.error(
                    f"Failed to sync ticket {ticket_id} with its correlating case"
                )
                self.logger.error(f"Error: {e}")
                self.logger.exception(e)

                self._check_backlog(
                    case_id=case_id,
                    backlog=backlog,
                    case_id_to_ticket_ids_mapping=case_id_to_ticket_ids_mapping,
                )
                failed_cases = True
                closed_cases = True

        return TicketIterationResult(closed_cases, failed_cases)

    def _case_iteration(
        self,
        case_iter_setup: CaseIterationSetup,
        case_id_to_ticket_ids_mapping: MutableMapping[str, str],
        checked_tickets: set[str],
        last_run_timestamp: int,
        backlog: MutableMapping[str, int],
    ) -> CaseIterationResult:
        """Perform sync iteration over all fetched case IDs

        Iteration steps:
            Go over each case and ticket from the setup stage mapping:
                1) Get context property from the database
                2) Get ticket details and comments
                3) Get case details and comments
                4) Sync comments
                5) Check SLO and send notification in needed
                6) Sync closure based on ticket-case status combination
                7) Update ticket description
                8) Update ticket severity
                9) Sync case priority with ticket severity
                10) Update database context
                11) If any case has failed - perform backlog operations

        Args:
            case_iter_setup: The result object from the
                _case_iteration_setup method
            case_id_to_ticket_ids_mapping: A mapping of {case_id -> ticket_id}
                that is sorted in the database
            checked_tickets: A set of ticket IDs that this method updates
                to track which IDs have been iterated successfully
            last_run_timestamp: The job's last successful run start timestamp
            backlog: A mapping of {case_id -> number_of_retries} from the
                database to perform backlog operations on failed cases

        Returns:
            CaseIterationResult: A named tuple object containing close_case,
                added_cases and failed_case booleans that indicate whether
                cases were closed, added or failed during this stage
        """
        closed_cases = False
        added_cases = False
        failed_cases = False
        for case_id in case_iter_setup.case_ids:
            case_id = str(case_id)
            self.logger.info(f"==> Going over case No. {case_id}")
            try:
                self.logger.info("Reading case context property")
                ext_scc_ticket_info = self.get_case_external_ticket_info(case_id)

                if not ext_scc_ticket_info:
                    self.logger.info("No case context was found. Skipping...")
                    case_id_to_ticket_ids_mapping.pop(case_id, None)
                    closed_cases = True
                    continue

                og_ext_scc_info = ExternalSCCTicketInfo.from_obj(ext_scc_ticket_info)
                if not ext_scc_ticket_info.case.sync_case:
                    self.logger.info(
                        "Case context is marked with sync_case=False. Skipping..."
                    )
                    case_id_to_ticket_ids_mapping.pop(case_id, None)
                    closed_cases = True
                    continue

                try:
                    self.logger.info("Fetching case overview details")
                    case_details = get_case_overview_details(self.soar_job, case_id)
                except requests.HTTPError as e:
                    raise SoarApiServerError(
                        "Failed to get case overview data. "
                        "If the case is a merged case this error is expected "
                        f"and can be ignored.\n The error: {e}"
                    ) from e

                itsm_ticket_id = (
                    case_id_to_ticket_ids_mapping.get(case_id)
                    or ext_scc_ticket_info.ticket.id_
                )
                self.logger.info(f"Correlated ticket ID: {itsm_ticket_id}")

                # Get case/ticket details and comments if missing in bulk
                if case_id not in case_id_to_ticket_ids_mapping:
                    self.logger.info(
                        "Case ID was not in the stored IDs. "
                        "Fetching its ticket details and comments and "
                        "adding to the stored IDs"
                    )
                    case_id_to_ticket_ids_mapping[case_id] = itsm_ticket_id
                    ticket_details_map = self._get_ticket_id_to_details_map(
                        ticket_id=itsm_ticket_id
                    )
                    ticket_details = ticket_details_map[itsm_ticket_id]

                    itsm_comments_map = self._get_ticket_id_to_comments_map(
                        ticket=ticket_details
                    )
                    itsm_comments = itsm_comments_map[itsm_ticket_id]

                else:  # Taking ticket details and comments from bulk data
                    self.logger.info(
                        "Case ID was found in stored IDs, taking ticket "
                        "details and comments from the fetched bulk data"
                    )
                    ticket_details = case_iter_setup.ticket_id_to_ticket_details[
                        itsm_ticket_id
                    ]
                    itsm_comments = case_iter_setup.ticket_id_to_ticket_comments[
                        itsm_ticket_id
                    ]

                if self._is_ticket_closed(ticket_details) and not case_details.is_open:
                    self.logger.info(
                        "Both the case and the ticket are closed. "
                        "Deleting the case ID from the stored IDs if it's "
                        "there. Skipping case comment sync..."
                    )
                    ext_scc_ticket_info.case.sync_case = False
                    case_id_to_ticket_ids_mapping.pop(case_id, None)
                    closed_cases = True

                else:
                    self.logger.info("Getting case comments")
                    case_comments = get_soar_case_comments(self.soar_job, case_id)
                    self.logger.info(
                        f"Syncing comments for case with ID {case_id} and "
                        f"ticket with ID {itsm_ticket_id}"
                    )
                    soar_comments = [comment.comment for comment in case_comments]
                    self._sync_soar_case_and_itsm_ticket_comments(
                        case_id=case_id,
                        itsm_ticket_id=itsm_ticket_id,
                        soar_comments=soar_comments,
                        itsm_comments=itsm_comments,
                    )

                if (
                    not self._is_ticket_closed(ticket_details)
                    and case_details.is_closed
                ):
                    self.logger.info(
                        "The case status is closed, but the ticket is not, "
                        "closing the correlated ticket "
                        "and removing it from case IDs cache"
                    )
                    self._close_ticket(itsm_ticket_id)
                    self._set_ticket_status(ticket_details, RESOLVED_STATUS)
                    self._set_ticket_update_time(ticket_details, utc_now())
                    ext_scc_ticket_info.case.sync_case = False
                    case_id_to_ticket_ids_mapping.pop(case_id, None)
                    closed_cases = True

                elif not case_details.is_closed:
                    self._check_and_send_slo_warning(
                        case_details=case_details,
                        itsm_ticket_id=itsm_ticket_id,
                        itsm_comments=itsm_comments,
                    )

                if self._is_ticket_closed(ticket_details) and case_details.is_open:
                    self.logger.info(
                        "The ticket is closed but the case is still opened, "
                        "closing the correlated case"
                    )
                    self._close_case(case_id, case_details.alerts[0].identifier)
                    self._align_objects_with_closed_case_state(
                        case_details=case_details,
                        ext_scc_ticket_info=ext_scc_ticket_info,
                        case_id_to_ticket_ids_mapping=case_id_to_ticket_ids_mapping,
                    )
                    closed_cases = True

                finding_context = self._get_finding_context(case_id)
                last_update_time = finding_context["last_update_time"]
                if last_update_time >= last_run_timestamp:
                    new_description = self._update_description_table(
                        description=ext_scc_ticket_info.ticket.description,
                        table=self._create_description_table(
                            finding_context["finding_context_list"]
                        ),
                    )
                    if new_description != ext_scc_ticket_info.ticket.description:
                        self.logger.info("Updating ticket description")
                        ext_scc_ticket_info.ticket.description = new_description
                        self._update_ticket_description(
                            ticket_id=itsm_ticket_id, description=new_description
                        )

                case_priority = CASE_PRIORITY_VAL_NAME_MAP[case_details.priority]
                if case_priority != ext_scc_ticket_info.case.case_priority:
                    self.logger.info(
                        "Case Priority was changed from "
                        f'"{ext_scc_ticket_info.case.case_priority}" to '
                        f'"{case_priority}" - Syncing to ticket'
                    )
                    severity = CASE_PRIORITY_TO_TICKET_SEVERITY[case_priority]
                    self._update_ticket_severity(itsm_ticket_id, severity)

                self._update_case_and_ticket_ext_info(
                    case=case_details,
                    ticket=ticket_details,
                    ext_scc_ticket_info=ext_scc_ticket_info,
                    og_ext_scc_info=og_ext_scc_info,
                )

                checked_tickets.add(itsm_ticket_id)

            except Exception as e:
                self.logger.error("------- Failed to sync case -------")
                self.logger.error(
                    f"Failed to sync case {case_id} with its correlating ticket"
                )
                self.logger.error(f"Error: {e}")
                self.logger.exception(e)

                self._check_backlog(case_id, backlog, case_id_to_ticket_ids_mapping)
                failed_cases = True
                closed_cases = True

        return CaseIterationResult(
            added_cases=added_cases,
            closed_cases=closed_cases,
            failed_cases=failed_cases,
        )

    def _check_backlog(
        self,
        case_id: str,
        backlog: MutableMapping[str, int],
        case_id_to_ticket_ids_mapping: MutableMapping[str, str],
    ) -> None:
        """Deal with failure backlog logic

        Args:
            case_id: Failed case ID
            backlog: Backlog from DB
            case_id_to_ticket_ids_mapping: Mapping of case id to ticket id
        """
        self.logger.error("Checking case backlog")
        if case_id not in backlog:
            self.logger.info(f"Adding case No. {case_id} to backlog with 0 retries")
            backlog[case_id] = 0
            return

        backlog[case_id] += 1
        retries = backlog[case_id]
        self.logger.info(f"Case No. {case_id} - increased retries number to {retries}")
        if retries > BACKLOG_RETRIES_LIMIT:
            self.logger.info(
                f"Case No. {case_id} reached retry limit of "
                f"{BACKLOG_RETRIES_LIMIT}. "
                "Removing from cache and backlog"
            )
            del backlog[case_id]
            case_id_to_ticket_ids_mapping.pop(case_id, None)

    def _sync_soar_case_and_itsm_ticket_comments(
        self,
        case_id: str,
        itsm_ticket_id: str,
        soar_comments: list[str],
        itsm_comments: list[str],
    ) -> None:
        """Sync comments of SOAR case and ITSM ticket

        Args:
            case_id: The ID of the case to be synced
            itsm_ticket_id: The ID of the ticket to be synced
            soar_comments: All SOAR case comments
            itsm_comments: All ITSM ticket comments

        Raises:
            SyncCommentError: If failed to sync due to  any error that may occur
        """
        try:
            # Remove prefix for comment comparison
            soar_comments = remove_prefix_from_comments(
                comments=soar_comments, prefix=self.itsm_comment_prefix
            )
            itsm_comments = remove_prefix_from_comments(
                comments=itsm_comments, prefix=SCCE_COMMENT_PREFIX
            )

            # Filter SLO comments from the ticket
            # SLO comment is considered without the prefix
            itsm_comments = [
                comment for comment in itsm_comments if not is_slo_comment(comment)
            ]

            new_soar_case_comments = get_unique_items_by_difference(
                item_pool=soar_comments, items_to_remove=itsm_comments
            )
            new_itsm_ticket_comments = get_unique_items_by_difference(
                item_pool=itsm_comments, items_to_remove=soar_comments
            )

            if new_soar_case_comments:
                self.soar_job.LOGGER.info(
                    f"Found {len(new_soar_case_comments)} comments to add "
                    f"to ITSM ticket {itsm_ticket_id}.\nAdding comments"
                )
                self._send_soar_comments_to_itsm(
                    new_soar_comments=new_soar_case_comments, ticket_id=itsm_ticket_id
                )

            if new_itsm_ticket_comments:
                self.soar_job.LOGGER.info(
                    f"Found {len(new_itsm_ticket_comments)} comments to "
                    f"add to Chronicle SOAR case {case_id}.\nAdding comments"
                )
                self._send_itsm_comments_to_soar(
                    case_id=case_id, new_itsm_comments=new_itsm_ticket_comments
                )

        except Exception as e:
            raise SyncCommentError(
                "Failed tp sync comments between case "
                f"{case_id} and ticket {itsm_ticket_id}"
            ) from e

    def _send_soar_comments_to_itsm(
        self,
        new_soar_comments: Iterable[str],
        ticket_id: str,
        soar_comment_prefix: str = SCCE_COMMENT_PREFIX,
    ) -> None:
        """Add comments to ITSM ticket

        Args:
            new_soar_comments: Case comments to add to the ticket
            ticket_id: The ticket ID
            soar_comment_prefix:
                Prefix for comments. Defaults to SOAR_COMMENT_PREFIX.
        """
        for comment in new_soar_comments:
            try:
                prefixed_comment = f"{soar_comment_prefix}{comment}"
                self._add_comment_to_ticket(
                    comment=prefixed_comment, ticket_id=ticket_id
                )

            except Exception as e:
                self.logger.error(
                    f"Failed to add comment to ITSM ticket No. {ticket_id}"
                )
                self.logger.exception(e)

    def _send_itsm_comments_to_soar(
        self, case_id: str, new_itsm_comments: Iterable[str]
    ) -> None:
        """Add comments to case

        Args:
            case_id: The ID for the case to add comments to
            new_itsm_comments: The comments to add
        """
        for comment in new_itsm_comments:
            try:
                comment_with_prefix = f"{self.itsm_comment_prefix}{comment}"
                self.soar_job.add_comment(
                    comment=comment_with_prefix, case_id=case_id, alert_identifier=None
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to add comment to case {case_id}, Reason: {e}"
                )
                self.logger.exception(e)

    def _check_and_send_slo_warning(
        self, case_details: CaseDetails, itsm_ticket_id: str, itsm_comments: list[str]
    ) -> None:
        """Check if an SLO message should be sent, and send it if needed

        Args:
            case_details: The current case overview details object
            itsm_ticket_id: The case's correlating ticket
            itsm_comments: List of all comments from ticket itsm_ticket_id
        """
        if case_details.stage_sla.sla_expiration_time is not None:
            self.logger.info(
                "Found SLO for the current case. "
                "Checking whether a time based warning should be sent"
            )
            slo_comment = create_slo_message(
                slo=case_details.stage_sla.sla_expiration_time,
                interval_days=CASE_SLO_DAYS_INTERVALS,
                existing_comments=remove_prefix_from_comments(
                    comments=itsm_comments, prefix=SCCE_COMMENT_PREFIX
                ),
            )

            if slo_comment is not None:
                self.logger.info(
                    "A warning about the SLO is added to the ITSM ticket.\n"
                    f'Comment "{slo_comment}"'
                )
                self._send_soar_comments_to_itsm(
                    ticket_id=itsm_ticket_id, new_soar_comments=[slo_comment]
                )

            else:
                self.logger.info("No new SLO warning should be added to the case")

    def _update_ext_info(
        self,
        original_ext_scc_info_copy: ExternalSCCTicketInfo,
        updated_ext_scc_ticket_info: ExternalSCCTicketInfo,
    ) -> None:
        """Update case context if there's new updated data to update

        Args:
            original_ext_scc_info_copy: The original context
            updated_ext_scc_ticket_info: The updated context
        """
        if original_ext_scc_info_copy == updated_ext_scc_ticket_info:
            self.logger.info(
                "No SCC relevant data was changed in neither the case and ticket"
            )
            return

        if (
            updated_ext_scc_ticket_info.case.external_system_update_time
            < self.job_start_time
        ):
            self.logger.info(
                "Updating the case modifications time to push update into "
                "Sync SCC Data Job"
            )
            self._update_case_modification_time(updated_ext_scc_ticket_info.case)
            updated_ext_scc_ticket_info.case.external_system_update_time = (
                unix_now() // NUM_OF_MILLI_IN_SEC
            )

        self.logger.info(
            "Found data to update in external info. "
            "Setting case context property with updated data"
        )
        ext_json_str = json.dumps(updated_ext_scc_ticket_info.to_full_json())
        self._set_case_context_property(
            case_id=updated_ext_scc_ticket_info.case.external_uid,
            property_key=EXTERNAL_SCC_TICKET_INFO,
            property_value=ext_json_str,
        )

    def _update_case_modification_time(self, case: SOARCaseDetailsForSCC):
        """Update case modification time with NOOP change.

        Setting the same priority

        Args:
            case: soar case details for scc object
        """
        if case.status == CASE_DATA_STATUS_VAL_NAME_MAP[CaseDataStatus.OPENED]:
            self.soar_job.change_case_priority(
                priority=case.case_priority,
                case_id=case.external_uid,
                alert_identifier=None,
            )

        else:
            self.soar_job.add_comment(
                comment=UPDATE_CASE_CONTEXT_COMMENT,
                case_id=case.external_uid,
                alert_identifier=None,
            )

    def _update_case_and_ticket_ext_info(
        self,
        case: CaseDetails,
        ticket: _Ticket,
        og_ext_scc_info: ExternalSCCTicketInfo,
        ext_scc_ticket_info: ExternalSCCTicketInfo,
    ) -> None:
        """Update case and ticket external data in case context

        Args:
            case: The case details object
            ticket: The ticket details object
            og_ext_scc_info: The original fetched external context object
            ext_scc_ticket_info: The updated external context object
        """
        self.logger.info("Checking for updated case data")
        scc_case_details = self._parse_case_details_for_scc(
            case=case, current_ext_scc_case_info=ext_scc_ticket_info.case
        )
        self.logger.info("Checking for updated ticket data")
        scc_ticket_details = self._parse_ticket_details_for_scc(
            ticket=ticket, **ext_scc_ticket_info.ticket.additional_keys
        )

        ext_scc_ticket_info.update_by_case_details(scc_case_details)
        ext_scc_ticket_info.update_by_ticket_details(scc_ticket_details)

        self._update_ext_info(og_ext_scc_info, ext_scc_ticket_info)

    def _is_ticket_closed(self, ticket: _Ticket) -> bool:
        """Check if the ticket has a closed status

        Args:
            ticket: The ticket object

        Returns:
            True if the ticket is closed, else False
        """
        ticket_status = self._get_ticket_status(ticket)
        return ticket_status.casefold() in (
            status.casefold() for status in CLOSED_STATUSES
        )

    def _parse_case_details_for_scc(
        self, case: CaseDetails, current_ext_scc_case_info: SOARCaseDetailsForSCC
    ) -> SOARCaseDetailsForSCC:
        """Parse a new external info case object to update the current data

        Args:
            case: All case details that the ext data will be updated from
            current_ext_scc_case_info:
                The current case ext data to take values that shouldn't change

        Returns:
            A new SOARCaseDetailsForSCC object to update the ext scc data with
        """
        mod_time = case.modification_time_unix_time_ms // NUM_OF_MILLI_IN_SEC

        sla = case.stage_sla.sla_expiration_time
        sla = sla // NUM_OF_MILLI_IN_SEC if sla is not None else NOT_AVAILABLE

        assignee = case.assigned_user
        user = get_user_by_id(self.soar_job, case.assigned_user)
        if user is not None:
            assignee = f"{user.first_name} {user.last_name}".strip()

        case_uri = construct_soar_case_url(case.id_, self.soar_job.platform_url)
        return SOARCaseDetailsForSCC(
            sync_case=current_ext_scc_case_info.sync_case,
            # Not updating ext system name
            name=current_ext_scc_case_info.name,
            assignees=assignee,
            # Not updating ext system name
            external_uid=current_ext_scc_case_info.external_uid,
            status=CASE_DATA_STATUS_VAL_NAME_MAP[case.status],
            external_system_update_time=mod_time,
            case_uri=case_uri or NOT_AVAILABLE,
            case_sla=sla,
            case_priority=CASE_PRIORITY_VAL_NAME_MAP[case.priority],
            **current_ext_scc_case_info.additional_keys,
        )

    def _get_finding_context(
        self, case_id: str
    ) -> dict[str, int | list[FindingContext]]:
        """Get the context value under SCC-FINDINGS-STATE key in the database.

        Notes:
            The structure of the returned dict is the following:
            {
                "last_update_time": 1701254186123,
                "finding_context_list": [
                    <FindingContext object 1>,
                    <FindingContext object 2>
                ]
            }

        Args:
            case_id (int): The case ID (e.g. 21)

        Returns:
            dict[str, int | FindingContext]: The finding context from the DB

        """
        finding_context_str = self._get_case_context_property(
            case_id=case_id, property_key=FINDINGS_CONTEXT_KEY
        )

        finding_context = self._parse_case_context(finding_context_str)
        finding_context["finding_context_list"] = [
            FindingContext(**finding_context_json)
            for finding_context_json in finding_context["finding_context_list"]
        ]

        return finding_context

    def get_ext_scc_context(
        self, case_context: JSON
    ) -> tuple[ExternalSCCTicketInfo, ExternalSCCTicketInfo]:
        """Get 2 SCC context objects.

        This should be used to update one object and keep one for reference.

        Args:
            case_context: The case context property JSON

        Returns:
            tuple[ExternalSCCTicketInfo, ExternalSCCTicketInfo]: A tuple of two
                ExternalSCCTicketInfo objects
        """
        case_context = self._parse_case_context(case_context)
        ext_scc_ticket_info = ExternalSCCTicketInfo.from_json(case_context)
        og_ext_scc_info = ExternalSCCTicketInfo.from_obj(ext_scc_ticket_info)

        return ext_scc_ticket_info, og_ext_scc_info

    def _close_case(self, case_id: str, alert_id: str) -> None:
        self.soar_job.close_case(
            case_id=case_id,
            root_cause=CLOSE_CASE_ROOT_CAUSE,
            reason=CLOSE_CASE_REASON,
            comment=CLOSED_BY_SCCE_COMMENT,
            alert_identifier=alert_id,
        )

    @staticmethod
    def _align_objects_with_closed_case_state(
        case_details: CaseDetails,
        ext_scc_ticket_info: ExternalSCCTicketInfo,
        case_id_to_ticket_ids_mapping: MutableMapping[str, str],
    ) -> None:
        case_details.status = CaseDataStatus.CLOSED
        case_details.modification_time_unix_time_ms = unix_now()
        ext_scc_ticket_info.case.sync_case = False
        case_id_to_ticket_ids_mapping.pop(str(case_details.id_), None)

    @staticmethod
    def _parse_case_context(case_context_property_json: str | dict | list) -> JSON:
        """Parse case context to a JSON if it's a string

        Args:
            case_context_property_json: The context property

        Raises:
            InternalJSONDecoderError: If failed to parse from str to dict | list
            GeneralJobException: If the type is not str | dict | list

        Returns:
            The parsed JSON
        """
        if isinstance(case_context_property_json, str):
            try:
                return json.loads(case_context_property_json)
            except json.JSONDecodeError as e:
                raise InternalJSONDecoderError(
                    f"Failed to parse {EXTERNAL_SCC_TICKET_INFO} as a JSON"
                ) from e

        if isinstance(case_context_property_json, (dict, list)):
            return case_context_property_json

        raise GeneralJobException(
            f"{EXTERNAL_SCC_TICKET_INFO} has invalid type: "
            f"{type(case_context_property_json)}"
        )
