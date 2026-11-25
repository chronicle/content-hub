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
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon import (
    extract_action_param,
    extract_configuration_param,
    string_to_multi_value,
)

from ..core.constants import (
    AZURE_AD_ENDPOINT_DEFAULT_VALUE,
    INTEGRATION_NAME,
    MICROSOFT_GRAPH_ENDPOINT_DEFAULT_VALUE,
    REMOTE_LOCK_MANAGED_DEVICE_SCRIPT_NAME,
)
from ..core.exceptions import MicrosoftIntuneBadRequestError, MissingHostNameIDEntitiesError
from ..core.MicrosoftIntuneManager import MicrosoftIntuneManager
from ..core.UtilsManager import (
    check_multiple_host_id_exists,
    get_entity_original_identifier,
    get_valid_host_id_by_name,
    is_valid_host,
)


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = REMOTE_LOCK_MANAGED_DEVICE_SCRIPT_NAME
    siemplify.LOGGER.info("--------------- Main - Param Init ---------------")
    azure_ad_endpoint = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Azure AD endpoint",
        is_mandatory=True,
        print_value=True,
        default_value=AZURE_AD_ENDPOINT_DEFAULT_VALUE,
    )

    microsoft_graph_endpoint = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Microsoft Graph Endpoint",
        is_mandatory=True,
        print_value=True,
        default_value=MICROSOFT_GRAPH_ENDPOINT_DEFAULT_VALUE,
    )

    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        print_value=True,
    )

    client_secret_value = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret Value",
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )

    azure_ad_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Azure Active Directory ID",
        is_mandatory=True,
        print_value=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
        default_value=True,
    )

    # Action parameters
    host_names = string_to_multi_value(
        extract_action_param(siemplify, param_name="Host Name", print_value=True)
    )
    host_ids = string_to_multi_value(
        extract_action_param(siemplify, param_name="Host Id", print_value=True)
    )

    siemplify.LOGGER.info("---------------- Main - Started ----------------")
    output_message = ""
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    successful_host = []
    failed_host = []
    bad_request_host = []
    host_names_entity = (
        host_names
        if host_names
        else [
            get_entity_original_identifier(entity)
            for entity in siemplify.target_entities
            if entity.entity_type == EntityTypes.HOSTNAME
        ]
    )

    try:
        if not host_ids and not host_names:
            raise MissingHostNameIDEntitiesError(
                "Action failed to start since Hostname or Host ID was not "
                "provided either as Siemplify Entity or action input parameter."
            )

        siemplify.LOGGER.info("Initializing manager")
        manager = MicrosoftIntuneManager(
            azure_ad_endpoint=azure_ad_endpoint,
            microsoft_graph_endpoint=microsoft_graph_endpoint,
            client_id=client_id,
            client_secret_value=client_secret_value,
            azure_ad_id=azure_ad_id,
            verify_ssl=verify_ssl,
            logger=siemplify.LOGGER,
        )

        siemplify.LOGGER.info("Fetching all devices")
        action_result = manager.list_all_managed_devices(
            host_ids=host_ids, host_names=host_names
        )
        devices = action_result.devices
        if host_ids:
            siemplify.LOGGER.info(f"Found {len(host_ids)} host IDs")
            for host_id in host_ids:
                try:
                    if is_valid_host(devices, host_id, is_host_id=True):
                        siemplify.LOGGER.info(
                            "Creating remote lock task for managed device with "
                            f'host ID "{host_id}"'
                        )
                        manager.remote_lock_managed_device(host_id)
                        successful_host.append(host_id)

                    else:
                        siemplify.LOGGER.info(
                            f"Host ID '{host_id}' doesn't belong to any of the "
                            "fetched devices. Skipping..."
                        )
                        failed_host.append(host_id)

                except MicrosoftIntuneBadRequestError as e:
                    result_value = False
                    siemplify.LOGGER.error(
                        f'Failed to create task for host ID "{host_id}". ' f"Error: {e}"
                    )
                    siemplify.LOGGER.exception(e)
                    bad_request_host.append(host_id)

            if successful_host:
                output_message += (
                    "\nSuccessfully started remote lock task for managed "
                    "devices with host ids in the Microsoft Intune: "
                    f"{', '.join(successful_host)}"
                )

            if failed_host:
                output_message += (
                    "\nThe following host ids were not found in the "
                    f"Microsoft Intune: {', '.join(failed_host)}"
                )
                result_value = False

            if bad_request_host:
                output_message += (
                    "\nAction wasn't able to create a task for the following "
                    "hosts in the Microsoft Intune: "
                    f"{', '.join(bad_request_host)}"
                )

            if not successful_host:
                output_message = (
                    "\nNo tasks were created on the provided hosts in "
                    "Microsoft Intune."
                )
                result_value = False

        else:  # Get using the host name
            siemplify.LOGGER.info(f"Found {len(host_names)} host names")

            multiple_intune_agents = []
            for host_name in host_names_entity:
                if not is_valid_host(devices, host_name, is_host_id=False):
                    siemplify.LOGGER.info(
                        f"Host name {host_name} doesn't belong to any of the "
                        "fetched devices. Skipping..."
                    )
                    failed_host.append(host_name)
                    continue

                if check_multiple_host_id_exists(devices, host_name):
                    siemplify.LOGGER.info(
                        f'Host name "{host_name}" has multiple agents'
                    )
                    multiple_intune_agents.append(host_name)

                siemplify.LOGGER.info(f"Getting host name's host ID")
                host_id = get_valid_host_id_by_name(devices, host_name)

                try:
                    siemplify.LOGGER.info(
                        "Creating remote lock task for managed device with "
                        f'host ID "{host_id}"'
                    )
                    manager.remote_lock_managed_device(host_id)
                    successful_host.append(host_name)

                except MicrosoftIntuneBadRequestError as e:
                    result_value = False
                    siemplify.LOGGER.error(
                        f'Failed to create task for host name "{host_name}". '
                        f"Error: {e}"
                    )
                    siemplify.LOGGER.exception(e)
                    bad_request_host.append(host_name)

            if successful_host:
                output_message += (
                    "\nSuccessfully started remote lock task for managed "
                    "devices with hostnames in the Microsoft Intune: "
                    f'{", ".join(successful_host)}'
                )

            if failed_host:
                output_message += (
                    "\nThe following hostnames were not found in the "
                    f"Microsoft Intune: {', '.join(failed_host)}"
                )
                result_value = False

            if multiple_intune_agents:
                output_message += (
                    "\nMultiple managed devices were found for the provided "
                    "hostnames in the Microsoft Intune: "
                    f"{', '.join(multiple_intune_agents)}.\n"
                    "Taking the managed device with the most recent "
                    "lastSyncDateTime"
                )

            if bad_request_host:
                output_message += (
                    "\nAction wasn't able to create a task for the following "
                    "hosts in the Microsoft Intune: "
                    f"{', '.join(bad_request_host)}"
                )

            if not successful_host:
                output_message = (
                    "\nNo tasks were created on the provided hosts in "
                    "Microsoft Intune."
                )
                result_value = False

    except Exception as e:
        output_message = (
            f'Error executing action "Remote Lock Managed Device". Reason: {e}'
        )
        result_value = False
        status = EXECUTION_STATE_FAILED

        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    if successful_host:
        result_value = True

    siemplify.LOGGER.info("---------------- Main - Finished ----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
