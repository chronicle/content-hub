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

from TIPCommon.extraction import extract_configuration_param, extract_action_param

from microsoft365_defender.core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    UPDATE_INCIDENT_SCRIPT_NAME,
    EMPTY_DROPDOWN_VALUE,
    CLASSIFICATION_MAPPING,
    DETERMINATION_MAPPING,
    LOGIN_API_ROOT_DEFAULT,
    GRAPH_API_ROOT_DEFAULT,
)
from microsoft365_defender.core.Microsoft365DefenderManager import Microsoft365DefenderManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_INCIDENT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    login_api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Login API Root",
        is_mandatory=True,
        default_value=LOGIN_API_ROOT_DEFAULT,
        print_value=True,
    )
    graph_api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Graph API Root",
        is_mandatory=True,
        default_value=GRAPH_API_ROOT_DEFAULT,
        print_value=True,
    )
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    tenant_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Tenant ID",
        is_mandatory=True,
        print_value=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        print_value=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Action parameters
    incident_id = extract_action_param(
        siemplify,
        param_name="Incident ID",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )
    incident_status = extract_action_param(
        siemplify, param_name="Status", print_value=True
    )
    classification = extract_action_param(
        siemplify, param_name="Classification", print_value=True
    )
    determination = extract_action_param(
        siemplify, param_name="Determination", print_value=True
    )
    assign_to = extract_action_param(
        siemplify, param_name="Assign To", print_value=True
    )

    incident_status = (
        incident_status if incident_status != EMPTY_DROPDOWN_VALUE else None
    )
    classification = (
        CLASSIFICATION_MAPPING.get(classification)
        if classification != EMPTY_DROPDOWN_VALUE
        else None
    )
    determination = (
        DETERMINATION_MAPPING.get(determination)
        if determination != EMPTY_DROPDOWN_VALUE
        else None
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        if all(
            value is None
            for value in [assign_to, incident_status, classification, determination]
        ):
            raise Exception(
                "at least one of the parameters should have a value provided."
            )

        manager = Microsoft365DefenderManager(
            api_root=api_root,
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
            microsoft_graph_url=graph_api_root,
            siemplify=siemplify,
            login_api_root=login_api_root,
        )
        manager.update_incident(
            incident_id=incident_id,
            status=(incident_status.lower() if incident_status is not None else ""),
            classification=classification,
            determination=determination,
            assign_to=assign_to,
        )
        result = True
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f"Successfully updated incident {incident_id} in {INTEGRATION_DISPLAY_NAME}"
        )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {UPDATE_INCIDENT_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = f'Error executing action "Update Incident". Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
