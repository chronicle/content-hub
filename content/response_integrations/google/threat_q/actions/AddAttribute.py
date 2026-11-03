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
from ..core.custom_exceptions import (
    ThreatQManagerException,
    ObjectNotFoundException,
    ObjectCreateException,
)
from ..core.constants import INTEGRATION_NAME, ADD_ATTRIBUTE_SCRIPT


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_ATTRIBUTE_SCRIPT

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
        default_value="Adversary",
        is_mandatory=True,
        print_value=True,
    )

    object_identifier = extract_action_param(
        siemplify, param_name="Object Identifier", is_mandatory=True, print_value=True
    )

    indicator_type = extract_action_param(
        siemplify,
        param_name="Indicator Type",
        default_value="ASN",
        is_mandatory=False,
        print_value=True,
    )

    attribute_name = extract_action_param(
        siemplify, param_name="Attribute Name", is_mandatory=True, print_value=True
    )

    attribute_value = extract_action_param(
        siemplify, param_name="Attribute Value", is_mandatory=True, print_value=True
    )

    attribute_source = extract_action_param(
        siemplify, param_name="Attribute Source", is_mandatory=False, print_value=True
    )

    siemplify.LOGGER.info("=" * 10 + " Main - Started " + "=" * 10)

    try:
        threatq_manager = ThreatQManager(server_address, client_id, username, password)

        universal_object = threatq_manager.add_attribute_to_object(
            object_type=object_type,
            object_identifier=object_identifier,
            indicator_type=indicator_type,
            attribute_name=attribute_name,
            attribute_value=attribute_value,
            attribute_source=attribute_source,
        )

        siemplify.result.add_result_json(universal_object.to_json())

        output_message = f"Successfully added attribute {attribute_name} to {object_type} object in ThreatQ"
        result_value = True
        execution_status = EXECUTION_STATE_COMPLETED

    except ObjectNotFoundException as e:
        output_message = f"{object_type} object with value {object_identifier} was not found in ThreatQ."
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False
        execution_status = EXECUTION_STATE_COMPLETED

    except ObjectCreateException as e:
        output_message = f"Action was not able to add attribute {attribute_name} to the ThreatQ object."
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False
        execution_status = EXECUTION_STATE_COMPLETED

    except (ThreatQManagerException, Exception) as e:
        output_message = f'Error executing action "Add Attribute". Reason: {e}'
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
