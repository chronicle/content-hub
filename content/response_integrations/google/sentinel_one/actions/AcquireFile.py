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

import datetime
import hashlib
import io
import json
import os
import secrets
import string
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
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.SentinelOneManager import (
    SentinelOneAgentNotFoundError,
    SentinelOneManager,
    SentinelOneManagerError,
)

INTEGRATION_NAME = "SentinelOne"
SCRIPT_NAME = "Acquire File"
SUPPORTED_ENTITIES = [EntityTypes.HOSTNAME, EntityTypes.ADDRESS]


class BadZipPasswordError(Exception):
    """Raised when the zip archive cannot be opened with the provided password."""

    pass


def generate_password() -> str:
    """Generate a 15-character password conforming to SentinelOne requirements."""
    chars = string.ascii_letters + string.digits + string.punctuation
    while True:
        password = "".join(secrets.choice(chars) for _ in range(15))
        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
            and any(not c.isalnum() for c in password)
        ):
            return password


def resolve_agent_id(
    siemplify: SiemplifyAction,
    manager: SentinelOneManager,
    agent_id_param: str | None,
) -> str | None:
    """Resolve target agent ID from parameter or fallback to scope entities."""
    if agent_id_param and str(agent_id_param).strip():
        return str(agent_id_param).strip()

    for entity in getattr(siemplify, "target_entities", []):
        if entity.entity_type in SUPPORTED_ENTITIES:
            try:
                by_ip = entity.entity_type == EntityTypes.ADDRESS
                return str(
                    manager.find_endpoint_agent_id(
                        entity.identifier, by_ip_address=by_ip
                    )
                )
            except SentinelOneAgentNotFoundError:
                continue
    return None


def get_acquired_file_info(zip_file: zipfile.ZipFile, target_file_path: str):
    """Return file metadata from manifest.json inside the acquired zip package."""
    try:
        manifest_raw = zip_file.read("manifest.json")
        manifest_entries = json.loads(manifest_raw.decode("utf-8"))
        for entry in manifest_entries:
            if entry.get("path") == target_file_path:
                return entry, manifest_entries
        if len(manifest_entries) == 1:
            return manifest_entries[0], manifest_entries
        return None, manifest_entries
    except RuntimeError as e:
        if "bad password" in str(e).lower() or "password required" in str(e).lower():
            raise BadZipPasswordError() from e
        raise


def process_acquired_file_bytes(zip_file: zipfile.ZipFile):
    """Read the non-manifest file from the zip archive and compute MD5 / SHA256 checksums."""
    non_manifest_names = [
        name for name in zip_file.namelist() if name != "manifest.json"
    ]
    if not non_manifest_names:
        return "", "", "", 0
    extracted_filename = non_manifest_names[0]
    file_bytes = zip_file.read(extracted_filename)
    md5_hash = hashlib.md5(file_bytes).hexdigest()
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()
    return extracted_filename, md5_hash, sha256_hash, len(file_bytes)


def start_file_acquisition(
    siemplify: SiemplifyAction,
    manager: SentinelOneManager,
    agent_id_param: str | None,
    file_path: str,
    password: str | None,
):
    """Start file acquisition request via SentinelOne API v2.1."""
    agent_id = resolve_agent_id(siemplify, manager, agent_id_param)
    if not agent_id:
        output_message = (
            "No valid agent_id was supplied or found across target entities."
        )
        siemplify.LOGGER.error(output_message)
        return output_message, "false", EXECUTION_STATE_FAILED

    if not file_path or not ("/" in file_path or "\\" in file_path):
        output_message = f"File Path '{file_path}' must be an absolute path."
        siemplify.LOGGER.error(output_message)
        return output_message, "false", EXECUTION_STATE_FAILED

    if not password or not str(password).strip():
        password = generate_password()

    try:
        manager.fetch_files(
            agent_id=agent_id, file_path=file_path, password=password
        )
    except SentinelOneManagerError as mgr_err:
        siemplify.LOGGER.exception(str(mgr_err))
        return str(mgr_err), "false", EXECUTION_STATE_FAILED
    except Exception as e:
        output_message = f"Unable to create file acquisition: {e}"
        siemplify.LOGGER.exception(output_message)
        return output_message, "false", EXECUTION_STATE_FAILED

    state = {
        "agent_id": str(agent_id),
        "file_path": file_path,
        "password": password,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "activities_seen": [],
    }
    output_message = (
        f"File acquisition requested for file '{file_path}' on agent {agent_id}. "
        "Waiting for agent upload."
    )
    return output_message, json.dumps(state), EXECUTION_STATE_INPROGRESS


def poll_file_acquisition(
    siemplify: SiemplifyAction, manager: SentinelOneManager, state: dict
):
    """Poll SentinelOne Activity Log (activity type 80) until complete or failed."""
    target_agent_id = state.get("agent_id")
    target_file_path = state.get("file_path")
    target_password = state.get("password")
    created_at = state.get("created_at")
    activities_seen = state.get("activities_seen", [])

    siemplify.LOGGER.info(
        f"Polling file upload activities for agent {target_agent_id}"
    )

    try:
        activities = manager.get_file_upload_activities(
            agent_id=target_agent_id, created_at_gte=created_at
        )
    except Exception as e:
        output_message = (
            f"Failed fetching activities for agent {target_agent_id}: {e}"
        )
        siemplify.LOGGER.exception(output_message)
        return output_message, "false", EXECUTION_STATE_FAILED

    for activity in activities:
        activity_id = str(activity.get("id"))
        if activity_id in activities_seen:
            continue

        activities_seen.append(activity_id)
        download_url = activity.get("data", {}).get("downloadUrl")
        if not download_url:
            continue

        try:
            zip_bytes = manager.download_file_by_url(download_url)
        except Exception as dl_err:
            siemplify.LOGGER.info(
                f"Failed downloading activity {activity_id} stream: {dl_err}"
            )
            continue

        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zipf:
                zipf.setpassword(target_password.encode("utf-8"))
                try:
                    file_info, _ = get_acquired_file_info(
                        zipf, target_file_path
                    )
                except BadZipPasswordError:
                    siemplify.LOGGER.info(
                        f"Skipping activity {activity_id}: zip password did not match."
                    )
                    continue

                if not file_info:
                    siemplify.LOGGER.info(
                        f"Target file '{target_file_path}' not found in activity {activity_id} manifest."
                    )
                    continue

                is_included = file_info.get("included")
                if is_included is True or str(is_included).lower() in (
                    "true",
                    "1",
                ):
                    extracted_name, md5, sha256, size = (
                        process_acquired_file_bytes(zipf)
                    )
                    completed_at = datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat()

                    execution_folder = getattr(siemplify, "run_folder", None)
                    if not isinstance(execution_folder, str) or not os.path.isdir(execution_folder):
                        execution_folder = getattr(siemplify, "execution_folder", None)
                    if not isinstance(execution_folder, str) or not os.path.isdir(execution_folder):
                        execution_folder = "/tmp"
                    temp_filename = os.path.join(
                        execution_folder, f"{uuid.uuid4()}.zip"
                    )
                    with open(temp_filename, "wb") as f:
                        f.write(zip_bytes)
                    siemplify.LOGGER.info(
                        f"Saved acquired package to: {temp_filename}"
                    )

                    json_result = {
                        "agent_id": target_agent_id,
                        "file_path": target_file_path,
                        "zip_password": target_password,
                        "status": "COMPLETED",
                        "file_name": extracted_name or file_info.get("name", ""),
                        "md5": md5 or file_info.get("md5", ""),
                        "sha256": sha256 or file_info.get("sha256", ""),
                        "sha1": file_info.get("sha1", ""),
                        "size": size or file_info.get("size", 0),
                        "manifest": file_info,
                        "created_at": created_at,
                        "completed_at": completed_at,
                        "download_path": temp_filename,
                        "local_package_file": temp_filename,
                    }
                    siemplify.result.add_result_json(json_result)
                    output_message = (
                        f"File '{target_file_path}' was successfully acquired from host {target_agent_id} "
                        f"(MD5: {json_result['md5']})."
                    )
                    return output_message, "true", EXECUTION_STATE_COMPLETED
                else:
                    reason = file_info.get(
                        "reason", "File could not be collected by agent."
                    )
                    output_message = f"File acquisition for '{target_file_path}' failed: {reason}"
                    json_result = {
                        "agent_id": target_agent_id,
                        "file_path": target_file_path,
                        "status": "FAILED",
                        "reason": reason,
                        "manifest": file_info,
                    }
                    siemplify.result.add_result_json(json_result)
                    return output_message, "false", EXECUTION_STATE_FAILED
        except zipfile.BadZipFile:
            siemplify.LOGGER.info(
                f"Skipping activity {activity_id}: non-zip payload."
            )
            continue

    state["activities_seen"] = activities_seen
    output_message = (
        f"Acquisition for file '{target_file_path}' is still in progress on agent {target_agent_id}."
    )
    return output_message, json.dumps(state), EXECUTION_STATE_INPROGRESS


@output_handler
def main(is_first_run: bool = True) -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
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

    agent_id_param = extract_action_param(
        siemplify,
        param_name="Agent ID",
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
    password_param = extract_action_param(
        siemplify,
        param_name="Password",
        is_mandatory=False,
        input_type=str,
        print_value=False,
    )

    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = "false"

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = SentinelOneManager(api_root, username, password)

        if is_first_run:
            output_message, result_value, status = start_file_acquisition(
                siemplify=siemplify,
                manager=manager,
                agent_id_param=agent_id_param,
                file_path=file_path_param,
                password=password_param,
            )
        else:
            state_raw = extract_action_param(
                siemplify,
                param_name="additional_data",
                default_value="{}",
                is_mandatory=False,
                input_type=str,
            )
            state = json.loads(state_raw or "{}")
            if not state or not state.get("agent_id"):
                raise ValueError(
                    "Missing or invalid 'additional_data' state for polling run."
                )

            output_message, result_value, status = poll_file_acquisition(
                siemplify=siemplify,
                manager=manager,
                state=state,
            )
    except Exception as e:
        siemplify.LOGGER.exception(f"Failed to execute action! Error is {e}")
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Failed to execute action! Error is {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
