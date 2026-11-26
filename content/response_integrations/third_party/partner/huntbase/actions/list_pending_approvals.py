from __future__ import annotations

from typing import TYPE_CHECKING

from TIPCommon.base.action.data_models import Link
from TIPCommon.extraction import extract_action_param

from ..core import constants
from ..core.base_action import HuntbaseAction

if TYPE_CHECKING:
    from typing import NoReturn


class ListPendingApprovals(HuntbaseAction):
    """List Scout proposals waiting for a person to approve them in Huntbase."""

    def __init__(self) -> None:
        super().__init__(constants.LIST_PENDING_APPROVALS_SCRIPT_NAME)
        self.error_output_message = f'Error executing action "{constants.LIST_PENDING_APPROVALS_SCRIPT_NAME}"'

    def _extract_action_parameters(self) -> None:
        self.params.limit = extract_action_param(
            self.soar_action,
            param_name="Max Results",
            input_type=int,
            default_value=constants.DEFAULT_PENDING_APPROVALS_LIMIT,
            print_value=True,
        )

    def _validate_params(self) -> None:
        if not 1 <= self.params.limit <= constants.MAX_PENDING_APPROVALS_LIMIT:
            msg = f"Max Results must be between 1 and {constants.MAX_PENDING_APPROVALS_LIMIT}."
            raise ValueError(msg)

    def _perform_action(self, _: object) -> None:
        proposals = self.manager.list_pending_approvals(limit=self.params.limit)
        self.json_results = {
            "count": len(proposals),
            "approvals_url": self.manager.app_link("approvals"),
            "items": [p.to_json() for p in proposals],
        }
        self.links.append(Link(link=self.manager.app_link("approvals"), title="Huntbase approvals"))
        if proposals:
            self.output_message = f"Successfully found {len(proposals)} pending approval(s) in Huntbase."
        else:
            self.output_message = "No pending approvals in Huntbase."
        self.result_value = bool(proposals)


def main() -> NoReturn:
    ListPendingApprovals().run()


if __name__ == "__main__":
    main()
