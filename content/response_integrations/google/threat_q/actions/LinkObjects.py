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

from threat_q.core.ThreatQManager import ThreatQManager
from threat_q.core.custom_exceptions import (
    ThreatQManagerException,
    ObjectNotFoundException,
    SourceObjectNotFoundException,
    DestinationObjectNotFoundException,
)
from threat_q.core.constants import INTEGRATION_NAME, LINK_OBJECTS_SCRIPT


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LINK_OBJECTS_SCRIPT

    siemplify.LOGGER.info("=" * 10 + " Main - Param Init " + "=" * 10)

    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="ServerAddress",
        input_type=str,
    )

    client_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="ClientId", input_type=str
    )

    username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Username", input_type=str
    )

    password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Password", input_type=str
    )

    source_object_type = extract_action_param(
        siemplify,
        param_name="Source Object Type",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    source_object_identifier = extract_action_param(
        siemplify,
        param_name="Source Object Identifier",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    source_indicator_type = extract_action_param(
        siemplify,
        param_name="Source Indicator Type",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    destination_object_type = extract_action_param(
        siemplify,
        param_name="Destination Object Type",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    destination_object_identifier = extract_action_param(
        siemplify,
        param_name="Destination Object Identifier",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    destination_indicator_type = extract_action_param(
        siemplify,
        param_name="Destination Indicator Type",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    siemplify.LOGGER.info("=" * 10 + " Main - Started " + "=" * 10)

    try:
        threatq_manager = ThreatQManager(server_address, client_id, username, password)

        linked_object = threatq_manager.link_objects(
            source_object_type=source_object_type,
            source_identifier=source_object_identifier,
            source_indicator_type=source_indicator_type,
            destination_object_type=destination_object_type,
            destination_identifier=destination_object_identifier,
            destination_indicator_type=destination_indicator_type,
        )

        siemplify.result.add_result_json(linked_object.to_json())

        output_message = "Successfully linked objects in ThreatQ"
        result_value = True
        execution_status = EXECUTION_STATE_COMPLETED

    except ObjectNotFoundException as e:
        if isinstance(e, SourceObjectNotFoundException):
            output_message = f"{source_object_type} object with value {source_object_identifier} was not found in ThreatQ."
        elif isinstance(e, DestinationObjectNotFoundException):
            output_message = f"{destination_object_type} object with value {destination_object_identifier} was not found in ThreatQ."

        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False
        execution_status = EXECUTION_STATE_COMPLETED

    except ThreatQManagerException as e:
        output_message = "Action was not able to link objects in ThreatQ."
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False
        execution_status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        output_message = f"Error executing action Link Objects. Reason: {e}"
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
