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
import secrets
import string
import sys
import zipfile

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.SentinelOneManager import SentinelOneManager

SENTINEL_ONE_PROVIDER = "SentinelOne"
SCRIPT_NAME = "SentinelOne - Acquire File"


class BadZipPasswordError(Exception):
    """Raised when the zip archive cannot be opened with the provided password."""

    pass


def generate_password() -> str:
    """
    Generate a 15-character password conforming to SentinelOne file acquisition requirements.
    Must contain at least 1 lowercase, 1 uppercase, 1 digit, and 1 special/punctuation character.
    """
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


def get_acquired_file_info(zip_file: zipfile.ZipFile, target_file_path: str):
    """
    Return file metadata from manifest.json inside the acquired zip package.
    """
    try:
        manifest_raw = zip_file.read("manifest.json")
        manifest_entries = json.loads(manifest_raw.decode("utf-8"))
        for entry in manifest_entries:
            if entry.get("path") == target_file_path:
                return entry, manifest_entries
        # If single-file acquisition package and path doesn't match exactly, fallback to first entry
        if len(manifest_entries) == 1:
            return manifest_entries[0], manifest_entries
        return None, manifest_entries
    except RuntimeError as e:
        if "bad password" in str(e).lower() or "password required" in str(e).lower():
            raise BadZipPasswordError() from e
        raise


def process_acquired_file_bytes(zip_file: zipfile.ZipFile):
    """
    Read the non-manifest file from the zip archive and compute MD5 / SHA256 checksums.
    """
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


@output_handler
def main(is_first_run: bool = True):
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    mode = "Main" if is_first_run else "QueryState"
    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    conf = siemplify.get_configuration(SENTINEL_ONE_PROVIDER)
    sentinel_one_manager = SentinelOneManager(
        conf["Api Root"], conf["Username"], conf["Password"]
    )

    agent_id = siemplify.extract_action_param(
        param_name="Agent ID", is_mandatory=is_first_run, print_value=True
    )
    file_path = siemplify.extract_action_param(
        param_name="File Path", is_mandatory=is_first_run, print_value=True
    )
    password = siemplify.extract_action_param(
        param_name="Password", is_mandatory=False, print_value=False
    )

    output_message = ""
    result_value = False
    status = EXECUTION_STATE_COMPLETED
    json_result = {}

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    try:
        if is_first_run:
            if not file_path or not ("/" in file_path or "\\" in file_path):
                raise ValueError(
                    f"File Path '{file_path}' must be an absolute path."
                )

            if not password or not str(password).strip():
                password = generate_password()

            sentinel_one_manager.fetch_files(
                agent_id=agent_id, file_path=file_path, password=password
            )

            state = {
                "agent_id": str(agent_id),
                "file_path": file_path,
                "password": password,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "activities_seen": [],
            }
            status = EXECUTION_STATE_INPROGRESS
            result_value = True
            output_message = (
                f"Successfully initiated file acquisition for '{file_path}' on agent '{agent_id}'. "
                "Waiting for agent upload."
            )
            siemplify.end(output_message, json.dumps(state), status)
            return

        # Polling run
        state_str = siemplify.parameters.get("additional_data")
        if not state_str:
            raise ValueError("Missing 'additional_data' state for polling run.")

        state = json.loads(state_str)
        target_agent_id = state.get("agent_id")
        target_file_path = state.get("file_path")
        target_password = state.get("password")
        created_at = state.get("created_at")
        activities_seen = state.get("activities_seen", [])

        activities = sentinel_one_manager.get_file_upload_activities(
            agent_id=target_agent_id, created_at_gte=created_at
        )

        found = False
        for activity in activities:
            activity_id = str(activity.get("id"))
            if activity_id in activities_seen:
                continue

            activities_seen.append(activity_id)
            download_url = activity.get("data", {}).get("downloadUrl")
            if not download_url:
                continue

            zip_bytes = sentinel_one_manager.download_file_by_url(download_url)
            try:
                with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zipf:
                    zipf.setpassword(target_password.encode("utf-8"))
                    try:
                        file_info, manifest_entries = get_acquired_file_info(
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

                    found = True
                    is_included = file_info.get("included")
                    if is_included is True or str(is_included).lower() in ("true", "1"):
                        extracted_name, md5, sha256, size = (
                            process_acquired_file_bytes(zipf)
                        )
                        completed_at = datetime.datetime.now(
                            datetime.timezone.utc
                        ).isoformat()
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
                        }
                        status = EXECUTION_STATE_COMPLETED
                        result_value = True
                        output_message = (
                            f"Successfully acquired file '{target_file_path}' from agent '{target_agent_id}' "
                            f"(MD5: {json_result['md5']})."
                        )
                    else:
                        reason = file_info.get(
                            "reason", "File could not be collected by agent."
                        )
                        status = EXECUTION_STATE_FAILED
                        result_value = False
                        output_message = (
                            f"Failed to acquire file '{target_file_path}': {reason}"
                        )
                        json_result = {
                            "agent_id": target_agent_id,
                            "file_path": target_file_path,
                            "status": "FAILED",
                            "reason": reason,
                            "manifest": file_info,
                        }
                    break
            except zipfile.BadZipFile:
                siemplify.LOGGER.info(
                    f"Skipping activity {activity_id}: corrupt or non-zip download."
                )
                continue

        if not found:
            state["activities_seen"] = activities_seen
            status = EXECUTION_STATE_INPROGRESS
            result_value = True
            output_message = (
                f"Waiting for file acquisition of '{target_file_path}' to complete on agent '{target_agent_id}'..."
            )
            siemplify.end(output_message, json.dumps(state), status)
            return

    except Exception as e:
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = f"Error executing action {SCRIPT_NAME}: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    if json_result:
        siemplify.result.add_result_json(json_result)
    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
