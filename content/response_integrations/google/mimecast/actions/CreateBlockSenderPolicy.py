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
from typing import NoReturn

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from TIPCommon.validation import ParameterValidator
from ..core import constants
from ..core.datamodels import BlockSenderPolicyActionParams
from ..core.MimecastExceptions import MimecastException
from ..core.MimecastManager import MimecastManager
from ..core import UtilsManager as utils


class CreateBlockSenderPolicy(Action):
    def __init__(self) -> None:
        super().__init__(constants.CREATE_BLOCK_SENDER_POLICY_SCRIPT_NAME)
        self.error_output_message = (
            "Error executing action "
            f"\"{constants.CREATE_BLOCK_SENDER_POLICY_SCRIPT_NAME}\"."
        )
        self.json_results = None
        self.output_message = None
        self.is_success = False

    def _extract_action_parameters(self) -> None:
        self.params.integration_parameters = utils.get_integration_parameters(
            siemplify=self.soar_action
        )
        self.params.response = extract_action_param(
            siemplify=self.soar_action,
            param_name="Response",
            default_value="Block Sender",
            print_value=True,
        )
        self.params.description = extract_action_param(
            siemplify=self.soar_action,
            param_name="Description",
            print_value=True,
            is_mandatory=True,
        )
        self.params.extracted_data = extract_action_param(
            siemplify=self.soar_action,
            param_name="Extracted Data",
            default_value="Both",
            print_value=True,
        )
        self.params.sender = extract_action_param(
            siemplify=self.soar_action,
            param_name="Sender",
            print_value=True,
        )
        self.params.sender_type = extract_action_param(
            siemplify=self.soar_action,
            param_name="Sender Type",
            print_value=True,
            default_value="Email Domain"
        )
        self.params.recipient = extract_action_param(
            siemplify=self.soar_action,
            param_name="Recipient",
            print_value=True,
        )
        self.params.recipient_type = extract_action_param(
            siemplify=self.soar_action,
            param_name="Recipient Type",
            print_value=True,
            default_value="Email Domain",
        )
        self.params.comment = extract_action_param(
            siemplify=self.soar_action,
            param_name="Comment",
            print_value=True,
        )
        self.params.bidirectional = extract_action_param(
            siemplify=self.soar_action,
            param_name="Bidirectional",
            default_value="true",
            print_value=True,
        )
        self.params.enforced = extract_action_param(
            siemplify=self.soar_action,
            param_name="Enforced",
            default_value="true",
            print_value=True,
        )
        self.params.start_time = extract_action_param(
            siemplify=self.soar_action,
            param_name="Start Time",
            print_value=True,
        )
        self.params.end_time = extract_action_param(
            siemplify=self.soar_action,
            param_name="End Time",
            print_value=True,
        )


    def _validate_params(self) -> None:
        super()._validate_params()
        validator = ParameterValidator(self.soar_action)
        validator.validate_ddl(
            param_name="Response",
            value=self.params.response,
            ddl_values=constants.RESPONSE,
            case_sensitive=True,
        )
        validator.validate_ddl(
            param_name="Extracted Data",
            value=self.params.extracted_data,
            ddl_values=constants.EXTRACTED_DATA,
            case_sensitive=True,
        )
        validator.validate_ddl(
            param_name="Sender Type",
            value=self.params.sender_type,
            ddl_values=constants.SENDER_RECIPIENT_TYPE
        )
        validator.validate_ddl(
            param_name="Recipient Type",
            value=self.params.recipient_type,
            ddl_values=constants.SENDER_RECIPIENT_TYPE
        )

        if self.params.sender_type in constants.VALID_SENDER_RECIPIENT_TYPES:
            if  not self.params.sender:
                raise MimecastException(constants.SENDER_REQUIRED_ERROR)
            if self.params.sender_type == constants.EMAIL_ADDRESS:
                validator.validate_email(
                    param_name="Sender",
                    email=self.params.sender,
                )

        if self.params.recipient_type in constants.VALID_SENDER_RECIPIENT_TYPES:
            if not self.params.recipient:
                raise MimecastException(constants.RECIPIENT_REQUIRED_ERROR)
            if self.params.recipient_type == constants.EMAIL_ADDRESS:
                validator.validate_email(
                    param_name="Recipient",
                    email=self.params.recipient,
                )


    def _init_api_clients(self) -> MimecastManager:
        return MimecastManager(
            api_root=self.params.integration_parameters.api_root,
            app_id=self.params.integration_parameters.app_id,
            app_key=self.params.integration_parameters.app_key,
            access_key=self.params.integration_parameters.access_key,
            secret_key=self.params.integration_parameters.secret_key,
            client_id=self.params.integration_parameters.client_id,
            client_secret=self.params.integration_parameters.client_secret,
            verify_ssl=self.params.integration_parameters.verify_ssl,
            siemplify=self.soar_action,
        )


    def _perform_action(self, _) -> None:
        action_params = BlockSenderPolicyActionParams(
            response=self.params.response,
            description=self.params.description,
            extracted_data=self.params.extracted_data,
            sender=self.params.sender,
            sender_type=self.params.sender_type,
            recipient=self.params.recipient,
            recipient_type=self.params.recipient_type,
            comment=self.params.comment,
            bidirectional=self.params.bidirectional,
            enforced=self.params.enforced,
            start_time=self.params.start_time,
            end_time=self.params.end_time
        )
        result = self.api_client.create_block_sender_policy(action_params)
        self.json_results = result.to_json()
        self.output_message = (
            "Successfully created a block sender policy in Mimecast"
        )
        self.is_success = True
        self.soar_action.LOGGER.info(self.output_message)


def main() -> NoReturn:
    CreateBlockSenderPolicy().run()


if __name__ == "__main__":
    main()
