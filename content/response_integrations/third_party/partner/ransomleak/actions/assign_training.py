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

from TIPCommon.extraction import extract_action_param

from ..core.base_action import BaseAction
from ..core.constants import (
    ASSIGN_TRAINING_ACTION_NAME,
    ASSIGN_TRAINING_SCRIPT_NAME,
    ENROLLED_STATUSES,
    MAX_ENROLLMENT_BATCH,
)
from ..core.data_models import AssignmentRequest, EnrollmentCounts
from ..core.exceptions import RansomLeakNotFoundError, RansomLeakValidationError
from ..core.utils import collect_emails, section

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

    from ..core.data_models import LearningPath

MAX_IDEMPOTENCY_KEY_LENGTH: int = 255


def _user_item(email: str) -> SingleJson:
    """Return a per-user result with the same keys in both modes (unused ones stay None)."""
    return {
        "email": email,
        "user_id": None,
        "enrollment_id": None,
        "assignment_id": None,
        "status": "pending",
        "created_at": None,
        "error": None,
    }


class AssignTrainingAction(BaseAction):
    """Assign a learning path or a single exercise to users."""

    def __init__(self) -> None:
        super().__init__(ASSIGN_TRAINING_SCRIPT_NAME, ASSIGN_TRAINING_ACTION_NAME)

    def _extract_action_parameters(self) -> None:
        learning_path: str | None = extract_action_param(
            self.soar_action,
            param_name="Learning Path",
            print_value=True,
        )
        exercise_slug: str | None = extract_action_param(
            self.soar_action,
            param_name="Exercise Slug",
            print_value=True,
        )
        emails_csv: str | None = extract_action_param(
            self.soar_action,
            param_name="Email Addresses",
            print_value=True,
        )
        due_days: int | None = extract_action_param(
            self.soar_action,
            param_name="Due In Days",
            input_type=int,
            print_value=True,
        )
        self.params.learning_path = (learning_path or "").strip()
        self.params.exercise_slug = (exercise_slug or "").strip()
        self.params.emails_csv = emails_csv
        self.params.due_days = due_days

    def _validate_params(self) -> None:
        if bool(self.params.learning_path) == bool(self.params.exercise_slug):
            msg = "Provide exactly one of 'Learning Path' or 'Exercise Slug'."
            raise RansomLeakValidationError(msg)
        if self.params.exercise_slug and self.params.due_days is not None:
            msg = "'Due In Days' only applies to learning paths."
            raise RansomLeakValidationError(msg)
        emails, skipped = collect_emails(self.soar_action, self.params.emails_csv)
        if skipped:
            self.logger.info(f"Skipped values that are not email addresses: {', '.join(skipped)}")
        if not emails:
            msg = "No email addresses found in the User entities or the 'Email Addresses' parameter."
            raise RansomLeakValidationError(msg)
        self.params.emails = emails
        self.params.skipped = skipped

    def _find_learning_path(self) -> LearningPath:
        learning_path = self.api_client.find_learning_path(self.params.learning_path)
        if learning_path is None:
            msg = (
                f"Learning path '{self.params.learning_path}' was not found. "
                "Use 'List Learning Paths' to find a valid ID."
            )
            raise RansomLeakNotFoundError(msg)
        return learning_path

    def _enroll_learning_path(self, emails: list[str]) -> SingleJson:
        learning_path = self._find_learning_path()
        by_email: dict[str, SingleJson] = {email.lower(): _user_item(email) for email in emails}
        totals = EnrollmentCounts()
        for start in range(0, len(emails), MAX_ENROLLMENT_BATCH):
            batch = emails[start : start + MAX_ENROLLMENT_BATCH]
            self.logger.info(f"Enrolling {len(batch)} user(s) in learning path {learning_path.id}")
            response = self.api_client.enroll_learning_path(
                learning_path.id,
                emails=batch,
                due_days=self.params.due_days,
            )
            totals += EnrollmentCounts.from_json(response)
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
                entry = by_email[email.lower()]
                if entry["status"] == "pending":
                    entry["status"] = "not_found" if email.lower() in not_found else "submitted"
        return {
            "training_type": "learning_path",
            "learning_path": {"id": learning_path.id, "name": learning_path.name},
            "exercise_slug": None,
            "due_in_days": self.params.due_days,
            "enrollment": totals.to_json(),
            "users": list(by_email.values()),
        }

    def _assign_exercise(self, emails: list[str]) -> SingleJson:
        exercise_slug: str = self.params.exercise_slug
        case_id = str(getattr(self.soar_action, "case_id", "") or "")
        users: list[SingleJson] = []
        for email in emails:
            entry = _user_item(email)
            users.append(entry)
            # Stable per case + exercise + user, so playbook re-runs return the same assignment.
            idempotency_key = f"secops:{case_id or 'manual'}:{exercise_slug}:{email.lower()}"
            request = AssignmentRequest(
                exercise_slug=exercise_slug,
                email=email,
                idempotency_key=idempotency_key[:MAX_IDEMPOTENCY_KEY_LENGTH],
                reference=case_id or None,
            )
            try:
                assignment = self.api_client.create_assignment(request)
            except RansomLeakNotFoundError as error:
                self.logger.info(f"Assignment for {email} not created: {error}")
                entry.update({"status": "not_found", "error": str(error)})
                continue
            entry.update({
                "user_id": assignment.user_id,
                "assignment_id": assignment.assignment_id,
                "status": assignment.status,
                "created_at": assignment.created_at,
            })
        return {
            "training_type": "exercise",
            "learning_path": None,
            "exercise_slug": exercise_slug,
            "due_in_days": None,
            "enrollment": None,
            "users": users,
        }

    def _build_output_message(self, result: SingleJson, target: str, done: list[str]) -> str:
        if done:
            message = f"Successfully assigned {target} to the following users in RansomLeak:\n" + "\n".join(done)
            if result["training_type"] == "learning_path":
                enrollment = result["enrollment"]
                message += (
                    f"\nNewly enrolled: {enrollment['assigned']}, already enrolled: "
                    f"{enrollment['already_enrolled']}, skipped for lack of a license: "
                    f"{enrollment['skipped_unlicensed']}."
                )
        else:
            message = f"No users were assigned {target}."
        for label, state in (
            ("were not found in RansomLeak", "not_found"),
            ("were not enrolled for lack of a license", "skipped_unlicensed"),
        ):
            message += section(
                f"The following users {label}",
                [u["email"] for u in result["users"] if u["status"] == state],
            )
        message += section(
            "The following values were skipped because they are not email addresses",
            self.params.skipped,
        )
        return message

    def _perform_action(self, _: object = None) -> None:
        emails: list[str] = self.params.emails
        if self.params.learning_path:
            result = self._enroll_learning_path(emails)
            target = f"learning path '{result['learning_path']['name']}'"
            done = [u["email"] for u in result["users"] if u["status"] in ENROLLED_STATUSES]
        else:
            result = self._assign_exercise(emails)
            target = f"exercise '{self.params.exercise_slug}'"
            done = [u["email"] for u in result["users"] if u["assignment_id"]]
        result["skipped_identifiers"] = self.params.skipped
        self.json_results = result
        self.output_message = self._build_output_message(result, target, done)
        self.result_value = bool(done)


def main() -> NoReturn:
    AssignTrainingAction().run()


if __name__ == "__main__":
    main()
