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

import re
from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv, string_to_multi_value

from ..core.constants import GET_TRAINING_STATUS_SCRIPT_NAME, SUMMARY_FIELDS
from ..core.exceptions import RansomLeakNotFoundError, RansomLeakValidationError
from ..core.utils import build_manager, collect_emails, lookup_user_summary, map_concurrently, section

ACTION_NAME = "Get Training Status"
UUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


@output_handler
def main() -> None:
    """Report training progress for users and/or remediation assignments."""
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_TRAINING_STATUS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    emails_csv = extract_action_param(siemplify, param_name="Email Addresses", print_value=True)
    assignment_ids_csv = extract_action_param(siemplify, param_name="Assignment IDs", print_value=True)
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED
    try:
        emails, skipped = collect_emails(siemplify, emails_csv)
        assignment_ids = string_to_multi_value(assignment_ids_csv, only_unique=True)
        if not emails and not assignment_ids:
            msg = "Provide User entities with email identifiers, 'Email Addresses' or 'Assignment IDs'."
            raise RansomLeakValidationError(msg)

        manager = build_manager(siemplify)
        users: list[dict[str, Any]] = []
        not_found: list[str] = []
        for email, summary, error in map_concurrently(lambda e: lookup_user_summary(manager, e), emails):
            if error is not None:
                raise error
            if summary is None:
                not_found.append(email)
            else:
                users.append(summary)

        assignments: list[dict[str, Any]] = []
        for assignment_id in assignment_ids:
            if not UUID_PATTERN.match(assignment_id):
                not_found.append(assignment_id)
                continue
            try:
                assignments.append(manager.get_assignment(assignment_id))
            except RansomLeakNotFoundError:
                not_found.append(assignment_id)

        siemplify.result.add_result_json({
            "users": users,
            "assignments": assignments,
            "not_found": not_found,
            "skipped_identifiers": skipped,
        })
        if users:
            siemplify.result.add_data_table(
                "RansomLeak Training Status",
                construct_csv([
                    {"Email": u["email"], **{label: u[key] for key, label in SUMMARY_FIELDS}} for u in users
                ]),
            )
        if assignments:
            siemplify.result.add_data_table(
                "RansomLeak Assignments",
                construct_csv([
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
            )

        found = [u["email"] for u in users] + [a.get("assignmentId") for a in assignments]
        if found:
            output_message = "Successfully retrieved RansomLeak training status for:\n" + "\n".join(found)
        else:
            output_message = "No training status was found in RansomLeak."
        output_message += section("The following users or assignments were not found in RansomLeak", not_found)
        output_message += section("The following values were skipped because they are not email addresses", skipped)
        result_value = bool(found)
    except Exception as error:
        siemplify.LOGGER.error(f'Error executing action "{ACTION_NAME}". Reason: {error}')
        siemplify.LOGGER.exception(error)
        output_message = f'Error executing action "{ACTION_NAME}". Reason: {error}'
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
