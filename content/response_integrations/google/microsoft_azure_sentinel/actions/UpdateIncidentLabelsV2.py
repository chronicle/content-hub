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

from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED
from soar_sdk.ScriptResult import EXECUTION_STATE_INPROGRESS
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.smp_time import unix_now
from ..core import constants
from ..core.exceptions import MicrosoftAzureSentinelConflictError
from ..core.MicrosoftAzureSentinelManager import MicrosoftAzureSentinelManager
from ..core.utils import is_async_action_global_timeout_approaching
from ..core.utils import string_to_multi_value


@output_handler
def main():
    action_start_time = unix_now()
    siemplify = SiemplifyAction()
    siemplify.script_name = constants.UPDATE_INCIDENT_LABELS_V2_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Integration parameters
    api_root = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    login_url = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="OAUTH2 Login Endpoint Url",
        print_value=True,
    )
    client_id = extract_configuration_param(
        siemplify, provider_name=constants.INTEGRATION_NAME, param_name="Client ID"
    )
    client_secret = extract_configuration_param(
        siemplify, provider_name=constants.INTEGRATION_NAME, param_name="Client Secret"
    )
    tenant_id = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Azure Active Directory ID",
    )
    workspace_id = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Azure Sentinel Workspace Name",
        print_value=True,
    )
    resource = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Azure Resource Group",
        print_value=True,
    )
    subscription_id = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Azure Subscription ID",
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=constants.INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
    )

    # Action parameters
    incident_number = extract_action_param(
        siemplify,
        param_name="Incident Case Number",
        is_mandatory=True,
        print_value=True,
    )
    labels = string_to_multi_value(
        extract_action_param(siemplify, param_name="Labels", print_value=True)
    )
    number_of_tries = json.loads(
        extract_action_param(siemplify, param_name="additional_data", default_value="0")
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = (
        f"{constants.PRODUCT_NAME} incident with case number "
        f"{incident_number} was not found!"
    )
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    incident, updated_labels, already_existing_labels = None, None, None

    try:
        try:
            number_of_retries = extract_action_param(
                siemplify,
                param_name="Number of retries",
                print_value=True,
                input_type=int,
                default_value=1,
            )
            if number_of_retries <= 0:
                raise ValueError

        except ValueError as e:
            raise ValueError("Number of retries must be a positive integer") from e

        manager = MicrosoftAzureSentinelManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            resource=resource,
            subscription_id=subscription_id,
            login_url=login_url,
            verify_ssl=verify_ssl,
        )

        if is_async_action_global_timeout_approaching(siemplify, action_start_time):
            raise TimeoutError(
                "action ran into a timeout. Please increase the timeout in IDE."
            )

        try:
            incident, updated_labels, already_existing_labels = (
                manager.update_incident_labels(
                    incident_number=incident_number, labels=labels
                )
            )
        except MicrosoftAzureSentinelConflictError as error:
            if number_of_tries >= number_of_retries:
                raise

            number_of_tries += 1
            status = EXECUTION_STATE_INPROGRESS
            siemplify.LOGGER.error(error)
            output_message = (
                f"Retrying update of Microsoft Azure Sentinel "
                f"incident {incident_number}"
            )
            siemplify.LOGGER.info(output_message)
            result_value = json.dumps(number_of_tries)

        if incident:
            if updated_labels:
                output_message = (
                    f"Successfully updated {constants.PRODUCT_NAME} labels for "
                    f"incident {incident.name} with the "
                    f"following labels: {', '.join(updated_labels)}"
                )

                if already_existing_labels:
                    output_message += (
                        f"The following labels were not added to the "
                        f"{constants.PRODUCT_NAME} labels for incident "
                        f"{incident.name} because they already exist: "
                        f"{', '.join(already_existing_labels)}"
                    )
            else:
                output_message = (
                    f"The following labels were not added to the "
                    f"{constants.PRODUCT_NAME} labels for incident "
                    f"{incident.name} because they already exist: "
                    f"{', '.join(already_existing_labels)}"
                )
                result_value = False

            siemplify.result.add_result_json(incident.to_json())

    except Exception as e:
        output_message = (
            f"Error executing action "
            f'"{constants.UPDATE_INCIDENT_LABELS_V2_SCRIPT_NAME}". Reason: {e}'
        )
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        if type(e).__name__ not in constants.SAFE_ERRORS:
            siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}"
        f"\n  result_value: {result_value}"
        f"\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
