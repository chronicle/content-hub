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

SCRIPT_NAME = "Panorama - CommitChanges"
PROVIDER_NAME = "Panorama"


def query_operation_status(siemplify, palo_alto_manager):
    job_information = json.loads(siemplify.extract_action_param("additional_data"))

    job_id = job_information.get("job_id")
    status = EXECUTION_STATE_INPROGRESS
    siemplify.LOGGER.info(f"Checking commit status of job id: {job_id}")
    commit_status, result, output_message = palo_alto_manager.check_commit_status(
        job_id=job_id
    )

    result_value = {"job_id": job_id}

    result_value = json.dumps(result_value)

    if commit_status == COMMIT_STATUS_FINISHED:

        if result == COMMIT_STATUS_FAILED:
            output_message = f"Action wasn't able to successfully commit changes. Details: {output_message}"
            result_value = False
            status = EXECUTION_STATE_COMPLETED
        else:
            output_message = "Successfully commited changes to Palo Alto Panorama"
            result_value = True
            status = EXECUTION_STATE_COMPLETED

    else:
        output_message = "Waiting for commit job to finish..."

    return output_message, result_value, status


def start_operation(siemplify, palo_alto_manager, only_my_changes):
    status = EXECUTION_STATE_INPROGRESS
    siemplify.LOGGER.info("Committing changes")
    job_id = palo_alto_manager.CommitChanges(only_my_changes=only_my_changes)

    if not job_id:
        output_message = "Action wasn't able to successfully commit changes."
        result_value = False
        status = EXECUTION_STATE_COMPLETED

    else:
        output_message = (
            "Changes commited to Palo Alto Panorama, checking the commit status..."
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
        only_my_changes = extract_action_param(
            siemplify,
            param_name="Only My Changes",
            default_value=True,
            input_type=bool,
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
                only_my_changes=only_my_changes,
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
