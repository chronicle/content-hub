# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from dataclasses import dataclass
from typing import Union, Dict, List, Any

from TIPCommon.smp_time import is_approaching_timeout

from crowd_strike_falcon.core.constants import SUCCESS_STATE, ERROR_STATE, DEFAULT_TIMEOUT, FILE_TYPE_BAD_ERROR
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core.exceptions import CrowdStrikeError, CrowdStrikeTimeoutError
from crowd_strike_falcon.core.utils import is_async_action_global_timeout_approaching


DEVICE_HOSTNAME_KEY = "hostname"
DEVICE_IP_KEY = "local_ip"


class CrowdStrikeCommon:
    @staticmethod
    def host_entity_output_message_pattern(entity_identifier, device_obj):
        """
        Form entity name for output message.
        :param entity_identifier: {string} Entity Identifier.
        :param device_obj: {datamodels.Device} The device obj representing the device
        :return: {string} Entity name.
        """
        return f"{entity_identifier}[{device_obj.local_ip}]"

    @staticmethod
    def address_entity_output_message_pattern(entity_identifier, device_obj):
        """
        Form entity name for output message.
        :param entity_identifier: {string} Entity Identifier.
        :param device_obj: {datamodels.Device} The device obj representing the device
        :return: {string} Entity name.
        """
        return f"{entity_identifier}[{device_obj.hostname}]"

    @staticmethod
    def convert_comma_separated_to_list(comma_separated):
        # type: (unicode or str) -> list
        """
        Convert comma-separated string to list
        @param comma_separated: String with comma-separated values
        @return: List of values
        """
        return (
            [item.strip() for item in comma_separated.split(",")]
            if comma_separated
            else []
        )

    @staticmethod
    def convert_list_to_comma_string(values_list):
        # type: (list) -> str or unicode
        """
        Convert list to comma-separated string
        @param values_list: String with comma-separated values
        @return: List of values
        """
        return (
            ", ".join(values_list)
            if values_list and isinstance(values_list, list)
            else values_list
        )


@dataclass
class ActionResult:
    output_message: str
    result_value: Union[bool, str]
    json_result: Dict[str, Any] = None
    table_results: Union[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]] = None


class SubmitActionBase:
    def __init__(
        self,
        siemplify,
        start_time: int,
        manager: CrowdStrikeManager,
        check_duplicate: bool,
        sandbox_environment: str,
        network_environment: str,
        action_context,
    ):
        self.siemplify = siemplify
        self.start_time = start_time
        self.manager = manager
        self.action_context = action_context

        self.check_duplicate = check_duplicate
        self.sandbox_environment = sandbox_environment
        self.network_environment = network_environment

    def is_all_processed(self):
        return all(
            not (submission_data["pending_submissions"])
            for submission_data in self.action_context["submissions"].values()
        )

    def query_status(self):
        pending_submissions_data = {
            entity_name: submission_data
            for entity_name, submission_data in self.action_context[
                "submissions"
            ].items()
            if submission_data.get("pending_submissions", [])
        }

        self.check_timeout()

        if not pending_submissions_data:
            return True

        submissions_map = {}

        for entity_name, submission_data in pending_submissions_data.items():
            submissions_map.update(
                {
                    submission_id: entity_name
                    for submission_id in submission_data["pending_submissions"]
                }
            )

        submissions_data = self.manager.get_submissions(list(submissions_map.keys()))

        finished_submissions = []
        failed_submissions = []

        # Process submissions data
        for submission in submissions_data:
            self.siemplify.LOGGER.info(
                f"Submissions state for {submissions_map[submission.id]} - {submission.state}"
            )
            if submission.state == SUCCESS_STATE:
                finished_submissions.append(submission)
            elif submission.state == ERROR_STATE:
                failed_submissions.append(submission)

        self.check_timeout()

        # Handle finished submissions
        self.siemplify.LOGGER.info(
            "Getting submission reports for finished submissions ..."
        )
        submissions_reports = self.manager.get_submission_reports(
            [submission.id for submission in finished_submissions]
        )
        for submission_report in submissions_reports:
            entity_name = submissions_map[submission_report.id]
            self.siemplify.LOGGER.info(
                f"Submission {submission_report.id} for {entity_name} is fully processed."
            )
            self.action_context["submissions"][entity_name][
                "pending_submissions"
            ].remove(submission_report.id)

            if (
                submission_report.raw_data["sandbox"][0].get("error_type")
                == FILE_TYPE_BAD_ERROR
            ):
                self.siemplify.LOGGER.error(
                    f"Failed to analyse file {entity_name}, file format is unsupported"
                )
                unsupported_submissions = self.action_context["submissions"][
                    entity_name
                ].get("unsupported_submissions", [])
                unsupported_submissions.append(submission_report.get_entity_name())
                self.action_context["submissions"][entity_name][
                    "unsupported_submissions"
                ] = unsupported_submissions

            else:
                reports = self.action_context["submissions"][entity_name].get(
                    "finished_submissions", []
                )
                reports.append(submission_report.to_json())
                self.action_context["submissions"][entity_name][
                    "finished_submissions"
                ] = reports

        # Handle failed submissions
        for submission_data in failed_submissions:
            entity_name = submissions_map[submission_data.id]
            self.siemplify.LOGGER.info(
                f"Submission for {submission_data.id} have failed."
            )
            self.action_context["submissions"][entity_name][
                "pending_submissions"
            ].remove(submission_data.id)

            failed_submissions = self.action_context["submissions"][entity_name].get(
                "failed_submissions", []
            )
            failed_submissions.append(submission_data.get_entity_name())
            self.action_context["submissions"][entity_name][
                "failed_submissions"
            ] = failed_submissions

        # Return is the process finished for all pending submissions
        return self.is_all_processed()

    def submit_entities(self, submissions_payloads):
        for entity_name, submission_payloads in submissions_payloads.items():
            self.check_timeout()

            submission_data = self.action_context["submissions"].get(
                entity_name, {"pending_submissions": [], "failed_submissions": []}
            )

            for submission_payload in submission_payloads:
                try:
                    submission_id = self.manager.submit_for_analysis(submission_payload)
                    submission_data["pending_submissions"].append(submission_id)
                except CrowdStrikeError as e:
                    self.siemplify.LOGGER.error(
                        f"Failed to submit {entity_name}, error is: {e}"
                    )
                    submission_data["failed_submissions"].append(
                        submission_payload["submit_name"]
                    )

            self.action_context["submissions"][entity_name] = submission_data

    def start_operation(self, entity_names):
        self.siemplify.LOGGER.info("Preparing payloads for submissions ...")
        self.check_timeout()

        submissions_payloads = self.prepare_submission_payloads(entity_names)

        if self.check_duplicate:
            self.siemplify.LOGGER.info("Checking for duplicates ...")
            submissions_payloads = self.remove_duplicates(submissions_payloads)

        self.siemplify.LOGGER.info("Submitting entities to Crowdstrike Sandbox ...")
        self.check_timeout()
        self.submit_entities(submissions_payloads=submissions_payloads)

        self.siemplify.LOGGER.info(f"Action context - {self.action_context}")

        # Return is the process finished for all pending submissions
        return self.is_all_processed()

    def check_timeout(self):
        timed_out = is_approaching_timeout(
            self.start_time, DEFAULT_TIMEOUT
        ) or is_async_action_global_timeout_approaching(self.siemplify, self.start_time)
        if timed_out:
            error_message = self.get_timeout_error_message()
            raise CrowdStrikeTimeoutError(error_message)

    def remove_duplicates(self, submission_payloads):
        raise NotImplementedError

    def prepare_submission_payloads(self, entity_names):
        raise NotImplementedError

    def generate_result(self):
        raise NotImplementedError

    def get_timeout_error_message(self):
        raise NotImplementedError
