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
import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import flat_dict_to_csv

from microsoft_graph_security.core.constants import (
    DEFAULT_API_ROOT,
    DEFAULT_LOGIN_API_ROOT,
    GET_ALERT_SCRIPT_NAME,
    INTEGRATION_NAME,
)
from microsoft_graph_security.core.utils import GraphSecurityManagerConfig, init_graph_security_manager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_ALERT_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        input_type=str,
    )
    secret_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret ID",
        is_mandatory=False,
        input_type=str,
    )
    certificate_path = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Certificate Path",
        is_mandatory=False,
        input_type=str,
    )
    certificate_password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Certificate Password",
        is_mandatory=False,
        input_type=str,
    )
    tenant = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Tenant",
        is_mandatory=True,
        input_type=str,
    )
    use_v2_api = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use V2 API",
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    api_root = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        default_value=DEFAULT_API_ROOT,
        print_value=True,
    )
    login_api_root = extract_configuration_param(
        siemplify=siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Login API Root",
        default_value=DEFAULT_LOGIN_API_ROOT,
        print_value=True,
    )

    alert_id = extract_action_param(
        siemplify,
        param_name="Alert ID",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_results = {}
    config = GraphSecurityManagerConfig(
        client_id=client_id,
        secret_id=secret_id,
        certificate_path=certificate_path,
        certificate_password=certificate_password,
        tenant=tenant,
        verify_ssl=verify_ssl,
        api_root=api_root,
        login_api_root=login_api_root,
        chronicle_soar=siemplify,
    )
    try:
        siemplify.LOGGER.info("Connecting to Microsoft Graph Security.")
        mtm = init_graph_security_manager(
            config=config,
            use_v2_api=use_v2_api,
        )
        siemplify.LOGGER.info("Connected successfully.")

        siemplify.LOGGER.info(f"Fetching alert {alert_id}")
        alert = mtm.get_alert_details(alert_id)

        if alert:
            siemplify.LOGGER.info(f"Found alert {alert_id} information.")
            siemplify.result.add_data_table(
                f"Alert {alert_id}", flat_dict_to_csv(alert.as_csv())
            )

            json_results = alert.raw_data
            output_message = f"Alert {alert_id} information was found."
            result_value = json.dumps(alert.raw_data)

        else:
            siemplify.LOGGER.info(f"Alert {alert_id} information was not found.")
            output_message = f"Alert {alert_id} information was not found."
            result_value = json.dumps({})

        status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        siemplify.LOGGER.error(f"Some errors occurred. Error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = json.dumps({})
        output_message = f"Some errors occurred. Error: {e}"

    siemplify.result.add_result_json(json_results)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
