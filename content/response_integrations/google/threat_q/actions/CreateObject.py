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
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from ..core.ThreatQManager import ThreatQManager
from ..core.custom_exceptions import ThreatQManagerException, ObjectCreateException
from ..core.constants import INTEGRATION_NAME, CREATE_OBJECT_SCRIPT


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_OBJECT_SCRIPT

    siemplify.LOGGER.info("=" * 10 + " Main - Param Init " + "=" * 10)

    server_address = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="ServerAddress"
    )

    client_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="ClientId"
    )

    username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Username"
    )

    password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Password"
    )

    object_type = extract_action_param(
        siemplify,
        param_name="Object Type",
        default_value="Attack Pattern",
        is_mandatory=True,
        print_value=True,
    )

    value = extract_action_param(
        siemplify, param_name="Value", is_mandatory=True, print_value=True
    )

    description = extract_action_param(
        siemplify, param_name="Description", is_mandatory=False, print_value=True
    )

    siemplify.LOGGER.info("=" * 10 + " Main - Started " + "=" * 10)

    try:
        threatq_manager = ThreatQManager(server_address, client_id, username, password)

        new_object = threatq_manager.create_object(
            object_type=object_type, value=value, description=description
        )

        siemplify.result.add_result_json(new_object.to_json())

        output_message = f"Successfully created new {object_type} object in ThreatQ"
        result_value = True
        execution_status = EXECUTION_STATE_COMPLETED

    except ObjectCreateException as e:
        output_message = (
            f"Action was not able to create new {object_type} object in ThreatQ."
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False
        execution_status = EXECUTION_STATE_COMPLETED

    except (ThreatQManagerException, Exception) as e:
        output_message = f'Error executing action "Create Object". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False
        execution_status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("=" * 10 + " Main - Finished " + "=" * 10)
    siemplify.LOGGER.info(
        f"Status: {execution_status}, Result Value: {result_value}, Output Message: {output_message}"
    )
    siemplify.end(output_message, result_value, execution_status)


if __name__ == "__main__":
    main()
