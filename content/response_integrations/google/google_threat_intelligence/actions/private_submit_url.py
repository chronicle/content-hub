from __future__ import annotations

import json
import logging
from enum import StrEnum
from itertools import chain, groupby
from typing import Any, MutableMapping

from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    create_entity_json_result_object,
    unix_now,
)
from TIPCommon import validation
from TIPCommon.base.action import ExecutionState, Link
from TIPCommon.extraction import extract_action_param
from TIPCommon.smp_time import is_approaching_action_timeout
from google_threat_intelligence.core.api_manager import ApiManager
from google_threat_intelligence.core.base_action import BaseAction
from google_threat_intelligence.core.constants import PRIVATE_SUBMIT_URL_SCRIPT_NAME, SUSPICIOUS_VERDICTS
from google_threat_intelligence.core.data_models import URL
from google_threat_intelligence.core.exceptions import (
    EntityNotFoundOrEmptyResults,
    GoogleThreatIntelligenceNotFoundException,
)
from google_threat_intelligence.core.utils import convert_days_to_milliseconds, encode_url


SHOW_ENTITY_STATUS = True

SUPPORTED_ENTITY_TYPES = [EntityTypes.URL]

TIMEOUT_ERROR_MESSAGE = (
    "Error executing action “Private Submit URL”. \n"
    "Reason: action ran into a timeout during execution. \n"
    "Pending urls: \n{}\n"
    "Please increase the timeout in IDE.\n"
)

SUCCESS_MESSAGE = (
    "Successfully returned information about the following "
    "URLs in Google Threat Intelligence: \n{}\n"
)

NOTHING_PROCESSED_MESSAGE = (
    "None of the provided URLs were processed in Google Threat Intelligence.\n"
)

FAILED_SUBMISSIONS_MESSAGE = (
    "Action couldn’t find information about the following "
    "URLs in Google Threat Intelligence: \n{}\n"
)


class SubmissionState(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    SUBMITTED = "SUBMITTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SubmissionType(StrEnum):
    PRIVATE = "PRIVATE"
    PUBLIC = "PUBLIC"


class Submission:
    """A helper class to handle the state of a single URL submission."""

    def __init__(
        self, url: str, api_client: ApiManager = None, logger: logging.Logger = None
    ):
        """Initializes a Submission.

        Args:
            url: The URL to be submitted.
            api_client: Reference to the GTI API client.
            logger: The logger object.
        """
        self.identifier = encode_url(url)
        self.url = url
        self.analysis_id = None
        self.state = SubmissionState.NOT_STARTED
        self._api_client = api_client
        self._logger = logger
        self._last_result = None
        self._last_result_submission_type = None

    def fetch_report(self, submission_type: SubmissionType) -> None:
        """Fetches a report for the current URL.

        The report can be fetched from either a private or public submission.

        Args:
            submission_type: The type of submission (PRIVATE or PUBLIC).
        """
        self._logger.info(f"{self.url}: Fetching report type: {submission_type.name}")
        try:
            self._last_result = self._api_client.get_ioc_details(
                ioc=self.identifier,
                ioc_type="urls",
                is_private_submission=submission_type == SubmissionType.PRIVATE,
                show_entity_status=SHOW_ENTITY_STATUS,
                raw_response=True,
            )
            self._last_result_submission_type = submission_type
            self.state = SubmissionState.COMPLETED
        except GoogleThreatIntelligenceNotFoundException as e:
            logging.info(f"Report for {self.url} not found.")
            logging.debug(f"Reason: {e}")
        except Exception as e:
            self._fail_with_message("Failed to fetch report", e)

    def is_outdated(self, resubmit_days: int) -> bool:
        """Checks if a public submission is outdated.

        Args:
            resubmit_days: The number of days after which a submission is
                considered outdated.

        Returns:
            True if the submission is a public submission and is older than
            `resubmit_days`. False otherwise.
        """
        # Nothing has been fetched so far
        if self._last_result is None:
            return False
        # Private submission does not require resubmitting
        if self._last_result_submission_type is SubmissionType.PRIVATE:
            return False

        return (
            unix_now() - convert_days_to_milliseconds(resubmit_days)
            > self._last_analysis_date() * 1000
        )

    def submit(self) -> None:
        """Submits the URL for private analysis."""
        self._logger.info(f"{self.url}: Submitting for analysis")
        if self.state == SubmissionState.NOT_STARTED:
            self._submit()

    def resubmit(self) -> None:
        """Re-submits the URL for private analysis."""
        self._logger.info(f"{self.url}: Resubmitting outdated report for analysis")
        if self.state == SubmissionState.COMPLETED:
            self._submit()

    def _submit(self) -> None:
        try:
            self.analysis_id = self._api_client.submit_url_for_analysis(
                url=self.url,
                show_entity_status=SHOW_ENTITY_STATUS,
                private_submission=True,
            )
            if self.analysis_id:
                self.state = SubmissionState.SUBMITTED
            else:
                raise EntityNotFoundOrEmptyResults("External api returned no result")
        except Exception as e:
            self._fail_with_message("Failed to submit", e)

    def _last_analysis_date(self) -> int:
        return self.as_model_object().last_analysis_date

    def is_analysis_done(self) -> bool:
        """Checks the remote status of the analysis in GTI.

        Returns:
            True if the analysis is complete, False otherwise.
        """
        self._logger.info(f"{self.url}: Analysis done")

        result = False
        try:
            result = self._api_client.check_analysis_status(
                self.analysis_id,
                show_entity_status=SHOW_ENTITY_STATUS,
                is_private_submission=True,
            )
        except Exception as e:
            self._fail_with_message("Failed to check state", e)
        return result

    def get_result(self) -> MutableMapping[str, Any]:
        """Gets the raw JSON result for the submission.

        Returns:
            A dictionary containing the enveloped raw JSON data.
        """
        return create_entity_json_result_object(self.url, self._last_result)

    def _fail_with_message(self, message: str, e: Exception) -> None:
        self._logger.error(f"{message}: {self.url}")
        self._logger.debug(f"Reason: {e}")
        self.state = SubmissionState.FAILED

    def is_finished(self) -> bool:
        """Checks if the submission has finished processing.

        Returns:
            True if the submission is in a COMPLETED or FAILED state.
        """
        result = self.state in (SubmissionState.COMPLETED, SubmissionState.FAILED)
        self._logger.info(f"{self.url}: {self.state} -> is_finished: {result}")
        return result

    def as_dict(self) -> dict:
        """Returns a dictionary representation of the submission.

        This is used for restoring the submission's state.

        Returns:
            A dictionary containing the submission's state.
        """
        return {
            "identifier": self.identifier,
            "state": SubmissionState(self.state),
            "_last_result": self._last_result,
            "_last_result_submission_type": self._last_result_submission_type,
            "analysis_id": self.analysis_id,
            "url": self.url,
        }

    def as_model_object(self) -> URL:
        """Converts the submission result to a GTI URL model.

        Returns:
            A URL data model object.
        """
        return URL.from_json(
            self._last_result.get("data"), ioc_type="url", ioc=self.identifier
        )

    def restore_state(self, previous_state: dict) -> None:
        """Restores the submission's state from a dictionary.

        Args:
            previous_state: A dictionary containing the previous state of the
                submission.
        """
        self._logger.info(f"Restoring state: {self.url}")
        self.state = SubmissionState(previous_state.get("state"))
        self.identifier = previous_state.get("identifier")
        self._last_result = previous_state.get("_last_result")
        last_result_submission_type = previous_state.get("_last_result_submission_type")
        if last_result_submission_type:
            self._last_result_submission_type = SubmissionType(
                last_result_submission_type
            )
        self.analysis_id = previous_state.get("analysis_id")

    def get_case_wall_link(self) -> Link:
        """Gets a case wall link for the finished submission.

        Returns:
            A Link object for the submission's report.
        """
        gui_url = self.as_model_object().report_link
        return Link(gui_url, self.url)


def _url(submission: Submission) -> str:
    """A helper function to extract the URL from a submission.

    Args:
        submission: A Submission object.

    Returns:
        The URL from the submission.
    """
    return submission.url


class PrivateSubmitUrl(BaseAction):
    """An action to submit a URL for private analysis in Google Threat Intelligence."""

    def __init__(self, script_name: str):
        """Initializes a PrivateSubmitUrl action.

        Args:
            script_name: The name of the script.
        """
        super().__init__(script_name)
        self.output_message: str = ""
        self._result_value = True
        self.error_output_message: str = f'Error executing action "{script_name}".'
        self._submissions = {}
        self.target_entities = []

    def _extract_action_parameters(self) -> None:
        """Extracts action parameters from the SOAR action."""
        self.logger.info("Extracting action parameters")
        self.params.urls = extract_action_param(
            self.soar_action,
            param_name="URL",
            print_value=True,
        )

        self.params.check_existing_submission_first = extract_action_param(
            self.soar_action,
            input_type=bool,
            param_name="Check Existing Submissions First",
            print_value=True,
        )

        self.params.resubmit_after = extract_action_param(
            self.soar_action,
            input_type=int,
            param_name="Resubmit After (Days)",
            print_value=True,
        )

        self.params.additional_data = json.loads(
            extract_action_param(
                siemplify=self.soar_action,
                param_name="additional_data",
                default_value="{}",
            ),
        )

    def _validate_params(self) -> None:
        """Validates the action parameters."""
        self.logger.info("Validating action parameters")
        validator = validation.ParameterValidator(self.soar_action)

        self.params.resubmit_after = validator.validate_non_negative(
            param_name="Resubmit After (Days)",
            value=self.params.resubmit_after,
            print_value=False,
        )

        self.params.urls = validator.validate_csv(
            param_name="URL",
            csv_string=self.params.urls,
            print_value=False,
        )
        self.target_entities = [
            entity
            for entity in self._soar_action.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        ]

        urls = []
        urls.extend(self.params.urls)
        urls.extend(self.target_entities)
        for url in map(str, urls):
            self._submissions[url] = Submission(
                url, logger=self._logger, api_client=self.api_client
            )

    def _is_approaching_async_timeout(self) -> bool:
        """Determines whether the action is approaching its asynchronous timeout."""
        return is_approaching_action_timeout(
            self.soar_action.async_total_duration_deadline,
        )

    def _perform_action(self, _) -> None:
        """Performs the action's logic."""
        self.logger.info("Perform action")
        self.api_client.test_connectivity()
        self.execution_state = ExecutionState.IN_PROGRESS
        actions_previous_state = self.params.additional_data

        for url, submission in self._submissions.items():
            self.logger.info(f"Url: {submission.url}")
            # Try to restore previous state if present
            if (
                isinstance(actions_previous_state, dict)
                and url in actions_previous_state
            ):
                submission.restore_state(actions_previous_state.get(url))
            if self.is_first_run:
                self._handle_first_run(submission)
            elif (
                submission.state == SubmissionState.SUBMITTED
                and submission.is_analysis_done()
            ):
                submission.fetch_report(SubmissionType.PRIVATE)
            if submission.is_outdated(self.params.resubmit_after):
                submission.resubmit()

        if self._is_approaching_async_timeout():
            self.logger.info(
                "Action is approaching async timeout, and will exit gracefully"
            )
            self._handle_timeout()
        elif self._all_complete():
            self.logger.info("All done")
            self._handle_all_complete()
        else:
            self.logger.info("Setting context for next iteration")
            self._save_current_action_state()

    def _handle_first_run(self, submission: Submission) -> None:
        """Handles the logic for the first run of the action.

        Args:
            submission: The submission to process.
        """
        if self.params.check_existing_submission_first:
            # First try to fetch from public reports
            submission.fetch_report(SubmissionType.PUBLIC)
            if not submission.state == SubmissionState.COMPLETED:
                submission.fetch_report(SubmissionType.PRIVATE)
        if not submission.is_finished():
            submission.submit()

    def _handle_all_complete(self) -> None:
        """Handles the case where all submissions are complete."""
        self.execution_state = ExecutionState.COMPLETED
        grouped_submissions = self._split_submissions_on_state()
        self._finalize_successful_submissions(grouped_submissions)
        self._finalize_failed_submissions(grouped_submissions)

    def _save_current_action_state(self) -> None:
        """Saves the current state of all submissions."""
        self._result_value = json.dumps(
            {url: submission.as_dict() for url, submission in self._submissions.items()}
        )

    def _handle_timeout(self) -> None:
        """Handles the case where the action is approaching its timeout."""
        grouped_submissions = self._split_submissions_on_state()
        if SubmissionState.COMPLETED in grouped_submissions:
            grouped_submissions.pop(SubmissionState.COMPLETED)
        unfinished_submissions = chain(*grouped_submissions.values())
        self._handle_all_complete()
        if unfinished_submissions:
            self._result_value = False
            urls = map(_url, unfinished_submissions)
            self._output_message += TIMEOUT_ERROR_MESSAGE.format("\n".join(urls))

    def _split_submissions_on_state(self) -> dict[SubmissionState, list[Submission]]:
        """Splits submissions into groups based on their state.

        Returns:
            A dictionary where keys are submission states and values are lists
            of submissions in that state.
        """
        sorted_submissions = sorted(
            self._submissions.values(), key=lambda submission: submission.state
        )
        return {
            k: list(v)
            for k, v in groupby(
                sorted_submissions,
                lambda submission: submission.state,
            )
        }

    def _finalize_successful_submissions(
        self, grouped_submissions: dict[SubmissionState, list[Submission]]
    ) -> None:
        """Finalizes the successfully completed submissions.

        Args:
            grouped_submissions: A dictionary of submissions grouped by state.
        """
        successful_submissions = grouped_submissions.get(SubmissionState.COMPLETED)
        if successful_submissions:
            self._result_value = True

            case_wall_links = map(
                lambda submission: submission.get_case_wall_link(),
                successful_submissions,
            )
            self.links.extend(case_wall_links)

            urls = map(_url, successful_submissions)
            self.output_message += SUCCESS_MESSAGE.format("\n".join(urls))

            self.json_results = [
                submission.get_result() for submission in successful_submissions
            ]

            for entity in self.target_entities:
                url = str(entity)
                submission = self._submissions.get(url)
                if submission:
                    self.logger.info(f"Updating enrichment for {submission.url}")
                    submission_model_object = submission.as_model_object()
                    enrichment_data = submission_model_object.to_enrichment_data()
                    self.logger.info(f"Enrichment data: {enrichment_data}")
                    entity.additional_properties.update(enrichment_data)
                    entity.is_enriched = True
                    if submission_model_object.verdict in SUSPICIOUS_VERDICTS:
                        entity.is_suspicious = True
            self.soar_action.update_entities(self.target_entities)

        else:
            self.output_message = NOTHING_PROCESSED_MESSAGE
            self._result_value = False

    def _finalize_failed_submissions(
        self, grouped_submissions: dict[SubmissionState, list[Submission]]
    ) -> None:
        """Finalizes the failed submissions.

        Args:
            grouped_submissions: A dictionary of submissions grouped by state.
        """
        failed_submissions = grouped_submissions.get(SubmissionState.FAILED)
        if failed_submissions:
            urls = map(_url, failed_submissions)
            self.output_message += FAILED_SUBMISSIONS_MESSAGE.format("\n".join(urls))

    def _all_complete(self) -> bool:
        """Checks if all submissions are in a finished state.

        Returns:
            True if all submissions are complete, False otherwise.
        """
        return all(
            map(lambda submission: submission.is_finished(), self._submissions.values())
        )


def main() -> None:
    """The main entry point for the script."""
    PrivateSubmitUrl(PRIVATE_SUBMIT_URL_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
