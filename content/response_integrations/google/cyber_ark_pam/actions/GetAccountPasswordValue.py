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

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import INTEGRATION_NAME
from ..core.CyberArkPamManager import CyberArkPamManager, CyberArkPamNotFoundError

SCRIPT_NAME = "Get Account Password Value"


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    ca_certificate = extract_configuration_param(siemplify, provider_name=INTEGRATION_NAME, param_name="CA Certificate")
    client_certificate = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client Certificate"
    )
    client_certificate_passphrase = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Certificate Passphrase",
        remove_whitespaces=False,
    )

    account = extract_action_param(siemplify, param_name="Account", print_value=True, is_mandatory=True)
    reason = extract_action_param(siemplify, param_name="Reason", print_value=True, is_mandatory=True)
    ticketing_system_name = extract_action_param(siemplify, param_name="Ticketing System Name", print_value=True)
    ticket_id = extract_action_param(siemplify, param_name="Ticket ID", input_type=int, print_value=True)
    version = extract_action_param(siemplify, param_name="Version", input_type=int, print_value=True)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = "false"
    output_message = ""

    try:
        cyber_ark_manager = CyberArkPamManager(
            api_root=api_root,
            username=username,
            password=password,
            siemplify=siemplify,
            verify_ssl=verify_ssl,
            ca_certificate=ca_certificate,
            client_certificate=client_certificate,
            client_certificate_passphrase=client_certificate_passphrase,
        )
        siemplify.LOGGER.info("Connected successfully.")

        password = cyber_ark_manager.get_password(
            account=account,
            reason=reason,
            ticketing_system_name=ticketing_system_name,
            ticket_id=ticket_id,
            version=version,
        )

        result_value = "true"
        log_message = f"Successfully fetched password value for account id {account}"
        output_message += log_message
        siemplify.LOGGER.info(log_message)
        siemplify.result.add_result_json({"content": password})

    except CyberArkPamNotFoundError:
        log_message = (
            f"Password value for account with id {account}"
            f"and supplied version {version} was not found in the CyberArk PAM"
        )
        output_message += log_message
        siemplify.LOGGER.info(log_message)

    except Exception as e:
        result_value = "false"
        log_message = f"Error executing action “{SCRIPT_NAME}”. Reason: {e}"
        output_message = log_message
        siemplify.LOGGER.error(log_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
