from __future__ import annotations

import json
from typing import TYPE_CHECKING

from TIPCommon.base.action.data_models import ExecutionState, Link
from TIPCommon.extraction import extract_action_param
from TIPCommon.smp_time import is_approaching_action_timeout

from ..core import constants
from ..core.base_action import HuntbaseAction

if TYPE_CHECKING:
    from typing import NoReturn


class GetHunt(HuntbaseAction):
    """Get a hunt's status, verdict, summary and findings; optionally wait until it finishes."""

    def __init__(self) -> None:
        super().__init__(constants.GET_HUNT_SCRIPT_NAME)
        self.error_output_message = f'Error executing action "{constants.GET_HUNT_SCRIPT_NAME}"'

    def _extract_action_parameters(self) -> None:
        self.params.hunt_id = extract_action_param(
            self.soar_action,
            param_name="Hunt ID",
            is_mandatory=True,
            print_value=True,
        ).strip()
        self.params.include_findings = extract_action_param(
            self.soar_action,
            param_name="Include Findings",
            input_type=bool,
            default_value=True,
            print_value=True,
        )
        self.params.wait = extract_action_param(
            self.soar_action,
            param_name="Wait For Completion",
            input_type=bool,
            default_value=False,
            print_value=True,
        )

    def _approaching_async_timeout(self) -> bool:
        deadline: int | None = getattr(self.soar_action, "async_total_duration_deadline", None)
        return bool(deadline) and is_approaching_action_timeout(deadline)

    def _perform_action(self, _: object) -> None:
        hunt = self.manager.get_hunt(self.params.hunt_id)

        if self.params.wait and not hunt.is_finished:
            if self._approaching_async_timeout():
                msg = (
                    f"Hunt {hunt.hunt_id} was still {hunt.status} when the action timed out. "
                    "Run Get Hunt again later, or raise the action's async timeout."
                )
                raise TimeoutError(msg)
            self.output_message = f"Waiting for Huntbase hunt {hunt.hunt_id} to finish (status: {hunt.status})."
            self.result_value = json.dumps({"hunt_id": hunt.hunt_id, "status": hunt.status})
            self.execution_state = ExecutionState.IN_PROGRESS
            return

        findings = self.manager.get_hunt_findings(hunt.hunt_id) if self.params.include_findings else None
        self.json_results = hunt.to_json(findings)
        self.links.append(Link(link=hunt.url, title=f"Huntbase hunt: {hunt.title or hunt.hunt_id}"))
        for finding in findings or []:
            if finding.url:
                self.links.append(Link(link=finding.url, title=f"Huntbase finding: {finding.title}"))

        parts = [f"Successfully retrieved Huntbase hunt {hunt.hunt_id} (status: {hunt.status}"]
        if hunt.verdict:
            parts[0] += f", verdict: {hunt.verdict}"
        parts[0] += ")."
        if findings is not None:
            parts.append(f"Findings: {len(findings)}.")
        self.output_message = " ".join(parts)
        self.result_value = True


def main() -> NoReturn:
    GetHunt().run()


if __name__ == "__main__":
    main()
