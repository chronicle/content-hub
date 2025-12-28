# Copyright 2025 Google LLC
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

from typing import TYPE_CHECKING

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param

from ..core import action_init
from ..core import api_client
from ..core import constants
from ..core import exceptions


if TYPE_CHECKING:
    from typing import NoReturn

    from TIPCommon.types import SingleJson

    from ..core import datamodels


class AddCommentToIssue(Action):
    def __init__(self) -> None:
        super().__init__(constants.ADD_COMMENT_TO_ISSUE_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        self.params.issue_id = extract_action_param(
            self.soar_action,
            param_name="Issue ID",
            is_mandatory=True,
            print_value=True,
        )
        self.params.comment = extract_action_param(
            self.soar_action,
            param_name="Comment",
            is_mandatory=True,
            print_value=True,
        )

    def _init_api_clients(self) -> api_client.WizApiClient:
        return action_init.create_api_client(self.soar_action)

    def _perform_action(self, _) -> None:
        self.json_results: SingleJson = self._add_comment_to_issue().to_json()
        self.output_message: str = (
            "Successfully added a comment to the issue with ID "
            f"{self.params.issue_id} in {constants.INTEGRATION_NAME}."
        )

    def _add_comment_to_issue(self) -> datamodels.IssueComment:
        try:
            return self.api_client.add_comment_to_issue(
                issue_id=self.params.issue_id,
                comment=self.params.comment,
            )

        except exceptions.IssueNotFoundError as e:
            raise exceptions.IssueNotFoundError(
                f"Issue with ID {self.params.issue_id} wasn't found in "
                f"{constants.INTEGRATION_NAME}."
            ) from e


def main() -> NoReturn:
    AddCommentToIssue().run()


if __name__ == "__main__":
    main()
