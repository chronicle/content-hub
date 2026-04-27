from __future__ import annotations

import copy
import json
import sys
from time import sleep
from typing import Any

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyUtils import unix_now
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)

from ..core.CybereasonManager import CybereasonManager
from ..core.constants import (
    INTEGRATION_NAME,
    REMEDIEATE_MELOP_SCRIPT_NAME,
    LIST_MALOP_REMEDIATIONS_SCRIPT_NAME,
    REMEDEIATION_SUCCESS,
    RESPONSE_KEY_CHECK,
)
from ..core import exceptions
from ..core.utils import (
    convert_comma_separated_to_list,
    merge_result_json_data,
    search_unique_ids_in_malop,
    update_ids_get_status_result_data,
)


def start_operation(
    siemplify: SiemplifyAction,
    manager: CybereasonManager,
    malop_id: str,
    unique_ids: str,
    action_start_time: int,
) -> tuple[str, bool | dict[str, Any], int]:
    """This function calls while is_first_run is true for Action Script.

    It gets the remediations details for the malop provided in parameter and
    searches the unique ids, if found it calls the remediation on the found
    unique ids and gets the status for further async iteration.

    Step 1:
        It calls the manager method "get_malop_suspicious_details" to get the
        possible remedations with unique IDs.
    Step 2:
        It searches the unique IDs provided in parameter in the malop response
        of Step 1.
    Step 3:
        It initiates remediation action on found remedations wrt to unique
        ids provided in parameter.
    Step 4:
        It register the response from Step 3 and get the remediationId from it
        and calls manager mathod "get_remediation_status" to get the status.
        NOTE: For block file remediation action, It just calls the remediation
        action but won't check the status in async iteration. It just register
        reponse as success in the first run.
    Args:
        siemplify (SiemplifyAction): SiemplifyAction object.
        manager (CybereasonManager): CybereasonManager object.
        malop_id (str): Action parameter "Malop ID".
        unique_ids (str): Action parameter "Remediation Unique IDs".
        action_start_time (int): Script start time.

    Raises:
        CybereasonMalopProcessError: If no process data found in
        "get_malop_suspicious_details" method response for Malop ID.

        CybereasonfilesDataError: If any parameter "Remediation Unique IDs"
        provided files not found in the Malop Response.

    Returns:
        tuple[str, bool | dict, int]: output_message, result, status
    """
    status = EXECUTION_STATE_INPROGRESS
    timeout_approaching = False
    result = []
    tracked = []
    result_data = {
        "target_ids": [],
        "failed_ids": [],
        "successful_ids": {},
        "unsuccessful_ids": {},
        "in_progress": [],
    }

    try:
        unique_ids_list = convert_comma_separated_to_list(unique_ids)
        malop_value = manager.get_malop_suspicious_details(malop_id=malop_id)
        if not malop_value:
            raise exceptions.CybereasonMalopProcessError(
                f"no remediation actions were found for malop {malop_id}."
                "Please verify that correct malop was provided."
            )

        found_unique_ids_data, not_found_ids = search_unique_ids_in_malop(
            malop_value, unique_ids_list
        )

        if found_unique_ids_data:
            found_ids = [uid.unique_id for uid in found_unique_ids_data]
            siemplify.LOGGER.info(
                f'Unique IDs "{", ".join(found_ids)}" found in ' "Malop details."
            )

        if not_found_ids:
            siemplify.LOGGER.info(
                f'Unique IDs "{", ".join(not_found_ids)}" not found in '
                "Malop details."
            )
            raise exceptions.CybereasonUniqueIdError(
                f'remediation actions: "{", ".join(not_found_ids)}" weren\'t '
                f"found for malop {malop_id}. Please check the spelling or run "
                f'the action "{LIST_MALOP_REMEDIATIONS_SCRIPT_NAME}" to verify '
                "that the input is correct."
            )

        for data_object in found_unique_ids_data:
            unique_id = data_object.unique_id
            result_data["target_ids"].append(unique_id)
            remediate_malop = manager.remediate_melop(data_object.to_json())

            if remediate_malop and not data_object.is_block_action:

                if remediate_malop.is_success:
                    result.append(remediate_malop)
                    get_status = manager.get_remediation_status(
                        malop_id, remediate_malop.remediation_id
                    )
                    tracked.append(
                        dict(
                            unique_id=unique_id,
                            remediation_result=get_status,
                            malop_id=malop_id,
                            process_name=data_object.target_name,
                            action=data_object.remediation_type,
                        )
                    )

                else:
                    result_data["failed_ids"].append(unique_id)
                    siemplify.LOGGER.error(
                        f"Remediate action failed for unique_id: {unique_id}"
                    )
                    continue

            else:
                remediate_malop.to_json().update(
                    {
                        "target_name": data_object.target_name,
                        "remediation_action": data_object.remediation_type,
                    }
                )
                result_data["successful_ids"][unique_id] = [remediate_malop.to_json()]
                siemplify.LOGGER.info(
                    f"Remediation action has been successful for {unique_id}"
                )
            sleep(2)

        if not tracked:
            is_timeout = is_async_action_global_timeout_approaching(
                siemplify, action_start_time
            )

            if is_timeout:
                siemplify.LOGGER.info(
                    "Timeout is approaching. Action will gracefully exit"
                )
                timeout_approaching = True

            output_message, result_data, status = finish_operation(
                siemplify=siemplify,
                malop_id=malop_id,
                result_data=result_data,
                timeout_approaching=timeout_approaching,
            )

            return output_message, result_data, status

        result_data["in_progress"].extend(tracked)
        result_data = json.dumps(result_data)
        output_message = (
            "Pending remediations: "
            f'{" ".join([item["unique_id"] for item in tracked])}'
        )

    except Exception as error:
        output_message = (
            f'Error executing action "{REMEDIEATE_MELOP_SCRIPT_NAME}". '
            f"Reason: {error}"
        )
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        result_data = False

    return output_message, result_data, status


def query_operation_status(
    siemplify: SiemplifyAction,
    manager: CybereasonManager,
    malop_id: str,
    action_start_time: int,
    result_data: dict[str, Any],
) -> tuple[str, bool | dict[str, Any], int]:
    """This function runs async flow for "in_progress" ids in result_data.

    Step 1:
        It checks the timeout is approaching in case. if found and ids are
        in_progress, it failes the action with required log.
    Step 2:
        It checks the unique ID in "in_progress" key in result data
        and checks each remediation action status on Cybereason, it keeps
        checking until all remediation processed successfully with SUCCESS or
        FAILED/ABORTED response from Cybereason.

    Args:
        siemplify (SiemplifyAction): SiemplifyAction object.
        manager (CybereasonManager): CybereasonManager object.
        malop_id: Action parameter "Malop ID"
        action_start_time (int): Script start time.
        result_data (dict[str, Any]): Dict object from parameter additional_data

    Returns:
        tuple[str, bool | dict[str, Any], int]: output_message, result, status
    """
    successful_ids = result_data["successful_ids"]
    unsuccessful_ids = result_data["unsuccessful_ids"]
    timeout_approaching = False
    is_timeout = is_async_action_global_timeout_approaching(
        siemplify, action_start_time
    )
    if is_timeout:
        siemplify.LOGGER.info("Timeout is approaching. Action will gracefully exit")
        timeout_approaching = True

    else:
        in_progress_items = result_data["in_progress"]
        in_progress_copy = copy.deepcopy(in_progress_items)

        for item in in_progress_items[:]:
            unique_id = item["unique_id"]
            process_name = item["process_name"]
            remediation_id = item["remediation_result"]["remediationId"]

            get_status = manager.get_remediation_status(malop_id, remediation_id)

            if not successful_ids.get(unique_id):
                successful_ids[unique_id] = []

            if not unsuccessful_ids.get(unique_id):
                unsuccessful_ids[unique_id] = []

            if get_status.get(RESPONSE_KEY_CHECK) is not None:
                get_status = update_ids_get_status_result_data(
                    result_data=get_status, process_name=process_name
                )
                if get_status.get("final_status") == REMEDEIATION_SUCCESS:
                    result_data["successful_ids"][unique_id].append(get_status)

                else:
                    result_data["unsuccessful_ids"][unique_id].append(get_status)
                in_progress_items.remove(item)

        for item in in_progress_copy:
            unique_id = item["unique_id"]

            if not successful_ids.get(unique_id):
                del successful_ids[unique_id]

            if not unsuccessful_ids.get(unique_id):
                del unsuccessful_ids[unique_id]

        if in_progress_items:
            output_message = (
                f"Pending remediations: "
                f'{" ".join([item["unique_id"] for item in in_progress_items])}'
            )
            siemplify.LOGGER.info(output_message)
            result_value = json.dumps(result_data)

            return output_message, result_value, EXECUTION_STATE_INPROGRESS

    output_message, result_value, status = finish_operation(
        siemplify=siemplify,
        malop_id=malop_id,
        result_data=result_data,
        timeout_approaching=timeout_approaching,
    )

    return output_message, result_value, status


def finish_operation(
    siemplify: SiemplifyAction,
    malop_id: str,
    result_data: dict[str, Any],
    timeout_approaching: bool,
) -> tuple[str, bool | dict, int]:
    """This function filter the successful and unsuccessful unique ids.

    It filter the unique ID wrt to keys defined in result_data parameter.
    In case of script timeout approaching and entities found in in_progress
    it fails the action with result values false and log.

    Args:
        siemplify (SiemplifyAction): SiemplifyAction object.
        malop_id: Action Parameter "Malop ID".
        result_data (dict): Dict object from parameter for all entites.
            example: {
                    "target_entities": [],
                    "failed_entities": [],
                    "successful_entities": {},
                    "unsuccessful_entities": {},
                    "in_progress": []
            }
        timeout_approaching (bool): boolean value for timeout approaching.

    Returns:
        tuple[str, bool | dict, int]: output_message, result, status
    """
    output_message = ""
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    successful_ids = []
    unsuccessful_ids = []
    in_progress_ids = []
    successful_ids_data = result_data["successful_ids"]
    unsuccessful_ids_data = result_data["unsuccessful_ids"]
    final_ids_data = []

    for unique_id in result_data["target_ids"]:
        if unique_id in successful_ids_data:
            successful_ids.append(unique_id)
        elif unique_id in unsuccessful_ids_data:
            unsuccessful_ids.append(unique_id)
        else:
            in_progress_ids.append(unique_id)

    successful_message = (
        f"Successfully executed the following remediation actions "
        f'for malop "{malop_id}" in Cybereason: \n'
        f'{", ".join(list(set(successful_ids)))}\n'
    )

    unsuccessful_message = (
        f"Action wasn't able to execute the following remediation actions "
        f'for malop "{malop_id}" in Cybereason: \n'
        f'{", ".join(list(set(unsuccessful_ids)))}\n'
    )

    if successful_ids and unsuccessful_ids:
        output_message += successful_message + unsuccessful_message

    elif successful_ids and not unsuccessful_ids:
        output_message += successful_message

    elif not successful_message and unsuccessful_message:
        output_message += unsuccessful_message

    else:
        output_message += (
            "No remediation actions were executed for malop "
            f"{malop_id} in Cybereason."
        )

    failed_ids = result_data["failed_ids"]
    if failed_ids:
        log_message = (
            f"Action wasn't able to execute remediation action on the "
            "following unique_ids in Cybereason: \n"
            f'{", ".join(id for id in failed_ids)}\n'
        )
        output_message += log_message

    siemplify.LOGGER.info(output_message)

    merge_data = merge_result_json_data(successful_ids_data, unsuccessful_ids_data)

    for value in merge_data.values():
        final_ids_data.extend(value)

    siemplify.result.add_result_json(json_data=final_ids_data)

    if timeout_approaching and in_progress_ids:
        error_message = (
            f"Action ran into a timeout during execution. Pending remediations:"
            f' {", ".join(id for id in in_progress_ids)}\n'
            f"Please increase the timeout in IDE."
        )

        output_message = (
            f"Error executing action {REMEDIEATE_MELOP_SCRIPT_NAME}."
            f" Reason: {error_message}"
        )
        siemplify.LOGGER.error(output_message)
        result_value = False
        status = EXECUTION_STATE_FAILED

        return output_message, result_value, status

    if unsuccessful_ids:
        result_value = False

    return output_message, result_value, status


@output_handler
def main(is_first_run=True):
    siemplify = SiemplifyAction()
    siemplify.script_name = REMEDIEATE_MELOP_SCRIPT_NAME
    action_start_time = unix_now()

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate Base64",
    )
    malop_id = extract_action_param(
        siemplify,
        param_name="Malop ID",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )
    unique_ids = extract_action_param(
        siemplify,
        param_name="Remediation Unique IDs",
        is_mandatory=False,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        manager = CybereasonManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            ca_certificate_b64=ca_certificate,
            logger=siemplify.LOGGER,
            force_check_connectivity=True,
        )
        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify=siemplify,
                manager=manager,
                malop_id=malop_id,
                unique_ids=unique_ids,
                action_start_time=action_start_time,
            )

        else:
            result_data_json = extract_action_param(
                siemplify=siemplify,
                param_name="additional_data",
                default_value="{}",
                is_mandatory=True,
            )
            result_data = json.loads(result_data_json)

            output_message, result_value, status = query_operation_status(
                siemplify=siemplify,
                manager=manager,
                malop_id=malop_id,
                action_start_time=action_start_time,
                result_data=result_data,
            )

    except Exception as e:
        output_message = (
            f'Error executing action "{REMEDIEATE_MELOP_SCRIPT_NAME}". ' f"Reason: {e}"
        )
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}"
        f"\n  is_success: {result_value}"
        f"\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


def is_async_action_global_timeout_approaching(siemplify, start_time):
    return siemplify.execution_deadline_unix_time_ms - start_time < 1 * 60 * 1000


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
