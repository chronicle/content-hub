from __future__ import annotations

import json
import sys

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import extract_action_param, extract_configuration_param

from ..core.constants import (
    COMPLETED_STATUS,
    DEFAULT_TIMEOUT,
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_NAME,
    SCAN_ASSETS_SCRIPT_NAME,
)
from ..core.OrcaSecurityExceptions import OrcaSecurityExistingProcessException
from ..core.OrcaSecurityManager import OrcaSecurityManager
from ..core.UtilsManager import (
    convert_comma_separated_to_list,
    convert_list_to_comma_string,
    is_approaching_process_timeout,
    is_async_action_global_timeout_approaching,
)


def start_scans(siemplify, manager, action_start_time, asset_ids):
    """
    Start scans for assets by id
    :param siemplify: {siemplify} Siemplify object
    :param manager: {OrcaSecurityManager} OrcaSecurityManager manager object
    :param action_start_time: {int} action start time in unix format
    :param asset_ids: {list} list of asset ids
    :return: {tuple} output_message, result, status
    """
    pending_assets, failed_assets = {}, []

    for asset_id in asset_ids:
        try:
            scan_status = manager.start_scan(asset_id)
            pending_assets[asset_id] = scan_status.scan_id
        except OrcaSecurityExistingProcessException as e:
            pending_assets[asset_id] = str(e)
        except Exception as e:
            failed_assets.append(asset_id)
            siemplify.LOGGER.error(f"An error occurred on asset with ID {asset_id}")
            siemplify.LOGGER.exception(e)

    return check_scans_statuses(
        siemplify,
        manager,
        action_start_time,
        pending_assets,
        failed_assets=failed_assets,
    )


def check_scans_statuses(
    siemplify,
    manager,
    action_start_time,
    pending_assets,
    successful_assets={},
    failed_assets=[],
):
    """
    Check scans statuses
    :param siemplify: {siemplify} Siemplify object
    :param manager: {OrcaSecurityManager} OrcaSecurityManager manager object
    :param action_start_time: {int} action start time in unix format
    :param pending_assets: {dict} dict of pending assets asset_id:scan_id pairs
    :param successful_assets: {dict} dict of successful assets asset_id:scan raw data pairs
    :param failed_assets: {list} list of failed asset ids
    :return: {tuple} output_message, result, status
    """
    batch_pending_assets = {}

    for asset_id, scan_id in pending_assets.items():
        if is_async_action_global_timeout_approaching(
            siemplify, action_start_time
        ) or is_approaching_process_timeout(action_start_time, DEFAULT_TIMEOUT):
            siemplify.LOGGER.info("Timeout is approaching. Action will gracefully exit")
            raise Exception(
                f"action ran into a timeout during execution. Pending assets: "
                f"{convert_list_to_comma_string(list(pending_assets.keys()))}. Please increase the timeout in IDE."
            )

        try:
            scan_status = manager.get_scan_status(scan_id)

            if scan_status.status == COMPLETED_STATUS:
                successful_assets[asset_id] = scan_status.raw_data
            else:
                batch_pending_assets[asset_id] = scan_id
        except Exception as e:
            failed_assets.append(asset_id)
            siemplify.LOGGER.error(f"An error occurred on asset with ID {asset_id}")
            siemplify.LOGGER.exception(e)

    if batch_pending_assets:
        result = json.dumps({
            "successful_assets": successful_assets,
            "pending_assets": batch_pending_assets,
            "failed_assets": failed_assets,
        })
        status = EXECUTION_STATE_INPROGRESS
        output_message = (
            f"Pending assets: {convert_list_to_comma_string(list(batch_pending_assets.keys()))}"
        )
    else:
        status = EXECUTION_STATE_COMPLETED
        result = True
        output_message = ""

        if successful_assets:
            siemplify.result.add_result_json(list(successful_assets.values()))
            output_message = (
                f"Successfully scanned the following assets using in {INTEGRATION_DISPLAY_NAME}: "
                f"{convert_list_to_comma_string(list(successful_assets.keys()))}"
            )

        if failed_assets:
            output_message += (
                f"\nAction wasn't able to scan the following assets in {INTEGRATION_DISPLAY_NAME}: "
                f"{convert_list_to_comma_string(failed_assets)}"
            )

        if not successful_assets:
            output_message = "None of the provided assets were scanned."
            result = False

    return output_message, result, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = SCAN_ASSETS_SCRIPT_NAME
    action_start_time = unix_now()
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
        is_mandatory=False,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    # action parameters
    asset_ids_string = extract_action_param(
        siemplify, param_name="Asset IDs", is_mandatory=True, print_value=True
    )
    asset_ids = convert_comma_separated_to_list(asset_ids_string)
    additional_data = json.loads(
        extract_action_param(siemplify=siemplify, param_name="additional_data", default_value="{}")
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = OrcaSecurityManager(
            api_root=api_root,
            api_key=api_key,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        if is_first_run:
            output_message, result, status = start_scans(
                siemplify, manager, action_start_time, asset_ids
            )
        else:
            output_message, result, status = check_scans_statuses(
                siemplify, manager, action_start_time, **additional_data
            )

    except Exception as e:
        result = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(f"General error performing action {SCAN_ASSETS_SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        output_message = f'Error executing action "{SCAN_ASSETS_SCRIPT_NAME}". Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
