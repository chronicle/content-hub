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

from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param

from ..core.constants import ASSIGN_TRAINING_SCRIPT_NAME, MAX_ENROLLMENT_BATCH
from ..core.exceptions import RansomLeakNotFoundError, RansomLeakValidationError
from ..core.ransomleak_manager import RansomLeakManager
from ..core.utils import build_manager, collect_emails

ACTION_NAME = "Assign Training"
# "submitted" is only reported by RansomLeak versions without per-user enrollment results.
ENROLLED_STATUSES = ("enrolled", "already_enrolled", "submitted")


def _enroll_learning_path(
    siemplify: SiemplifyAction,
    manager: RansomLeakManager,
    learning_path_ref: str,
    emails: list[str],
    due_days: int | None,
) -> dict[str, Any]:
    learning_path = manager.find_learning_path(learning_path_ref)
    if learning_path is None:
        msg = f"Learning path '{learning_path_ref}' was not found. Use 'List Learning Paths' to find a valid ID."
        raise RansomLeakNotFoundError(msg)

    by_email: dict[str, dict[str, Any]] = {
        email: {"email": email, "user_id": None, "enrollment_id": None, "status": "pending"} for email in emails
    }
    totals = {"assigned": 0, "already_enrolled": 0, "skipped_unlicensed": 0}
    for start in range(0, len(emails), MAX_ENROLLMENT_BATCH):
        batch = emails[start : start + MAX_ENROLLMENT_BATCH]
        siemplify.LOGGER.info(f"Enrolling {len(batch)} user(s) in learning path {learning_path['id']}")
        response = manager.enroll_learning_path(learning_path["id"], emails=batch, due_days=due_days)
        totals["assigned"] += response.get("assigned", 0)
        totals["already_enrolled"] += response.get("alreadyEnrolled", 0)
        totals["skipped_unlicensed"] += response.get("skippedUnlicensed", 0)
        for result in response.get("results") or []:
            entry = by_email.get((result.get("email") or "").lower())
            if entry is None:
                continue
            entry.update({
                "user_id": result.get("userId"),
                "enrollment_id": result.get("enrollmentId"),
                "status": result.get("status") or "submitted",
            })
        not_found = {(x or "").lower() for x in response.get("notFound") or []}
        for email in batch:
            if by_email[email]["status"] == "pending":
                by_email[email]["status"] = "not_found" if email in not_found else "submitted"
    users = list(by_email.values())

    return {
        "training_type": "learning_path",
        "learning_path": {"id": learning_path.get("id"), "name": learning_path.get("name")},
        "due_in_days": due_days,
        "enrollment": totals,
        "users": users,
    }


def _assign_exercise(
    siemplify: SiemplifyAction,
    manager: RansomLeakManager,
    exercise_slug: str,
    emails: list[str],
) -> dict[str, Any]:
    case_id = str(getattr(siemplify, "case_id", "") or "")
    users: list[dict[str, Any]] = []
    for email in emails:
        entry: dict[str, Any] = {"email": email, "assignment_id": None, "status": "not_found"}
        users.append(entry)
        # Stable per case + exercise + user, so playbook re-runs return the same assignment.
        idempotency_key = f"secops:{case_id or 'manual'}:{exercise_slug}:{email.lower()}"
        try:
            assignment = manager.create_assignment(
                exercise_slug=exercise_slug,
                email=email,
                idempotency_key=idempotency_key[:255],
                reference=case_id or None,
            )
        except RansomLeakNotFoundError as error:
            siemplify.LOGGER.info(f"Assignment for {email} not created: {error}")
            entry["error"] = str(error)
            continue
        entry.update({
            "assignment_id": assignment.get("assignmentId"),
            "status": assignment.get("status"),
            "created_at": assignment.get("createdAt"),
        })
    return {"training_type": "exercise", "exercise_slug": exercise_slug, "users": users}


@output_handler
def main() -> None:
    """Assign a learning path or a single exercise to users."""
    siemplify = SiemplifyAction()
    siemplify.script_name = ASSIGN_TRAINING_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    learning_path_ref = extract_action_param(siemplify, param_name="Learning Path", print_value=True) or ""
    exercise_slug = extract_action_param(siemplify, param_name="Exercise Slug", print_value=True) or ""
    emails_csv = extract_action_param(siemplify, param_name="Email Addresses", print_value=True)
    due_days = extract_action_param(siemplify, param_name="Due In Days", input_type=int, print_value=True)
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED
    try:
        learning_path_ref, exercise_slug = learning_path_ref.strip(), exercise_slug.strip()
        if bool(learning_path_ref) == bool(exercise_slug):
            msg = "Provide exactly one of 'Learning Path' or 'Exercise Slug'."
            raise RansomLeakValidationError(msg)
        if exercise_slug and due_days is not None:
            msg = "'Due In Days' only applies to learning paths."
            raise RansomLeakValidationError(msg)

        emails, skipped = collect_emails(siemplify, emails_csv)
        if skipped:
            siemplify.LOGGER.info(f"Skipped values that are not email addresses: {', '.join(skipped)}")
        if not emails:
            msg = "No email addresses found in the User entities or the 'Email Addresses' parameter."
            raise RansomLeakValidationError(msg)

        manager = build_manager(siemplify)
        if learning_path_ref:
            result = _enroll_learning_path(siemplify, manager, learning_path_ref, emails, due_days)
            target = f"learning path '{result['learning_path']['name']}'"
            done = [u["email"] for u in result["users"] if u["status"] in ENROLLED_STATUSES]
        else:
            result = _assign_exercise(siemplify, manager, exercise_slug, emails)
            target = f"exercise '{exercise_slug}'"
            done = [u["email"] for u in result["users"] if u.get("assignment_id")]
        result["skipped_identifiers"] = skipped
        siemplify.result.add_result_json(result)

        if done:
            output_message = f"Successfully assigned {target} to the following users in RansomLeak:\n" + "\n".join(done)
            if result["training_type"] == "learning_path":
                enrollment = result["enrollment"]
                output_message += (
                    f"\nNewly enrolled: {enrollment['assigned']}, already enrolled: "
                    f"{enrollment['already_enrolled']}, skipped for lack of a license: "
                    f"{enrollment['skipped_unlicensed']}."
                )
        else:
            output_message = f"No users were assigned {target}."
        for label, state in (
            ("were not found in RansomLeak", "not_found"),
            ("were not enrolled for lack of a license", "skipped_unlicensed"),
        ):
            matched = [u["email"] for u in result["users"] if u["status"] == state]
            if matched:
                output_message += f"\nThe following users {label}:\n" + "\n".join(matched)
        if skipped:
            output_message += "\nThe following values were skipped because they are not email addresses:\n" + (
                "\n".join(skipped)
            )
        result_value = bool(done)
    except Exception as error:
        siemplify.LOGGER.error(f'Error executing action "{ACTION_NAME}". Reason: {error}')
        siemplify.LOGGER.exception(error)
        output_message = f'Error executing action "{ACTION_NAME}". Reason: {error}'
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
