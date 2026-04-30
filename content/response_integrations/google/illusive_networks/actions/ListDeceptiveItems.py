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
from TIPCommon import construct_csv, extract_action_param, extract_configuration_param

from ..core.constants import (
    ALL,
    DECEPTIVE_SERVERS_TABLE_NAME,
    DECEPTIVE_STATE_MAPPING,
    DECEPTIVE_USERS_TABLE_NAME,
    INTEGRATION_NAME,
    LIST_DECEPTIVE_ITEMS_ACTION,
    ONLY_SERVERS,
    ONLY_USERS,
    PRODUCT_NAME,
)
from ..core.IllusiveNetworksManager import IllusiveNetworksManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_DECEPTIVE_ITEMS_ACTION
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

    deceptive_type = extract_action_param(
        siemplify, param_name="Deceptive Type", print_value=True, default_value=ALL
    )
    deceptive_state = extract_action_param(
        siemplify, param_name="Deceptive State", print_value=True, default_value=ALL
    )
    max_items_to_return = extract_action_param(
        siemplify, param_name="Max Items To Return", print_value=True, input_type=int
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = (
        f"Successfully returned available deceptive items from {PRODUCT_NAME}."
    )
    deceptive_users, deceptive_servers = [], []

    try:
        manager = IllusiveNetworksManager(
            api_root=api_root,
            api_key=api_key,
            ca_certificate=ca_certificate,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        if deceptive_type in {ALL, ONLY_USERS}:
            deceptive_users = manager.get_deceptive_users(
                deceptive_state=DECEPTIVE_STATE_MAPPING[deceptive_state],
                limit=max_items_to_return,
            )
        if deceptive_type in {ALL, ONLY_SERVERS}:
            deceptive_servers = manager.get_deceptive_servers(
                deceptive_state=DECEPTIVE_STATE_MAPPING[deceptive_state],
                limit=max_items_to_return,
            )

        if deceptive_users:
            siemplify.result.add_data_table(
                DECEPTIVE_USERS_TABLE_NAME,
                construct_csv([user.to_table() for user in deceptive_users]),
            )
        if deceptive_servers:
            siemplify.result.add_data_table(
                DECEPTIVE_SERVERS_TABLE_NAME,
                construct_csv([server.to_table() for server in deceptive_servers]),
            )

        if deceptive_users or deceptive_servers:
            json_results = {
                "users": [user.to_json() for user in deceptive_users],
                "servers": [server.to_json() for server in deceptive_servers],
            }
            siemplify.result.add_result_json(json_results)
        else:
            output_message = (
                f"No data was found regarding deceptive items based on "
                f"the provided criteria in {PRODUCT_NAME}."
            )
            result_value = False

    except Exception as err:
        output_message = (
            f"Error executing action '{LIST_DECEPTIVE_ITEMS_ACTION}'. Reason: {err}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)
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
