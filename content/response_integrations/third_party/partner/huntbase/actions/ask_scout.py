from __future__ import annotations

import json
from typing import TYPE_CHECKING

from TIPCommon.base.action.data_models import ExecutionState, Link
from TIPCommon.extraction import extract_action_param
from TIPCommon.smp_time import is_approaching_action_timeout

from ..core import constants
from ..core.base_action import HuntbaseAction
from ..core.utils import external_ref, seed_values_from_entities

if TYPE_CHECKING:
    from typing import NoReturn

    from ..core.datamodels import ScoutJob


class AskScout(HuntbaseAction):
    """Ask Scout, the Huntbase investigation partner, a question (async: submit, then poll)."""

    def __init__(self) -> None:
        super().__init__(constants.ASK_SCOUT_SCRIPT_NAME)
        self.error_output_message = f'Error executing action "{constants.ASK_SCOUT_SCRIPT_NAME}"'

    def _extract_action_parameters(self) -> None:
        self.params.question = extract_action_param(
            self.soar_action, param_name="Question", is_mandatory=True, print_value=True
        )
        self.params.hunt_id = extract_action_param(self.soar_action, param_name="Hunt ID", print_value=True)
        self.params.include_context = extract_action_param(
            self.soar_action,
            param_name="Include Case Context",
            input_type=bool,
            default_value=True,
            print_value=True,
        )
        self.params.initiative = extract_action_param(
            self.soar_action,
            param_name="Initiative",
            default_value="medium",
            print_value=True,
        )
        self.params.additional_data = extract_action_param(
            self.soar_action, param_name="additional_data", default_value="", print_value=False
        )

    def _validate_params(self) -> None:
        if len((self.params.question or "").strip()) < 3:  # noqa: PLR2004
            msg = "Question must be at least 3 characters."
            raise ValueError(msg)
        self.params.initiative = (self.params.initiative or "medium").strip().lower()
        if self.params.initiative not in constants.SCOUT_INITIATIVES:
            msg = f"Initiative must be one of: {', '.join(constants.SCOUT_INITIATIVES)}."
            raise ValueError(msg)

    def _previous_job_id(self) -> str | None:
        raw = self.params.additional_data
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return None
        return data.get("job_id") if isinstance(data, dict) else None

    def _perform_action(self, _: object) -> None:
        job_id = self._previous_job_id()
        if job_id is None:
            question = self.params.question.strip()
            ref = None
            if self.params.include_context:
                ref = external_ref(self.soar_action)
                seeds = seed_values_from_entities(self.soar_action.target_entities)
                if seeds:
                    listed = ", ".join(f"{seed['type']} {seed['value']}" for seed in seeds)
                    question = f"{question}\n\nEntities in the Google SecOps case: {listed}"
            job = self.manager.ask_scout(
                question[: constants.MAX_SCOUT_QUESTION_CHARS],
                hunt_id=(self.params.hunt_id or "").strip() or None,
                external_ref=ref,
                initiative=self.params.initiative,
            )
        else:
            job = self.manager.get_scout_job(job_id)

        if job.is_failed:
            msg = f"Scout could not answer (job {job.job_id}, status {job.status}): {job.error or 'no reason given'}"
            raise RuntimeError(msg)

        if not job.is_done:
            if job_id is not None and self._approaching_async_timeout():
                msg = f"Scout was still working on job {job.job_id} when the action timed out."
                raise TimeoutError(msg)
            self.output_message = f"Scout is working on the question (job {job.job_id}, status {job.status})."
            self.result_value = json.dumps({"job_id": job.job_id})
            self.execution_state = ExecutionState.IN_PROGRESS
            return

        self._complete(job)

    def _approaching_async_timeout(self) -> bool:
        deadline = getattr(self.soar_action, "async_total_duration_deadline", None)
        return bool(deadline) and is_approaching_action_timeout(deadline)

    def _complete(self, job: ScoutJob) -> None:
        self.json_results = job.to_json() | {"question": self.params.question.strip()}
        if job.url:
            self.links.append(Link(link=job.url, title="Scout's answer in Huntbase"))
        self.output_message = "Successfully received Scout's answer.\n\n" + (job.answer or job.summary or "")
        self.result_value = True


def main() -> NoReturn:
    AskScout().run()


if __name__ == "__main__":
    main()
