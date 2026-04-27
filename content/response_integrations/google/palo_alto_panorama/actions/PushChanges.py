# coding=utf-8
from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.PanoramaManager import PanoramaManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
import sys
import json
from ..core.PanoramaConstants import COMMIT_STATUS_FAILED, COMMIT_STATUS_FINISHED

SCRIPT_NAME = "Panorama - PushChanges"
PROVIDER_NAME = "Panorama"


def query_operation_status(siemplify, palo_alto_manager):
    job_information = json.loads(siemplify.extract_action_param("additional_data"))
    job_id = job_information.get("job_id")
    status = EXECUTION_STATE_INPROGRESS

    siemplify.LOGGER.info(f"Checking commit status of job: {job_id}")
    commit_status, result, output_message = palo_alto_manager.check_commit_status(
        job_id=job_id
    )

    result_value = {"job_id": job_id}

    result_value = json.dumps(result_value)

    if commit_status == COMMIT_STATUS_FINISHED:
        if result == COMMIT_STATUS_FAILED:
            output_message = f"Action wasn't able to successfully push changes. Details: {output_message}"
            result_value = False
            status = EXECUTION_STATE_COMPLETED

        else:
            output_message = "Successfully pushed changes to Palo Alto Panorama."
            result_value = True
            status = EXECUTION_STATE_COMPLETED

    else:
        output_message = "Waiting for push job to finish..."

    return output_message, result_value, status


def start_operation(siemplify, palo_alto_manager, device_group):
    status = EXECUTION_STATE_INPROGRESS

    siemplify.LOGGER.info(
        f"Pushing changes to device group {device_group} in Palo Alto Panorama"
    )
    job_id = palo_alto_manager.PushChanges(device_group=device_group)

    if not job_id:
        output_message = (
            "Action wasn't able to successfully push changes to Palo Alto Panorama."
        )
        result_value = False
        status = EXECUTION_STATE_COMPLETED

    else:
        output_message = (
            "Changes pushed to Palo Alto Panorama, checking the push status..."
        )
        result_value = {"job_id": job_id}

        result_value = json.dumps(result_value)

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    mode = "Main" if is_first_run else "Check changes"

    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    # Configuration.
    server_address = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Api Root"
    )
    username = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Username"
    )
    password = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="Password"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True

    try:
        device_group = extract_action_param(
            siemplify,
            param_name="Device Group Name",
            is_mandatory=True,
            print_value=True,
        )

        palo_alto_manager = PanoramaManager(
            server_address, username, password, verify_ssl, siemplify.run_folder
        )

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify=siemplify,
                palo_alto_manager=palo_alto_manager,
                device_group=device_group,
            )
        else:
            output_message, result_value, status = query_operation_status(
                siemplify=siemplify, palo_alto_manager=palo_alto_manager
            )

    except Exception as e:
        output_message = f"Error executing action {SCRIPT_NAME}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
