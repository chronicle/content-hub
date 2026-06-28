# Copyright 2026 Google LLC
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
from http import HTTPStatus

from okta.core.base_action import BaseAction
from okta.core.constants import (
    SEND_ITP_SIGNAL_ERROR_MESSAGE,
    SEND_ITP_SIGNAL_SCRIPT_NAME,
    SEVERITY_TYPE
)
from TIPCommon import validation
from TIPCommon.extraction import extract_action_param


class SendITPSignal(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = ""
        self.error_output_message = SEND_ITP_SIGNAL_ERROR_MESSAGE
        self.json_results = []
        self.result_value = True

    def _extract_action_parameters(self) -> None:
        self.params.key_id = extract_action_param(
            self.soar_action,
            param_name="Key ID",
            is_mandatory=True,
            print_value=False,
        )
        self.params.private_key = extract_action_param(
            self.soar_action,
            param_name="Private Key",
            is_mandatory=True,
            print_value=False,
            remove_whitespaces=False,
        )
        self.params.user_email = extract_action_param(
            self.soar_action,
            param_name="User Email",
            is_mandatory=True,
            print_value=False,
        )
        self.params.timestamp = extract_action_param(
            self.soar_action,
            param_name="Timestamp",
            is_mandatory=True,
            print_value=True,
        )
        self.params.reason = extract_action_param(
            self.soar_action,
            param_name="Reason",
            is_mandatory=True,
            print_value=True,
        )
        self.params.issuer_url = extract_action_param(
            self.soar_action,
            param_name="Issuer URL",
            is_mandatory=True,
            print_value=True,
        )
        self.params.severity = extract_action_param(
            self.soar_action,
            param_name="Severity",
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator = validation.ParameterValidator(self.soar_action)

        self.params.severity = validator.validate_ddl(
            param_name="Severity",
            value=self.params.severity,
            ddl_values=SEVERITY_TYPE,
        )
        self.params.user_email = validator.validate_email(
            param_name="User Email",
            email=self.params.user_email,
        )

    def _perform_action(self, _=None) -> None:
        self.api_client.test_connectivity()
        json_results = self.api_client.sent_itp_signal(
            key_id=self.params.key_id,
            private_key_string=self.params.private_key,
            timestamp=self.params.timestamp,
            user_email=self.params.user_email,
            reason=self.params.reason,
            severity=self.params.severity,
            data_issuer_url=self.params.issuer_url,
        )
        self.json_results = json_results
        if json_results.get("status") == HTTPStatus.ACCEPTED:
            self.output_message = "Successfully sent the ITP Signal to Okta."
        else:
            self.output_message = "Failed to send the ITP Signal to Okta."
            self.result_value = False


def main() -> None:
    SendITPSignal(SEND_ITP_SIGNAL_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
