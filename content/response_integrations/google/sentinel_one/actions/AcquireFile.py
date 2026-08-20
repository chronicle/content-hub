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
from contextlib import contextmanager
import datetime
import hashlib
import json
import os
import secrets
from shutil import copy
import string
import sys
import tempfile
from typing import Any, Dict, List, Optional
import zipfile

try:
    from soar_sdk.SiemplifyAction import SiemplifyAction
    from soar_sdk.SiemplifyUtils import output_handler, unix_now
    from soar_sdk.ScriptResult import (
        EXECUTION_STATE_COMPLETED,
        EXECUTION_STATE_FAILED,
        EXECUTION_STATE_INPROGRESS,
        EXECUTION_STATE_TIMEDOUT,
    )
except ImportError:
    from SiemplifyAction import SiemplifyAction
    from SiemplifyUtils import output_handler, unix_now
    from ScriptResult import (
        EXECUTION_STATE_COMPLETED,
        EXECUTION_STATE_FAILED,
        EXECUTION_STATE_INPROGRESS,
        EXECUTION_STATE_TIMEDOUT,
    )

from TIPCommon import extract_action_param, extract_configuration_param

try:
    from ..core.SentinelOneResponseManager import SentinelOneResponseManager
    from ..core.exceptions import (
        SentinelOneException,
        SentinelOneNotFoundError,
        SentinelOneTimeoutException,
    )
except ImportError:
    from SentinelOneResponseManager import SentinelOneResponseManager
    from exceptions import (
        SentinelOneException,
        SentinelOneNotFoundError,
        SentinelOneTimeoutException,
    )

PROVIDER_NAME = "SentinelOne"
SCRIPT_NAME = "Acquire File"
TIMEOUT_THRESHOLD_MS = 35000
SUPPORTED_ENTITY_TYPES = ["HOSTNAME"]
DOWNLOAD_CHUNK_SIZE = 65536
READ_BUFFER_SIZE = 4096
TMPDIR = "/opt/siemplify/siemplify_server/Scripting"


def generate_password() -> str:
    """
    Generate a 15-character complex password conforming to SentinelOne specs.
    Must contain lowercase, uppercase, digit, and symbol.

    :return: Generated password string
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


def is_absolute_path(path: Optional[str]) -> bool:
    """
    Validate if path is a non-empty absolute path (Unix, Windows drive, or Windows UNC).

    :param path: File path string
    :return: True if absolute, False otherwise
    """
    if not path or not isinstance(path, str) or not path.strip():
        return False
    p = path.strip()
    if p.startswith("/"):
        return True
    if p.startswith("\\\\"):
        return True
    if len(p) >= 3 and p[0].isalpha() and p[1:3] in [":\\", ":/"]:
        return True
    return False


def get_manager(siemplify: SiemplifyAction) -> SentinelOneResponseManager:
    """
    Instantiate SentinelOneResponseManager using configuration parameters.

    :param siemplify: SiemplifyAction instance
    :return: SentinelOneResponseManager instance
    """
    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Api Root",
        input_type=str,
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Token",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Username",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Password",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=False,
        default_value=True,
    )
    return SentinelOneResponseManager(
        api_root=api_root,
        api_token=api_token,
        username=username,
        password=password,
        verify_ssl=verify_ssl,
    )


def is_approaching_timeout(
    action_start_time: int, python_process_timeout: Optional[int]
) -> bool:
    """
    Check if action execution is approaching timeout deadline.

    :param action_start_time: Action start time in milliseconds
    :param python_process_timeout: Execution deadline in milliseconds
    :return: True if timeout is approaching, False otherwise
    """
    if not isinstance(python_process_timeout, (int, float)) or python_process_timeout <= 0:
        return False
    return unix_now() >= (python_process_timeout - TIMEOUT_THRESHOLD_MS)


def save_acquired_package(src_file_path: str) -> str:
    """
    Save the acquired package zip to temporary scripting directory or system temp directory.

    :param src_file_path: Source temporary zip file path
    :return: Preserved file path
    """
    target_dir = TMPDIR if os.path.exists(TMPDIR) else tempfile.gettempdir()
    fd, dest_path = tempfile.mkstemp(dir=target_dir, prefix="acq-", suffix=".zip")
    os.close(fd)
    copy(src_file_path, dest_path)
    return dest_path


def decode_additional_data(raw_data: Any) -> Dict[str, Any]:
    """
    Decode additional_data parameter from JSON string or dictionary.

    :param raw_data: Additional data string or dict
    :return: Parsed state dictionary
    """
    if not raw_data:
        return {}
    if isinstance(raw_data, dict):
        return raw_data
    if isinstance(raw_data, str):
        try:
            parsed = json.loads(raw_data)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        if "," in raw_data or raw_data.isalnum():
            return {
                "activities_seen": [
                    x.strip() for x in raw_data.split(",") if x.strip()
                ]
            }
    return {}


@contextmanager
def extract_zip_from_response(response: Any, password: Optional[str]):
    """
    Save streamed response to a temporary file, open as ZipFile with password, and yield.
    Cleans up the temporary file on exit.

    :param response: requests.Response or bytes
    :param password: Optional archive password
    :yield: Tuple of (ZipFile, temporary_file_path)
    """
    target_dir = TMPDIR if os.path.exists(TMPDIR) else tempfile.gettempdir()
    with tempfile.NamedTemporaryFile(delete=True, dir=target_dir) as tmp_fh:
        if hasattr(response, "iter_content"):
            for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                if chunk:
                    tmp_fh.write(chunk)
        elif hasattr(response, "content"):
            tmp_fh.write(response.content)
        elif isinstance(response, bytes):
            tmp_fh.write(response)
        tmp_fh.flush()
        tmp_fh.seek(0)

        with zipfile.ZipFile(tmp_fh.name) as zipf:
            if password:
                zipf.setpassword(password.encode("utf-8"))
            yield zipf, tmp_fh.name


@output_handler
def main(is_first_run: bool = True):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = SCRIPT_NAME

    mode = "Main" if is_first_run else "QueryState"
    siemplify.LOGGER.info(f"----------------- {mode} - Starting -----------------")

    fail_if_timeout = extract_action_param(
        siemplify,
        param_name="Fail If Timeout",
        input_type=bool,
        is_mandatory=False,
        default_value=False,
    )

    action_status = EXECUTION_STATE_COMPLETED
    is_success = True
    output_message = ""
    result_value: Any = False
    json_result: Dict[str, Any] = {}
    target_agent_id = ""

    try:
        manager = get_manager(siemplify)

        if is_approaching_timeout(
            action_start_time, getattr(siemplify, "execution_deadline_unix_time_ms", 0)
        ):
            raise SentinelOneTimeoutException("Timeout was approached.")

        if is_first_run:
            agent_id = extract_action_param(
                siemplify,
                param_name="Agent ID",
                input_type=str,
                is_mandatory=False,
                default_value=None,
            )
            if not agent_id:
                agent_id = extract_action_param(
                    siemplify,
                    param_name="Agent UUID",
                    input_type=str,
                    is_mandatory=False,
                    default_value=None,
                )

            if not agent_id:
                suitable_entities = [
                    entity
                    for entity in getattr(siemplify, "target_entities", [])
                    if getattr(entity, "entity_type", None) in SUPPORTED_ENTITY_TYPES
                ]
                if len(suitable_entities) == 1:
                    entity = suitable_entities[0]
                    agent_id = (
                        getattr(entity, "identifier", None)
                        or getattr(entity, "original_identifier", None)
                        or str(entity)
                    )
                else:
                    raise ValueError(
                        "If not passing in an endpoint id, your case/alert needs to be associated "
                        f"with exactly one HOSTNAME entity containing the endpoint id. Found {len(suitable_entities)} hosts."
                    )

            target_agent_id = agent_id

            file_path = extract_action_param(
                siemplify,
                param_name="File Path",
                input_type=str,
                is_mandatory=True,
            )
            if not is_absolute_path(file_path):
                raise ValueError(
                    f"File path '{file_path}' is not a valid absolute path. Absolute path required."
                )

            password = extract_action_param(
                siemplify,
                param_name="Password",
                input_type=str,
                is_mandatory=False,
                print_value=False,
                default_value=None,
            )
            if password is None or not str(password).strip():
                password = generate_password()
            else:
                password = str(password).strip()

            siemplify.LOGGER.info(
                f"Resolving agent ID for '{target_agent_id}' and initiating fetch-files for '{file_path}'"
            )

            resolved_agent_id = target_agent_id
            try:
                agent = manager.get_agent_by_uuid(target_agent_id)
                resolved_agent_id = str(agent.id)
            except SentinelOneNotFoundError:
                if not target_agent_id.isdigit():
                    raise

            created_at_utc = datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat()
            fetch_data = manager.initiate_fetch_files(
                resolved_agent_id, file_path, password
            )

            state = {
                "agent_id": resolved_agent_id,
                "file_path": file_path,
                "password": password,
                "created_at": created_at_utc,
                "activities_seen": [],
            }

            action_status = EXECUTION_STATE_INPROGRESS
            is_success = True
            output_message = (
                f"File acquisition initiated for '{file_path}' on agent '{resolved_agent_id}'. "
                "Waiting for package."
            )
            result_value = json.dumps(state)
            json_result = {
                "status": "in_progress",
                "agent_id": resolved_agent_id,
                "file_path": file_path,
                "zip_password": password,
                "created_at": created_at_utc,
                "data": fetch_data,
            }

        else:
            # Polling run
            raw_additional_data = getattr(siemplify, "parameters", {}).get(
                "additional_data"
            )
            state = decode_additional_data(raw_additional_data)

            agent_id = (
                state.get("agent_id")
                or extract_action_param(
                    siemplify,
                    param_name="Agent ID",
                    input_type=str,
                    is_mandatory=False,
                    default_value=None,
                )
                or extract_action_param(
                    siemplify,
                    param_name="Agent UUID",
                    input_type=str,
                    is_mandatory=False,
                    default_value=None,
                )
            )
            target_agent_id = str(agent_id) if agent_id else ""

            file_path = state.get("file_path") or extract_action_param(
                siemplify,
                param_name="File Path",
                input_type=str,
                is_mandatory=False,
                default_value=None,
            )

            password = state.get("password") or extract_action_param(
                siemplify,
                param_name="Password",
                input_type=str,
                is_mandatory=False,
                print_value=False,
                default_value=None,
            )

            created_at = state.get("created_at") or extract_action_param(
                siemplify,
                param_name="Acquisition Created At",
                input_type=str,
                is_mandatory=False,
                default_value=None,
            )
            if not created_at:
                created_at = datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat()

            activities_seen: List[str] = [
                str(x) for x in state.get("activities_seen", [])
            ]

            siemplify.LOGGER.info(
                f"Polling file upload activities for agent '{target_agent_id}' since '{created_at}'"
            )

            activities = manager.get_file_upload_activities(
                target_agent_id, created_at
            )
            found_package = False

            for activity in activities:
                activity_id = str(activity.get("id"))
                if activity_id in activities_seen:
                    siemplify.LOGGER.info(
                        f"Skipping previously inspected activity {activity_id}"
                    )
                    continue

                activities_seen.append(activity_id)

                download_url = activity.get("data", {}).get("downloadUrl")
                if not download_url:
                    continue

                response = manager.download_file(download_url)

                try:
                    with extract_zip_from_response(response, password) as (
                        zipf,
                        temp_pkg_path,
                    ):
                        try:
                            manifest_bytes = zipf.read("manifest.json")
                            manifest_data = json.loads(
                                manifest_bytes.decode("utf-8")
                            )
                        except RuntimeError as e:
                            if (
                                "bad password" in str(e).lower()
                                or "password" in str(e).lower()
                            ):
                                siemplify.LOGGER.warning(
                                    f"Skipping package for activity {activity_id}: bad password"
                                )
                                continue
                            raise
                        except zipfile.BadZipFile as e:
                            siemplify.LOGGER.warning(
                                f"Skipping corrupted package for activity {activity_id}: {e}"
                            )
                            continue

                        file_info = None
                        if isinstance(manifest_data, list):
                            for entry in manifest_data:
                                if isinstance(entry, dict):
                                    entry_path = entry.get("path", "")
                                    if (
                                        entry_path == file_path
                                        or entry_path.lower()
                                        == (file_path or "").lower()
                                    ):
                                        file_info = entry
                                        break
                        elif isinstance(manifest_data, dict):
                            if manifest_data.get("path") == file_path or str(
                                manifest_data.get("path", "")
                            ).lower() == (file_path or "").lower():
                                file_info = manifest_data

                        if not file_info:
                            siemplify.LOGGER.warning(
                                f"Acquired file '{file_path}' not found in package manifest for activity {activity_id}"
                            )
                            continue

                        is_included = file_info.get("included", False)
                        if is_included:
                            namelist = [
                                n
                                for n in zipf.namelist()
                                if n != "manifest.json" and not n.endswith("/")
                            ]
                            if namelist:
                                target_name = namelist[0]
                                md5_hash = hashlib.md5()
                                with zipf.open(target_name, "r") as f_in:
                                    while chunk := f_in.read(READ_BUFFER_SIZE):
                                        md5_hash.update(chunk)
                                file_info["file_name"] = target_name
                                file_info["md5"] = md5_hash.hexdigest()

                            local_pkg_path = save_acquired_package(
                                temp_pkg_path
                            )
                            now_iso = datetime.datetime.now(
                                datetime.timezone.utc
                            ).isoformat()
                            json_result = {
                                "agent_id": target_agent_id,
                                "file_path": file_path,
                                "zip_password": password,
                                "included": True,
                                "md5": file_info.get("md5"),
                                "file_name": file_info.get("file_name"),
                                "local_package_file": local_pkg_path,
                                "downloaded_at": now_iso,
                                "file_info": file_info,
                            }
                            action_status = EXECUTION_STATE_COMPLETED
                            is_success = True
                            output_message = (
                                f"Successfully acquired file '{file_path}' from "
                                f"agent '{target_agent_id}'."
                            )
                            result_value = True
                            found_package = True
                            break
                        else:
                            reason = (
                                file_info.get("reason")
                                or "File was not included in package."
                            )
                            json_result = {
                                "agent_id": target_agent_id,
                                "file_path": file_path,
                                "zip_password": password,
                                "included": False,
                                "reason": reason,
                                "NO_BINARY_FILE": True,
                                "file_info": file_info,
                            }
                            action_status = EXECUTION_STATE_FAILED
                            is_success = False
                            output_message = (
                                f"Failed to acquire file '{file_path}'. Reason: {reason}"
                            )
                            result_value = False
                            found_package = True
                            break

                except Exception as e:
                    siemplify.LOGGER.warning(
                        f"Error processing activity {activity_id}: {e}"
                    )
                    continue

            if not found_package:
                updated_state = {
                    "agent_id": target_agent_id,
                    "file_path": file_path,
                    "password": password,
                    "created_at": created_at,
                    "activities_seen": activities_seen,
                }
                action_status = EXECUTION_STATE_INPROGRESS
                is_success = True
                output_message = (
                    f"Waiting for file acquisition package for '{file_path}' on "
                    f"agent '{target_agent_id}'."
                )
                result_value = json.dumps(updated_state)
                json_result = {
                    "status": "in_progress",
                    "agent_id": target_agent_id,
                    "file_path": file_path,
                    "activities_inspected": len(activities_seen),
                }

    except SentinelOneNotFoundError as e:
        output_message = f"Could not find endpoint '{target_agent_id}' in SentinelOne."
        siemplify.LOGGER.error(output_message)
        json_result = {
            "status": "failed",
            "agent_id": target_agent_id,
            "reason": output_message,
        }
        action_status = EXECUTION_STATE_FAILED
        is_success = False
        result_value = False

    except SentinelOneTimeoutException as e:
        timeout_message = (
            f"File acquisition request timed out for endpoint '{target_agent_id}'."
        )
        siemplify.LOGGER.error(timeout_message)
        json_result = {
            "status": "timed_out",
            "agent_id": target_agent_id,
            "reason": timeout_message,
        }
        is_success = False
        result_value = False
        if not is_first_run:
            output_message = timeout_message
            action_status = EXECUTION_STATE_FAILED
            if fail_if_timeout:
                siemplify.result.add_result_json(json_result)
                raise SentinelOneTimeoutException(output_message)
        else:
            output_message = "Action timed out before execution completed."
            action_status = EXECUTION_STATE_TIMEDOUT

    except ValueError as e:
        output_message = str(e)
        siemplify.LOGGER.error(output_message)
        json_result = {
            "status": "failed",
            "agent_id": target_agent_id,
            "reason": output_message,
        }
        action_status = EXECUTION_STATE_FAILED
        is_success = False
        result_value = False

    except Exception as e:
        output_message = f"Error executing action '{SCRIPT_NAME}'. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        json_result = {
            "status": "failed",
            "agent_id": target_agent_id,
            "reason": str(e),
        }
        action_status = EXECUTION_STATE_FAILED
        is_success = False
        result_value = False

    siemplify.result.add_result_json(json_result)
    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {action_status}\n  is_success: {is_success}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, action_status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
