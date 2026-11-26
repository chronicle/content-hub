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
from typing import Any, Dict

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import construct_csv, extract_action_param, extract_configuration_param

from ..core.TenableIOManager import TenableIOManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from ..core.constants import (
    INTEGRATION_NAME,
    SCAN_ENDPOINTS_SCRIPT_NAME,
    DEFAULT_TIMEOUT,
    BAD_SCAN_STATUSES,
    COMPLETED_SCAN,
)
from ..core.TenableIOExceptions import WrongScanException
from ..core.UtilsManager import (
    get_entity_original_identifier,
    is_approaching_timeout,
    is_async_action_global_timeout_approaching,
    convert_list_to_comma_string,
    build_identifier_to_ip_map,
)


SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]
TABLE_NAME = "Scan Results"


def get_ip_address_for_entity(entity: Any, asset_map: Dict[str, str]) -> str | None:
    """
    Retrieves the IP address for a given entity using a pre-built asset map.

    Args:
        entity (Any): The entity object (HOSTNAME or ADDRESS).
        asset_map (Dict[str, str]): A lookup map of asset identifiers to IPs.

    Returns:
        str | None: The IP address of the entity if found, otherwise None.
    """
    if entity.entity_type == EntityTypes.ADDRESS:
        return entity.identifier

    if entity.entity_type == EntityTypes.HOSTNAME:
        normalized_entity = entity.identifier.lower()
        short_entity_name = normalized_entity.split(".")[0]

        # Direct lookup in the map (O(1) average)
        if normalized_entity in asset_map:
            return asset_map[normalized_entity]
        if short_entity_name in asset_map:
            return asset_map[short_entity_name]

    return None


def start_operation(
    siemplify, manager, suitable_entities, scan_name, policy_name, scanner_name, send_to
):
    result_value = {
        "scan_id": "",
        "json_results": {},
        "table_results": [],
        "completed": [],
        "not_found": [],
    }
    status = EXECUTION_STATE_INPROGRESS
    ip_addresses = []
    policy_uuid = next(
        (
            policy.uuid
            for policy in manager.list_policies()
            if policy.name == policy_name
        ),
        None,
    )
    scanner_uuid = (
        next(
            (
                scanner.uuid
                for scanner in manager.list_scanners()
                if scanner.name == scanner_name
            ),
            None,
        )
        if scanner_name
        else None
    )

    if not policy_uuid:
        raise Exception(
            f"Policy {policy_name} wasn't found in {INTEGRATION_NAME}. Please check the spelling."
        )

    if scanner_name and not scanner_uuid:
        raise Exception(
            f"Scanner {scanner_name} wasn't found in {INTEGRATION_NAME}. Please check the spelling."
        )

    try:
        asset_map = {}
        if any(
            entity.entity_type == EntityTypes.HOSTNAME for entity in suitable_entities
        ):
            siemplify.LOGGER.info(
                "Fetching all assets from Tenable.io to resolve Hostnames."
            )
            all_assets = manager.get_all_assets()
            asset_map = build_identifier_to_ip_map(all_assets)

        for entity in suitable_entities:
            ip_address = get_ip_address_for_entity(entity, asset_map)
            if not ip_address:
                result_value["not_found"].append(entity.identifier)
                siemplify.LOGGER.error(
                    f"Endpoint with {entity.identifier} value not found in {INTEGRATION_NAME}"
                )
            else:
                ip_addresses.append(ip_address)

        if ip_addresses:
            scan_id = manager.create_scan(
                policy_uuid=policy_uuid,
                scan_name=scan_name,
                ip_address=convert_list_to_comma_string(ip_addresses),
                emails=send_to,
                scanner_id=scanner_uuid,
            )

            manager.launch_scan(scan_id)

            scan_status = manager.check_scan_status(scan_id)

            if scan_status in BAD_SCAN_STATUSES:
                raise WrongScanException(scan_status)
            elif scan_status == COMPLETED_SCAN:
                scan_results = manager.get_scan_results(scan_id)
                result_value["completed"] = [
                    item.identifier
                    for item in suitable_entities
                    if item not in result_value["not_found"]
                ]
                siemplify.LOGGER.info(
                    f"Successfully executed scan on the following "
                    f"endpoints: {convert_list_to_comma_string(result_value['completed'])}"
                )
                result_value["json_results"] = scan_results.to_json()
                result_value["table_results"] = scan_results.to_csv()
            else:
                result_value["scan_id"] = scan_id
                output_message = f"Waiting for the scan to be completed. Current status: {scan_status}."
                result_value = json.dumps(result_value)
                return output_message, result_value, status

    except WrongScanException as err:
        raise Exception(f'The scan was "{err}"')

    output_message, result_value, status = finish_operation(
        siemplify=siemplify,
        suitable_entities=suitable_entities,
        result_data=result_value,
        timeout_approaching=False,
    )

    return output_message, result_value, status


def query_operation_status(
    siemplify, manager, action_start_time, result_data, suitable_entities
):
    timeout_approaching = False

    try:
        scan_id = result_data["scan_id"]
        scan_status = manager.check_scan_status(scan_id)
        result_data["scan_status"] = scan_status

        if is_async_action_global_timeout_approaching(
            siemplify, action_start_time
        ) or is_approaching_timeout(action_start_time, DEFAULT_TIMEOUT):
            siemplify.LOGGER.info("Timeout is approaching. Action will gracefully exit")
            timeout_approaching = True
        else:
            if scan_status in BAD_SCAN_STATUSES:
                raise WrongScanException(scan_status)
            elif scan_status == COMPLETED_SCAN:
                scan_results = manager.get_scan_results(scan_id)
                result_data["completed"] = [
                    item.identifier
                    for item in suitable_entities
                    if item not in result_data["not_found"]
                ]
                siemplify.LOGGER.info(
                    f"Successfully executed scan on the following "
                    f"endpoints: {convert_list_to_comma_string(result_data['completed'])}"
                )
                result_data["json_results"] = scan_results.to_json()
                result_data["table_results"] = scan_results.to_csv()
            else:
                result_data["scan_id"] = scan_id
                output_message = f"Waiting for the scan to be completed. Current status: {scan_status}."
                result_value = json.dumps(result_data)
                return output_message, result_value, EXECUTION_STATE_INPROGRESS
    except WrongScanException as err:
        raise Exception(f'The scan was "{err}"')

    output_message, result_value, status = finish_operation(
        siemplify=siemplify,
        suitable_entities=suitable_entities,
        result_data=result_data,
        timeout_approaching=timeout_approaching,
    )

    return output_message, result_value, status


def finish_operation(siemplify, suitable_entities, result_data, timeout_approaching):
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    not_found_entities = result_data["not_found"]
    successful_entities = []
    pending_entities = []
    output_message = ""

    for entity in suitable_entities:
        entity_identifier = get_entity_original_identifier(entity)
        if entity_identifier in result_data["completed"]:
            successful_entities.append(entity_identifier)
        elif entity_identifier not in not_found_entities:
            pending_entities.append(entity_identifier)

    if successful_entities:
        siemplify.result.add_result_json(result_data["json_results"])
        if result_data["table_results"]:
            siemplify.result.add_data_table(
                TABLE_NAME, construct_csv(result_data["table_results"])
            )
        output_message += (
            f"Successfully executed scan on the following endpoints: "
            f"{', '.join(successful_entities)}. \n"
        )
    if not_found_entities:
        output_message += (
            f"Action wasn’t able to find the following endpoints in {INTEGRATION_NAME}: "
            f"{', '.join(not_found_entities)} \n"
        )
    if timeout_approaching and pending_entities:
        raise Exception(
            f"Timeout was reached. Latest status: {result_data['scan_status']}"
        )
    if not successful_entities and not pending_entities:
        output_message = f"Provided endpoints were not found in {INTEGRATION_NAME}."
        result_value = False

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = SCAN_ENDPOINTS_SCRIPT_NAME
    mode = "Main" if is_first_run else "Scan Endpoints"
    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret Key",
        is_mandatory=True,
    )
    access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Access Key",
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
    scan_name = extract_action_param(
        siemplify, param_name="Scan Name", is_mandatory=True, print_value=True
    )
    policy_name = extract_action_param(
        siemplify, param_name="Policy Name", is_mandatory=True, print_value=True
    )
    scanner_name = extract_action_param(
        siemplify, param_name="Scanner Name", print_value=True
    )
    send_to = extract_action_param(
        siemplify, param_name="Send Report To", print_value=True
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    output_message = ""
    status = EXECUTION_STATE_INPROGRESS
    result_value = False
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        manager = TenableIOManager(
            api_root=api_root,
            secret_key=secret_key,
            access_key=access_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify,
                manager=manager,
                suitable_entities=suitable_entities,
                scan_name=scan_name,
                policy_name=policy_name,
                scanner_name=scanner_name,
                send_to=send_to,
            )
        if status == EXECUTION_STATE_INPROGRESS:
            result_data = (
                result_value
                if result_value
                else extract_action_param(
                    siemplify, param_name="additional_data", default_value="{}"
                )
            )
            output_message, result_value, status = query_operation_status(
                siemplify=siemplify,
                manager=manager,
                action_start_time=action_start_time,
                result_data=json.loads(result_data),
                suitable_entities=suitable_entities,
            )

    except Exception as err:
        output_message = (
            f"Error executing action {SCAN_ENDPOINTS_SCRIPT_NAME}. Reason: {err}"
        )
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
