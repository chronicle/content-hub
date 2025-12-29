from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from soar_sdk.SiemplifyDataModel import (
    CaseFilterOperatorEnum,
    CaseFilterSortByEnum,
    CaseFilterSortOrderEnum,
    CaseFilterStatusEnum,
)
from TIPCommon.base.job import Job
from TIPCommon.rest.soar_api import get_case_overview_details

from ..core import constants
from ..core.api.api_client import ApiParameters, SampleApiClient
from ..core.auth import (
    AuthenticatedSession,
    SessionAuthenticationParameters,
    build_auth_params,
)

if TYPE_CHECKING:
    from typing import NoReturn

    import requests
    from TIPCommon.data_models import CaseDetails
    from TIPCommon.types import SingleJson


class SimpleJobExample(Job):
    def __init__(self) -> None:
        super().__init__(constants.JOB_SCRIPT_NAME)
        self.context: dict[str, str] = {}
        self.current_date: str = self._get_today_date()

    def _init_api_clients(self) -> SampleApiClient:
        auth_params = build_auth_params(self.soar_job)
        authenticator: AuthenticatedSession = AuthenticatedSession()
        auth_params_for_session = SessionAuthenticationParameters(
            api_root=auth_params.api_root,
            password=auth_params.password,
            verify_ssl=auth_params.verify_ssl,
        )
        authenticator.authenticate_session(auth_params_for_session)
        authenticated_session: requests.Session = authenticator.session

        api_params: ApiParameters = ApiParameters(
            api_root=auth_params.api_root,
        )

        return SampleApiClient(
            authenticated_session=authenticated_session,
            configuration=api_params,
            logger=self.logger,
        )

    def _perform_job(self) -> None:
        self._load_context()
        updated_case_ids: list[int] = []
        cases: list[CaseDetails] = self._get_cases_with_details()

        for case in cases:
            tags = self._get_case_tags(case)
            if self._should_close_case(tags):
                self._close_case(case)
                if case.id_ in self.context[constants.CASES_WITH_COMMENT_KEY]:
                    self.context[constants.CASES_WITH_COMMENT_KEY].remove(case.id_)

            if self._should_comment_on_case(tags, case.id_):
                self._add_currency_comment_to_case(case)
                updated_case_ids.append(case.id_)

        self._update_context_with_commented_cases(updated_case_ids)
        self._save_context()

    def _load_context(self) -> None:
        self.logger.info("Loading context...")
        context_str: str = self.soar_job.get_job_context_property(
            self.name_id,
            constants.SIMPLE_JOB_CONTEXT_KEY,
        )
        if not context_str:
            self.logger.info("No context found. Initializing...")
            self.context = {
                constants.DATE_KEY: self.current_date,
                constants.CASES_WITH_COMMENT_KEY: [],
            }
            return

        self.context = json.loads(context_str)
        if self.context.get(constants.DATE_KEY) != self.current_date:
            self.logger.info("New date detected. Resetting context.")
            self.context: SingleJson = {
                constants.DATE_KEY: self.current_date,
                constants.CASES_WITH_COMMENT_KEY: [],
            }

    def _get_cases_with_details(self) -> list[CaseDetails]:
        return [
            get_case_overview_details(self.soar_job, case_id) for case_id in self._get_case_ids()
        ]

    def _get_case_ids(self) -> list[int]:
        case_ids: list[int] = self.soar_job.get_cases_ids_by_filter(
            status=CaseFilterStatusEnum.OPEN,
            operator=CaseFilterOperatorEnum.OR,
            sort_by=CaseFilterSortByEnum.UPDATE_TIME,
            sort_order=CaseFilterSortOrderEnum.ASC,
            max_results=constants.PROCESSED_CASES_LIMIT,
            tags=[constants.CLOSED_CASE_TAG, constants.CURRENCY_TAG],
        )
        self.logger.info(f"Fetched {len(case_ids)} cases from SOAR to process.")

        return case_ids

    def _get_case_tags(self, case: CaseDetails) -> list[str]:
        return [
            tag.get("displayName").lower() if "displayName" in tag else tag.lower()
            for tag in case.tags
        ]

    def _should_close_case(self, tags: list[str]) -> bool:
        return constants.CLOSED_CASE_TAG.lower() in tags

    def _close_case(self, case: CaseDetails) -> None:
        self.soar_job.close_case(
            root_cause=constants.ROOT_CAUSE,
            case_id=case.id_,
            reason=constants.CLOSE_CASE_REASON,
            comment=constants.CLOSE_CASE_COMMENT,
            alert_identifier=None,
        )
        self.logger.info(f"Closed case: {case.id_}")

    def _should_comment_on_case(self, tags: list[str], case_id: int) -> bool:
        return (
            constants.CLOSED_CASE_TAG.lower() not in tags
            and constants.CURRENCY_TAG.lower() in tags
            and case_id not in self.context[constants.CASES_WITH_COMMENT_KEY]
        )

    def _add_currency_comment_to_case(self, case: CaseDetails) -> None:
        exchange_data: SingleJson = self.api_client.get_job_rate()
        rate: str = exchange_data.get("rates", {}).get("EUR")
        comment: str = (
            f"{constants.COMMENT_PREFIX} {constants.CURRENCY_PAIR} {rate}. Date: "
            f"{exchange_data[constants.DATE_KEY]}"
        )

        self.soar_job.add_comment(
            comment=comment,
            case_id=case.id_,
            alert_identifier=None,
        )
        self.logger.info(f"Commented on case: {case.id_}")

    def _update_context_with_commented_cases(self, case_ids: list[int]) -> None:
        self.context[constants.CASES_WITH_COMMENT_KEY].extend(case_ids)

    def _save_context(self) -> None:
        self.logger.info("Saving context...")
        self.soar_job.set_job_context_property(
            identifier=self.name_id,
            property_key=constants.SIMPLE_JOB_CONTEXT_KEY,
            property_value=json.dumps(self.context),
        )

    def _get_today_date(self) -> str:
        return datetime.utcnow().strftime("%Y-%m-%d")


def main() -> NoReturn:
    SimpleJobExample().start()


if __name__ == "__main__":
    main()
