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
from TIPCommon.validation import ParameterValidator

from ..core import action_init
from ..core import api_client
from ..core import constants
from ..core import exceptions

if TYPE_CHECKING:
    from typing import NoReturn

    from TIPCommon.types import SingleJson

    from ..core import datamodels


class ResolveIssue(Action):
    def __init__(self) -> None:
        super().__init__(constants.RESOLVE_ISSUE_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        self.params.issue_id = extract_action_param(
            self.soar_action,
            param_name="Issue ID",
            is_mandatory=True,
            print_value=True,
        )
        self.params.resolution_reason = extract_action_param(
            self.soar_action,
            param_name="Resolution Reason",
            is_mandatory=True,
            default_value=constants.DEFAULT_RESOLVE_ISSUE_RESOLUTION_REASON,
            print_value=True,
        )
        self.params.resolution_note = extract_action_param(
            self.soar_action,
            param_name="Resolution Note",
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)
        validator.validate_ddl(
            param_name="Resolution Reason",
            value=self.params.resolution_reason,
            ddl_values=list(constants.RESOLVE_ISSUE_RESOLUTION_REASONS.keys()),
            default_value=constants.DEFAULT_RESOLVE_ISSUE_RESOLUTION_REASON,
        )

    def _init_api_clients(self) -> api_client.WizApiClient:
        return action_init.create_api_client(self.soar_action)

    def _perform_action(self, _) -> None:
        self.json_results: SingleJson = self._resolve_issue().to_json()
        self.output_message: str = (
            "Successfully resolved issue with ID "
            f"{self.params.issue_id} in {constants.INTEGRATION_NAME}."
        )

    def _resolve_issue(self) -> datamodels.Issue:
        try:
            return self.api_client.resolve_issue(
                issue_id=self.params.issue_id,
                resolution_reason=self.params.resolution_reason,
                resolution_note=self.params.resolution_note,
            )

        except exceptions.IssueNotFoundError as e:
            raise exceptions.IssueNotFoundError(
                f"Issue with ID {self.params.issue_id} wasn't found in "
                f"{constants.INTEGRATION_NAME}."
            ) from e


def main() -> NoReturn:
    ResolveIssue().run()


if __name__ == "__main__":
    main()
