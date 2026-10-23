from __future__ import annotations

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param

from ..core.constants import ADD_CASE_COMMENT_SCRIPT_NAME


class AddCaseComment(Action):
    """Add a comment on the current Google SecOps case."""

    def __init__(self) -> None:
        super().__init__(ADD_CASE_COMMENT_SCRIPT_NAME)
        self.comment: str = ""

    def _init_api_clients(self) -> None:
        """No remote API client — this action only uses the SOAR SDK."""

    def _extract_action_parameters(self) -> None:
        self.comment = extract_action_param(
            self.soar_action,
            param_name="Comment",
            is_mandatory=True,
            print_value=True,
            default_value="",
        )

    def _perform_action(self, _=None) -> None:
        comment = str(self.comment or "").strip()
        if not comment:
            raise ValueError("Comment is required.")
        self._add_comment_to_case(comment)
        self.json_results = {"comment": comment}
        self.output_message = "Added a case comment."


def main() -> None:
    AddCaseComment().run()


if __name__ == "__main__":
    main()
