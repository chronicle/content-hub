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
from functools import partial

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
from ..core.UtilsManager import (
    AGENT_LOOKUP_ENTITY_TYPES,
    ErrorType,
    classify_exception,
    count_skipped_entities,
    get_agent_lookup_failure_counts,
    log_action_result_summary,
    log_timeout_marker_once,
)

INTEGRATION_NAME = "FireEyeHX"
SCRIPT_NAME = "Get File"
SUPPORTED_ENTITIES = [EntityTypes.HOSTNAME, EntityTypes.ADDRESS]
MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ACQUISITION_MODULES = (
    "file-acquisition-api",
    "file-acquisition-raw",
    "w32apifile-acquisition",
    "w32rawfile-acquisition",
)
ACQUISITION_FAILED_STATE_ERROR_TYPES = {
    "FAILED": ErrorType.VENDOR_ERROR,
    "EXPIRED": ErrorType.TIMEOUT,
    "DELETED": ErrorType.CANCELLED,
    "CANCELLED": ErrorType.CANCELLED,
}


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


def has_acquired_file(manifest):
    """Check if the manifest of an acquisition package lists an acquired file.

    Args:
        manifest: The manifest.json content of the acquisition package.

    Returns:
        True or False, or None if the manifest is missing or has no list of audits. Never raises.
    """
    audits = manifest.get("audits") if isinstance(manifest, dict) else None
    if not isinstance(audits, list):
        return None

    return any(
        isinstance(result, dict) and result.get("payload") and result.get("type") == "application/octet-stream"
        for audit in audits
        if isinstance(audit, dict) and audit.get("generator") in ACQUISITION_MODULES
        for result in (audit.get("results") if isinstance(audit.get("results"), list) else [])
    )


def get_single_target_counts(failure=None, skipped: int = 0):
    """Count the one target of the action for the summary line.

    Args:
        failure: The error type or the exception of the target, or None if it succeeded.
        skipped: The number of unsupported entities skipped.

    Returns:
        The target count, the success count, the failed target error types, and the skipped count.
    """
    if failure is None:
        return 1, 1, [], skipped

    return 1, 0, [classify_exception(failure)[0] if isinstance(failure, Exception) else failure], skipped


def start_file_acquisition(
    siemplify,
    hx_manager,
    agent_id_param,
    file_path_param,
    use_api_mode_param,
    external_id_param,
    skipped: int = 0,
):
    """Start the file acquisition process.

    Args:
        siemplify: The action object.
        hx_manager: The FireEye HX manager.
        agent_id_param: Explicit Agent Id parameter, if provided.
        file_path_param: Full file path on the endpoint to acquire.
        use_api_mode_param: Whether to acquire the file using API mode.
        external_id_param: Optional external correlation identifier.
        skipped: The number of unsupported entities skipped.

    Returns:
        The output message, result value, execution state, and summary count callable.
    """
    file_name, file_path = split_file_path(file_path_param)
    agent_id = hx_manager.resolve_agent_id_from_entities(
        target_entities=siemplify.target_entities,
        agent_id_param=agent_id_param,
    )
    if not agent_id:
        output_message = "No valid agent_id was supplied or found across target entities."
        siemplify.LOGGER.error(output_message)
        return (
            output_message,
            "false",
            EXECUTION_STATE_FAILED,
            lambda: (*get_agent_lookup_failure_counts(siemplify.target_entities, hx_manager.lookup_errors), skipped),
        )

    siemplify.LOGGER.info(f"Target Agent ID: {agent_id}")
    count_target = partial(get_single_target_counts, skipped=skipped)
    try:
        data = hx_manager.create_file_acquisition(
            agent_id=agent_id,
            file_path=file_path,
            file_name=file_name,
            external_id=external_id_param,
            use_api_mode=use_api_mode_param,
            comment="Acquiring file through Chronicle SOAR",
        )
    except (FireEyeHXNotFoundError, FireEyeHXManagerError) as mgr_err:
        siemplify.LOGGER.exception(str(mgr_err))
        return str(mgr_err), "false", EXECUTION_STATE_FAILED, partial(count_target, mgr_err)
    except Exception as e:
        siemplify.LOGGER.exception(f"Unexpected error creating file acquisition: {e}")
        return f"Unable to create file acquisition: {e}", "false", EXECUTION_STATE_FAILED, partial(count_target, e)

    acquisition_id = data.get("_id") or data.get("id") or data.get("acquisition_id")
    if not acquisition_id:
        output_message = f"Failed to acquire file: No acquisition ID in response data: {data}"
        siemplify.LOGGER.error(output_message)
        return output_message, "false", EXECUTION_STATE_FAILED, partial(count_target, ErrorType.VENDOR_ERROR)

    result_value = json.dumps({
        "acquisition_id": acquisition_id,
        "agent_id": agent_id,
        "file_name": file_name,
        "file_path": file_path,
        "skipped_count": skipped,
    })
    output_message = f"File acquisition {acquisition_id} requested for file '{file_name}' on agent {agent_id}."

    return output_message, result_value, EXECUTION_STATE_INPROGRESS, count_target


def poll_file_acquisition(siemplify, hx_manager, acq_context, skipped: int = 0):
    """Poll the file acquisition status until complete or failed.

    Args:
        siemplify: The action object.
        hx_manager: The FireEye HX manager.
        acq_context: Deserialized async polling state.
        skipped: Fallback unsupported entity count when state lacks skipped_count.

    Returns:
        The output message, result value, execution state, and summary count callable.
    """
    acquisition_id = acq_context.get("acquisition_id")
    agent_id = acq_context.get("agent_id")
    file_name = acq_context.get("file_name")
    count_target = partial(get_single_target_counts, skipped=acq_context.get("skipped_count", skipped))

    siemplify.LOGGER.info(f"Polling status for acquisition ID: {acquisition_id}")

    try:
        data = hx_manager.get_file_acquisition_by_id(acquisition_id)
    except Exception as e:
        output_message = f"Failed fetching status for acquisition {acquisition_id}: {e}"
        siemplify.LOGGER.exception(output_message)
        return output_message, "false", EXECUTION_STATE_FAILED, partial(count_target, e)

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
            return output_message, "false", EXECUTION_STATE_FAILED, partial(count_target, ErrorType.FILE_RESTRICTED)

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
            return output_message, "false", EXECUTION_STATE_FAILED, partial(count_target, dl_err)

        zip_passphrase = data.get("zip_passphrase")
        zip_metadata = extract_zip_metadata(temp_filename, zip_passphrase, siemplify)

        json_result = data.copy()
        if zip_metadata:
            json_result.update(zip_metadata)

        json_result["download_path"] = temp_filename
        file_acquired = has_acquired_file(zip_metadata)
        error_type = None if file_acquired else ErrorType.VENDOR_ERROR
        if file_acquired is not None:
            json_result["file_acquired"] = file_acquired
        if file_acquired is False:
            error_type = json_result["error_type"] = ErrorType.FILE_NOT_FOUND

        siemplify.result.add_result_json(json_result)
        output_message = f"File '{file_name}' was successfully acquired from host {agent_id}."
        return output_message, "true", EXECUTION_STATE_COMPLETED, partial(count_target, error_type)

    if current_state in ACQUISITION_FAILED_STATE_ERROR_TYPES:
        err_msg = data.get("error_message") or f"Acquisition ended in state {current_state}"
        output_message = f"File acquisition {acquisition_id} failed: {err_msg}"
        siemplify.LOGGER.error(output_message)
        get_counts = partial(count_target, ACQUISITION_FAILED_STATE_ERROR_TYPES[current_state])
        return output_message, "false", EXECUTION_STATE_FAILED, get_counts

    output_message = f"Acquisition {acquisition_id} is still {current_state}."
    siemplify.LOGGER.info(output_message)
    log_timeout_marker_once(siemplify, acq_context, partial(count_target, ErrorType.TIMEOUT))

    return output_message, json.dumps(acq_context), EXECUTION_STATE_INPROGRESS, count_target


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
    hx_manager = None
    get_counts = None
    has_agent_id = bool(isinstance(agent_id_param, str) and agent_id_param.strip())
    has_supported_entity = any(
        getattr(entity, "entity_type", "") in AGENT_LOOKUP_ENTITY_TYPES for entity in siemplify.target_entities
    )
    targets = int(not is_first_run or has_agent_id or has_supported_entity)
    skipped = count_skipped_entities(siemplify.target_entities, AGENT_LOOKUP_ENTITY_TYPES, has_agent_id=has_agent_id)
    error = None

    try:
        hx_manager = FireEyeHXManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        if is_first_run:
            output_message, result_value, status, get_counts = start_file_acquisition(
                siemplify,
                hx_manager,
                agent_id_param,
                file_path_param,
                use_api_mode_param,
                external_id_param,
                skipped=skipped,
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
            output_message, result_value, status, get_counts = poll_file_acquisition(
                siemplify,
                hx_manager,
                acq_context,
                skipped=skipped,
            )

    except Exception as e:
        error = e
        siemplify.LOGGER.exception(f"Failed to execute action! Error is {e}")
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Failed to execute action! Error is {e}"

    finally:
        try:
            if hx_manager is not None:
                hx_manager.logout()
        except Exception as e:
            siemplify.LOGGER.exception(f"Logging out failed. Error: {e}")

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    log_action_result_summary(
        siemplify,
        status,
        get_counts or (lambda: (targets, 0, [], skipped)),
        error=error,
        fallback_error_type=ErrorType.INVALID_INPUT,
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
