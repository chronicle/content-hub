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
import sys

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from TIPCommon import construct_csv, extract_action_param, extract_configuration_param

from ..core.constants import DEFAULT_ITEMS, INTEGRATION_NAME, RUN_FORENSIC_SCAN_ACTION
from ..core.IllusiveNetworksExceptions import IncidentNotReadyException, RateLimitException
from ..core.IllusiveNetworksManager import IllusiveNetworksManager


def start_operation(siemplify, manager):
    """Function that initiates the forensic scan
    :param siemplify: SiemplifyAction object.
    :param manager: IllusiveNetworks manager object.
    """
    status = EXECUTION_STATE_INPROGRESS
    result_value = {}

    scope_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in {EntityTypes.HOSTNAME, EntityTypes.ADDRESS}
    ]
    event_ids = []
    successful_entities = []
    failed_entities = []

    if scope_entities:
        for entity in scope_entities:
            try:
                siemplify.LOGGER.error(
                    f"Started processing entity: {entity.identifier}"
                )
                event_id = manager.create_forensic_scan_request(entity.identifier)
                event_ids.append({event_id: entity.identifier})
                successful_entities.append(entity.identifier)

            except RateLimitException:
                raise

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed to process entity: {entity.identifier}. Reason: {e}"
                )
                failed_entities.append(entity.identifier)

        result_value = json.dumps({"event_ids": event_ids, "events_ready": []})

        output_message = "Started the forensic scan on the following endpoints: {}. Checking if forensic scan is ready...".format(
            ", ".join(list(successful_entities))
        )

    else:
        output_message = "No forensic information was found on the provided endpoints"
        result_value = False
        status = EXECUTION_STATE_COMPLETED
        return output_message, result_value, status

    if len(scope_entities) == len(failed_entities):
        output_message = "No forensic information was found on the provided endpoints"

    return output_message, result_value, status


def query_operation_status(
    siemplify,
    manager,
    include_sys_info,
    include_prefetch_files_info,
    include_add_remove,
    include_startup_info,
    include_running_info,
    include_user_assist_info,
    include_powershell_info,
    max_items_to_return,
):
    """Function that checks if the forensic scan is ready and fetch the results if ready
    :param siemplify: SiemplifyAction object.
    :param manager: IllusiveNetworks manager object.
    :param include_sys_info: True if System Info should be included in results
    :param include_prefetch_files_info: True if Prefetch Files Info should be included
    in results
    :param include_add_remove: True if Add Remove Processes should be included
    in results
    :param include_startup_info: True if Startup Processes should be included in results
    :param include_running_info: True if Running Processes should be included in results
    :param include_user_assist_info: True if User Assist should be included in results
    :param include_powershell_info: True if Powershell Info should be included
    in results
    :param max_items_to_return: Max number of results in the output
    """
    event_ids_all = json.loads(siemplify.extract_action_param("additional_data"))
    event_ids = event_ids_all.get("event_ids")
    events_ready = event_ids_all.get("events_ready")

    events_to_check_again = []
    events_ready_incidents = []
    successfully_fetched_forensics = []
    failed_fetched_forensics = []
    output_message = ""

    json_results = {}

    if event_ids:
        # If we still have some events that are not ready we need to get the status,
        # until the last event is ready
        for event_data in event_ids:
            event_id = next(iter(event_data.keys()))
            try:
                manager.get_incident_id(event_id=event_id)
                events_ready_incidents.append(event_data)
                siemplify.LOGGER.error(
                    f"Incident for event with ID {event_id} is ready."
                )
            except RateLimitException:
                raise
            except IncidentNotReadyException:
                events_to_check_again.append(event_data)
                siemplify.LOGGER.error(
                    f"Incident for event with ID {event_id} is not ready yet."
                )

        result_value = json.dumps(
            {"event_ids": events_to_check_again, "events_ready": events_ready_incidents}
        )
        status = EXECUTION_STATE_INPROGRESS
        output_message += "Created events {}. Waiting for forensic data to become available...".format(
            ", ".join([next(iter(entity.keys())) for entity in events_to_check_again])
        )

    elif events_ready:

        scope_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type in {EntityTypes.HOSTNAME, EntityTypes.ADDRESS}
        ]
        suitable_entities = {entity.identifier: entity for entity in scope_entities}

        # when all of the events are ready we will fetch results
        entities_to_update = []

        for event_ready in events_ready:
            event_ready_key = next(iter(event_ready.keys()))
            entity = suitable_entities[event_ready.get(event_ready_key)]

            try:

                forensic_data = manager.get_forensic_data(
                    event_id=event_ready_key,
                    include_sys_info=include_sys_info,
                    include_prefetch_files_info=include_prefetch_files_info,
                    include_add_remove=include_add_remove,
                    include_startup_info=include_startup_info,
                    include_running_info=include_running_info,
                    include_user_assist_info=include_user_assist_info,
                    include_powershell_info=include_powershell_info,
                )
                entity_json = {}

                if forensic_data and include_sys_info:
                    entity_json["host_info"] = forensic_data.get("host_info").raw_data
                    siemplify.result.add_entity_table(
                        f"{event_ready.get(event_ready_key)}",
                        construct_csv(forensic_data.get("host_info").to_table()),
                    )

                    entity.is_enriched = True
                    entity.additional_properties.update(
                        forensic_data.get("host_info").as_enrichment_data()
                    )
                    entities_to_update.append(entity)

                if (
                    forensic_data
                    and include_prefetch_files_info
                    and forensic_data.get("prefetch_info")
                ):

                    prefetch_data = forensic_data.get("prefetch_info")
                    prefetch_table = []
                    prefetch_json = []

                    for prefetch in prefetch_data:
                        prefetch_table.append(prefetch.to_table())
                        prefetch_json.append(prefetch.raw_data)

                    if max_items_to_return:
                        prefetch_table = prefetch_table[:max_items_to_return]
                        prefetch_json = prefetch_json[:max_items_to_return]

                    entity_json["prefetch_info"] = prefetch_json

                    siemplify.result.add_data_table(
                        f"{event_ready.get(event_ready_key)}: "
                        f"Prefetch Files Information",
                        construct_csv(prefetch_table),
                    )

                if (
                    forensic_data
                    and include_add_remove
                    and forensic_data.get("include_add_remove")
                ):

                    add_remove_data = forensic_data.get("include_add_remove")
                    add_remove_table = []
                    add_remove_json = []

                    for add_remove in add_remove_data:
                        add_remove_table.append(add_remove.to_table())
                        add_remove_json.append(add_remove.raw_data)

                    if max_items_to_return:
                        add_remove_table = add_remove_table[:max_items_to_return]
                        add_remove_json = add_remove_json[:max_items_to_return]

                    entity_json["installed_programs_info"] = add_remove_json
                    siemplify.result.add_data_table(
                        f"{event_ready.get(event_ready_key)}: "
                        f"Add-Remove Programs Information",
                        construct_csv(add_remove_table),
                    )

                if (
                    forensic_data
                    and include_startup_info
                    and forensic_data.get("include_startup_info")
                ):

                    startup_data = forensic_data.get("include_startup_info")
                    startup_table = []
                    startup_json = []

                    for startup in startup_data:
                        startup_table.append(startup.to_table())
                        startup_json.append(startup.raw_data)

                    if max_items_to_return:
                        startup_table = startup_table[:max_items_to_return]
                        startup_json = startup_json[:max_items_to_return]

                    entity_json["startup_processes"] = startup_json
                    siemplify.result.add_data_table(
                        f"{event_ready.get(event_ready_key)}: Startup Processes",
                        construct_csv(startup_table),
                    )

                if (
                    forensic_data
                    and include_running_info
                    and forensic_data.get("include_running_info")
                ):

                    running_info_data = forensic_data.get("include_running_info")
                    running_info_table = []
                    running_info_json = []

                    for startup in running_info_data:
                        running_info_table.append(startup.to_table())
                        running_info_json.append(startup.raw_data)

                    if max_items_to_return:
                        running_info_table = running_info_table[:max_items_to_return]
                        running_info_json = running_info_json[:max_items_to_return]

                    entity_json["running_processes"] = running_info_json
                    siemplify.result.add_data_table(
                        f"{event_ready.get(event_ready_key)}: Running Processes",
                        construct_csv(running_info_table),
                    )

                if (
                    forensic_data
                    and include_user_assist_info
                    and forensic_data.get("include_user_assist_info")
                ):

                    user_assist_info_data = forensic_data.get(
                        "include_user_assist_info"
                    )
                    user_assist_info_table = []
                    user_assist_info_json = []

                    for user_assist_info in user_assist_info_data:
                        user_assist_info_table.append(user_assist_info.to_table())
                        user_assist_info_json.append(user_assist_info.raw_data)

                    if max_items_to_return:
                        user_assist_info_table = user_assist_info_table[
                            :max_items_to_return
                        ]
                        user_assist_info_json = user_assist_info_json[
                            :max_items_to_return
                        ]

                    entity_json["user_assist_info"] = user_assist_info_json
                    siemplify.result.add_data_table(
                        f"{event_ready.get(event_ready_key)}: "
                        f"User-Assist Programs Information",
                        construct_csv(user_assist_info_table),
                    )

                if (
                    forensic_data
                    and include_powershell_info
                    and forensic_data.get("include_powershell_info")
                ):

                    powershell_data = forensic_data.get("include_powershell_info")
                    powershell_table = []
                    powershell_json = []

                    for powershell in powershell_data:
                        powershell_table.append(powershell.to_table())
                        powershell_json.append(powershell.raw_data)

                    if max_items_to_return:
                        powershell_table = powershell_table[:max_items_to_return]
                        powershell_json = powershell_json[:max_items_to_return]

                    entity_json["powershell_history"] = powershell_json
                    siemplify.result.add_data_table(
                        f"{event_ready.get(event_ready_key)}: Powershell History",
                        construct_csv(powershell_table),
                    )

                if entity_json:
                    json_results[event_ready.get(event_ready_key)] = entity_json
                    successfully_fetched_forensics.append(
                        event_ready.get(event_ready_key)
                    )
                else:
                    failed_fetched_forensics.append(event_ready.get(event_ready_key))
            except RateLimitException:
                raise

            except Exception as e:
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)
                failed_fetched_forensics.append(event_ready.get(event_ready_key))
                continue

        if successfully_fetched_forensics:

            if entities_to_update:
                siemplify.update_entities(entities_to_update)
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            output_message += "Successfully ran forensic scan on the following endpoints in Illusive Networks: {}.".format(
                ", ".join(list(successfully_fetched_forensics))
            )
            status = EXECUTION_STATE_COMPLETED
            result_value = True

        if failed_fetched_forensics:
            status = EXECUTION_STATE_COMPLETED
            result_value = True
            output_message += "\nAction wasn't able to get any information from forensic scan on the following endpoints: {}.".format(
                ", ".join(list(failed_fetched_forensics))
            )

        if failed_fetched_forensics and not successfully_fetched_forensics:
            output_message = (
                "No forensic information was found on the provided endpoints"
            )
            result_value = False
            status = EXECUTION_STATE_COMPLETED

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = RUN_FORENSIC_SCAN_ACTION
    mode = "Main" if is_first_run else "Get Forensic Data"
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
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File",
        is_mandatory=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
    )

    include_sys_info = extract_action_param(
        siemplify,
        param_name="Include System Information",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
    )
    include_prefetch_files_info = extract_action_param(
        siemplify,
        param_name="Include Prefetch Files Information",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
    )
    include_add_remove = extract_action_param(
        siemplify,
        param_name="Include Add-Remove Programs Information",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
    )
    include_startup_info = extract_action_param(
        siemplify,
        param_name="Include Startup Processes Information",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
    )
    include_running_info = extract_action_param(
        siemplify,
        param_name="Include Running Processes Information",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
    )
    include_user_assist_info = extract_action_param(
        siemplify,
        param_name="Include User-Assist Programs Information",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
    )
    include_powershell_info = extract_action_param(
        siemplify,
        param_name="Include Powershell History Information",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")
    output_message = ""
    try:
        max_items_to_return = extract_action_param(
            siemplify,
            param_name="Max Items To Return",
            is_mandatory=False,
            print_value=True,
            input_type=int,
        )

        if (
            include_sys_info
            or include_prefetch_files_info
            or include_add_remove
            or include_startup_info
            or include_running_info
            or include_user_assist_info
            or include_user_assist_info
            or include_powershell_info
        ):

            if max_items_to_return and max_items_to_return < 0:
                siemplify.LOGGER.error(
                    f'Given value for "Max Items To Return" has to be non negative. '
                    f'Using default value of {DEFAULT_ITEMS}'
                )
                max_items_to_return = DEFAULT_ITEMS

            illusivenetworks_manager = IllusiveNetworksManager(
                api_root=api_root,
                api_key=api_key,
                ca_certificate=ca_certificate,
                verify_ssl=verify_ssl,
                siemplify_logger=siemplify.LOGGER,
            )

            if is_first_run:
                illusivenetworks_manager.test_connectivity()
                output_message, result_value, status = start_operation(
                    siemplify=siemplify, manager=illusivenetworks_manager
                )

            else:
                output_message, result_value, status = query_operation_status(
                    siemplify=siemplify,
                    manager=illusivenetworks_manager,
                    include_sys_info=include_sys_info,
                    include_prefetch_files_info=include_prefetch_files_info,
                    include_add_remove=include_add_remove,
                    include_startup_info=include_startup_info,
                    include_running_info=include_running_info,
                    include_user_assist_info=include_user_assist_info,
                    include_powershell_info=include_powershell_info,
                    max_items_to_return=max_items_to_return,
                )
        else:
            output_message += (f'Error executing action {RUN_FORENSIC_SCAN_ACTION}. '
                               f'Reason: You need to enable at least one of the '
                               f'"Include ..." parameters.')
            siemplify.LOGGER.error(output_message)
            status = EXECUTION_STATE_FAILED
            result_value = False

    except Exception as e:
        output_message += (
            f"Error executing action {RUN_FORENSIC_SCAN_ACTION}. Reason {e}."
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  "
        f"result_value: {result_value}\n  "
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
