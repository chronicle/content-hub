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
from TIPCommon import extract_action_param, extract_configuration_param

from ..core.constants import ADD_DECEPTIVE_USER_SCRIPT_NAME, INTEGRATION_NAME, PRODUCT_NAME
from ..core.IllusiveNetworksExceptions import ManagerAlreadyExistException
from ..core.IllusiveNetworksManager import IllusiveNetworksManager
from ..core.Utils import string_to_multi_value


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_DECEPTIVE_USER_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
        print_value=False,
    )
    ca_certificate = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="CA Certificate File"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
    )

    username = extract_action_param(
        siemplify, param_name="Username", is_mandatory=True, print_value=True
    )
    password = extract_action_param(siemplify, param_name="Password", is_mandatory=True)
    dns_domain = extract_action_param(
        siemplify, param_name="DNS Domain", print_value=True
    )
    policy_names = string_to_multi_value(
        extract_action_param(siemplify, param_name="Policy Names", print_value=True)
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        manager = IllusiveNetworksManager(
            api_root=api_root,
            api_key=api_key,
            ca_certificate=ca_certificate,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        if manager.get_deceptive_user(username) is not None:
            msg = f'Deceptive user "{username}" already exists.'
            raise ManagerAlreadyExistException(
                msg
            )

        manager.add_deceptive_user(
            dns_domain=dns_domain,
            username=username,
            password=password,
            policy_names=policy_names,
        )

        output_message = f"Successfully added deceptive user in {PRODUCT_NAME}."
    except Exception as e:
        output_message = (
            f"Error executing action '{ADD_DECEPTIVE_USER_SCRIPT_NAME}'. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  "
        f"result_value: {result_value}\n  "
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
