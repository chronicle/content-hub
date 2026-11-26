# Copyright 2026 RansomLeak
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

from typing import TYPE_CHECKING, NoReturn

from TIPCommon.base.action import DataTable
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv

from ..core.base_action import BaseAction
from ..core.constants import (
    GET_TRAINING_STATUS_ACTION_NAME,
    GET_TRAINING_STATUS_SCRIPT_NAME,
    SUMMARY_FIELDS,
    UUID_PATTERN,
)
from ..core.exceptions import RansomLeakNotFoundError, RansomLeakValidationError
from ..core.utils import (
    collect_emails,
    lookup_user_summary,
    map_concurrently,
    section,
    unique_values,
)

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class GetTrainingStatusAction(BaseAction):
    """Report training progress for users and/or remediation assignments."""

    def __init__(self) -> None:
        super().__init__(GET_TRAINING_STATUS_SCRIPT_NAME, GET_TRAINING_STATUS_ACTION_NAME)

    def _extract_action_parameters(self) -> None:
        emails_csv: str | None = extract_action_param(
            self.soar_action,
            param_name="Email Addresses",
            print_value=True,
        )
        assignment_ids_csv: str | None = extract_action_param(
            self.soar_action,
            param_name="Assignment IDs",
            print_value=True,
        )
        self.params.emails_csv = emails_csv
        self.params.assignment_ids_csv = assignment_ids_csv

    def _validate_params(self) -> None:
        emails, skipped = collect_emails(self.soar_action, self.params.emails_csv)
        assignment_ids = unique_values(self.params.assignment_ids_csv)
        if not emails and not assignment_ids:
            msg = "Provide User entities with email identifiers, 'Email Addresses' or 'Assignment IDs'."
            raise RansomLeakValidationError(msg)
        self.params.emails = emails
        self.params.skipped = skipped
        self.params.assignment_ids = assignment_ids

    def _get_users(self, not_found: list[str]) -> list[SingleJson]:
        users: list[SingleJson] = []
        lookups = map_concurrently(
            lambda email: lookup_user_summary(self.api_client, email),
            self.params.emails,
        )
        for email, summary, error in lookups:
            if error is not None:
                raise error
            if summary is None:
                not_found.append(email)
            else:
                users.append(summary)
        return users

    def _get_assignments(self, not_found: list[str]) -> list[SingleJson]:
        assignment_ids: list[str] = self.params.assignment_ids
        valid_ids = [a for a in assignment_ids if UUID_PATTERN.match(a)]
        not_found += [a for a in assignment_ids if not UUID_PATTERN.match(a)]
        assignments: list[SingleJson] = []
        for assignment_id, assignment, error in map_concurrently(self.api_client.get_assignment, valid_ids):
            if isinstance(error, RansomLeakNotFoundError):
                not_found.append(assignment_id)
            elif error is not None:
                raise error
            elif assignment is not None:
                assignments.append(assignment)
        return assignments

    def _add_data_tables(self, users: list[SingleJson], assignments: list[SingleJson]) -> None:
        if users:
            self.data_tables.append(
                DataTable(
                    data_table=construct_csv([
                        {"Email": u["email"], **{label: u[key] for key, label in SUMMARY_FIELDS}} for u in users
                    ]),
                    title="RansomLeak Training Status",
                ),
            )
        if assignments:
            self.data_tables.append(
                DataTable(
                    data_table=construct_csv([
                        {
                            "Assignment ID": a.get("assignmentId"),
                            "Email": a.get("userEmail"),
                            "Exercise": a.get("exerciseSlug"),
                            "Status": a.get("status"),
                            "Started At": a.get("startedAt"),
                            "Completed At": a.get("completedAt"),
                        }
                        for a in assignments
                    ]),
                    title="RansomLeak Assignments",
                ),
            )

    def _perform_action(self, _: object = None) -> None:
        # Fail fast on a bad key instead of fanning out N failing lookups.
        self.api_client.test_connectivity()
        not_found: list[str] = []
        users = self._get_users(not_found)
        assignments = self._get_assignments(not_found)
        skipped: list[str] = self.params.skipped

        self.json_results = {
            "users": users,
            "assignments": assignments,
            "not_found": not_found,
            "skipped_identifiers": skipped,
        }
        self._add_data_tables(users, assignments)

        found = [u["email"] for u in users] + [a.get("assignmentId") for a in assignments]
        if found:
            self.output_message = "Successfully retrieved RansomLeak training status for:\n" + "\n".join(found)
        else:
            self.output_message = "No training status was found in RansomLeak."
        self.output_message += section(
            "The following users or assignments were not found in RansomLeak",
            not_found,
        )
        self.output_message += section(
            "The following values were skipped because they are not email addresses",
            skipped,
        )
        self.result_value = bool(found)


def main() -> NoReturn:
    GetTrainingStatusAction().run()


if __name__ == "__main__":
    main()
