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
import os
import pathlib
import sys
import uuid
import zipfile

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import (
    extract_action_param,
    extract_configuration_param,
)

from ..core.FireEyeHXManager import (
    FireEyeHXManager,
    FireEyeHXManagerError,
    FireEyeHXNotFoundError,
)

INTEGRATION_NAME = "FireEyeHX"
SCRIPT_NAME = "Get File"
SUPPORTED_ENTITIES = [EntityTypes.HOSTNAME, EntityTypes.ADDRESS]
MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def extract_zip_metadata(temp_filename, zip_passphrase=None, siemplify=None):
    """Safely extract manifest.json metadata from zip package."""
    zip_metadata = {}
    if pathlib.Path(temp_filename).exists():
        try:
            with zipfile.ZipFile(temp_filename) as zf:
                if zip_passphrase:
                    zf.setpassword(zip_passphrase.encode("utf-8"))
                for filename in zf.namelist():
                    if "manifest.json" in filename:
                        try:
                            zip_metadata = json.loads(zf.read(filename).decode("utf-8"))
                            break
                        except Exception as manifest_err:
                            if siemplify:
                                siemplify.LOGGER.exception(f"Error reading manifest: {manifest_err}")
        except Exception as e:
            if siemplify:
                siemplify.LOGGER.exception(f"Error extracting zip metadata: {e}")
    return zip_metadata


def split_file_path(file_path):
    """Split a file path into directory and file name, supporting Windows and Unix paths."""
    file_dir, file_name = "", file_path
    if "\\" in file_path:
        file_dir, file_name = file_path.rsplit("\\", 1)
    elif "/" in file_path:
        file_dir, file_name = file_path.rsplit("/", 1)
    return file_name, file_dir


def start_file_acquisition(
    siemplify, hx_manager, agent_id_param, file_path_param, use_api_mode_param, external_id_param
):
    """Start the file acquisition process."""
    file_name, file_path = split_file_path(file_path_param)

    agent_id = hx_manager.resolve_agent_id_from_entities(
        target_entities=siemplify.target_entities,
        agent_id_param=agent_id_param,
    )

    if not agent_id:
        output_message = "No valid agent_id was supplied or found across target entities."
        siemplify.LOGGER.error(output_message)
        return output_message, "false", EXECUTION_STATE_FAILED

    siemplify.LOGGER.info(f"Target Agent ID: {agent_id}")

    try:
        data = hx_manager.create_file_acquisition(
            agent_id=agent_id,
            file_path=file_path,
            file_name=file_name,
            external_id=external_id_param,
            use_api_mode=use_api_mode_param,
            comment="Acquiring file through Chronicle SOAR",
        )
    except FireEyeHXNotFoundError as not_found_err:
        siemplify.LOGGER.exception(str(not_found_err))
        return str(not_found_err), "false", EXECUTION_STATE_FAILED
    except FireEyeHXManagerError as mgr_err:
        siemplify.LOGGER.exception(str(mgr_err))
        return str(mgr_err), "false", EXECUTION_STATE_FAILED
    except Exception as e:
        siemplify.LOGGER.exception(f"Unexpected error creating file acquisition: {e}")
        return f"Unable to create file acquisition: {e}", "false", EXECUTION_STATE_FAILED

    acquisition_id = data.get("_id") or data.get("id") or data.get("acquisition_id")
    if not acquisition_id:
        output_message = f"Failed to acquire file: No acquisition ID in response data: {data}"
        siemplify.LOGGER.error(output_message)
        return output_message, "false", EXECUTION_STATE_FAILED

    status = EXECUTION_STATE_INPROGRESS
    result_value = json.dumps({
        "acquisition_id": acquisition_id,
        "agent_id": agent_id,
        "file_name": file_name,
        "file_path": file_path,
    })
    output_message = f"File acquisition {acquisition_id} requested for file '{file_name}' on agent {agent_id}."
    return output_message, result_value, status


def poll_file_acquisition(siemplify, hx_manager, acq_context):
    """Poll the file acquisition status until complete or failed."""
    acquisition_id = acq_context.get("acquisition_id")
    agent_id = acq_context.get("agent_id")
    file_name = acq_context.get("file_name")

    siemplify.LOGGER.info(f"Polling status for acquisition ID: {acquisition_id}")

    try:
        data = hx_manager.get_file_acquisition_by_id(acquisition_id)
    except Exception as e:
        output_message = f"Failed fetching status for acquisition {acquisition_id}: {e}"
        siemplify.LOGGER.exception(output_message)
        return output_message, "false", EXECUTION_STATE_FAILED

    current_state = data.get("state")
    siemplify.LOGGER.info(f"Acquisition state is: {current_state}")

    if current_state == "COMPLETE":
        zip_file_size = int(data.get("zip_file_size", 0) or 0)
        if zip_file_size > MAX_FILE_SIZE_BYTES:
            output_message = (
                f"The acquired zip size ({zip_file_size} bytes) exceeds the max allowed limit of {MAX_FILE_SIZE_MB}MB."
            )
            siemplify.LOGGER.error(output_message)
            try:
                hx_manager.delete_file_acquisition(acquisition_id)
            except Exception as del_err:
                siemplify.LOGGER.exception(f"Failed deleting oversized acquisition: {del_err}")
            return output_message, "false", EXECUTION_STATE_FAILED

        execution_folder = (
            getattr(siemplify, "run_folder", None) or getattr(siemplify, "execution_folder", None) or "/tmp"
        )
        temp_filename = os.path.join(execution_folder, f"{uuid.uuid4()}.zip")

        try:
            hx_manager.download_file_acquisition(acquisition_id, temp_filename)
            siemplify.LOGGER.info(f"Downloaded acquisition zip to: {temp_filename}")
        except Exception as dl_err:
            output_message = f"Failed to download acquisition zip for ID {acquisition_id}: {dl_err}"
            siemplify.LOGGER.exception(output_message)
            return output_message, "false", EXECUTION_STATE_FAILED

        zip_passphrase = data.get("zip_passphrase")
        zip_metadata = extract_zip_metadata(temp_filename, zip_passphrase, siemplify)

        json_result = data.copy()
        if zip_metadata:
            json_result.update(zip_metadata)

        json_result["download_path"] = temp_filename

        siemplify.result.add_result_json(json_result)
        output_message = f"File '{file_name}' was successfully acquired from host {agent_id}."
        return output_message, "true", EXECUTION_STATE_COMPLETED

    if current_state in {"FAILED", "EXPIRED", "DELETED", "CANCELLED"}:
        err_msg = data.get("error_message") or f"Acquisition ended in state {current_state}"
        output_message = f"File acquisition {acquisition_id} failed: {err_msg}"
        siemplify.LOGGER.error(output_message)
        return output_message, "false", EXECUTION_STATE_FAILED

    output_message = f"Acquisition {acquisition_id} is still {current_state}."
    siemplify.LOGGER.info(output_message)
    return output_message, json.dumps(acq_context), EXECUTION_STATE_INPROGRESS


@output_handler
def main(is_first_run=True) -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        input_type=str,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        input_type=str,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    agent_id_param = extract_action_param(
        siemplify,
        param_name="Agent Id",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    file_path_param = extract_action_param(
        siemplify,
        param_name="File Path",
        is_mandatory=bool(is_first_run),
        input_type=str,
        print_value=True,
    )
    use_api_mode_param = extract_action_param(
        siemplify,
        param_name="Use API Mode",
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    external_id_param = extract_action_param(
        siemplify,
        param_name="External Id",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )

    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = "false"

    try:
        hx_manager = FireEyeHXManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        if is_first_run:
            output_message, result_value, status = start_file_acquisition(
                siemplify,
                hx_manager,
                agent_id_param,
                file_path_param,
                use_api_mode_param,
                external_id_param,
            )
        else:
            acq_context_raw = extract_action_param(
                siemplify=siemplify,
                param_name="additional_data",
                default_value="{}",
                is_mandatory=False,
                input_type=str,
            )
            acq_context = json.loads(acq_context_raw)
            output_message, result_value, status = poll_file_acquisition(
                siemplify,
                hx_manager,
                acq_context,
            )

    except Exception as e:
        siemplify.LOGGER.exception(f"Failed to execute action! Error is {e}")
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Failed to execute action! Error is {e}"

    finally:
        try:
            hx_manager.logout()
        except Exception as e:
            siemplify.LOGGER.exception(f"Logging out failed. Error: {e}")

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
