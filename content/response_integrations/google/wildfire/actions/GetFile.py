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

import base64
import contextlib
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param

from ..core.WildfireManager import WildfireManager, WildfireNotFoundError

INTEGRATION_NAME = "Wildfire"
INTEGRATION_DISPLAY_NAME = "Palo Alto Wildfire"
ACTION_NAME = "Get File"
SAFE_SUFFIX_PATTERN = re.compile(r"^\.[A-Za-z0-9]{1,10}$")
SAFE_PREFIX_PATTERN = re.compile(r"[^A-Za-z0-9_-]")


def _get_download_dir(siemplify: SiemplifyAction) -> Path:
    """Return a writable directory for saved sample files."""
    try:
        candidate = getattr(siemplify, "run_folder", None)
    except OSError:
        candidate = None
    if isinstance(candidate, str) and candidate:
        download_dir = Path(candidate)
        if download_dir.is_dir() and os.access(download_dir, os.W_OK):
            return download_dir
    return Path(tempfile.gettempdir())


def _safe_suffix(filename: str) -> str:
    """Return a sanitized ASCII file extension for the temporary sample file."""
    suffix = Path(filename).suffix
    if SAFE_SUFFIX_PATTERN.fullmatch(suffix):
        return suffix
    return ".dat"


def _save_sample_to_disk(
    siemplify: SiemplifyAction,
    file_hash: str,
    filename: str,
    content: bytes,
) -> str:
    """Save downloaded sample bytes to a temporary file and return its path."""
    download_dir = _get_download_dir(siemplify)
    safe_hash = SAFE_PREFIX_PATTERN.sub("_", file_hash)
    suffix = _safe_suffix(filename)
    download_path = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f"{safe_hash}_",
            suffix=suffix,
            dir=download_dir,
            delete=False,
        ) as tmp_file:
            download_path = tmp_file.name
            tmp_file.write(content)
    except OSError:
        if download_path:
            with contextlib.suppress(OSError):
                Path(download_path).unlink(missing_ok=True)
        raise
    return download_path


def _process_file_hash(
    siemplify: SiemplifyAction,
    wildfire_manager: WildfireManager,
    file_hash: str,
) -> tuple[str, bool, int]:
    try:
        sample = wildfire_manager.get_sample(file_hash)
    except WildfireNotFoundError:
        siemplify.LOGGER.info(f"Sample not found for hash {file_hash}")
        return (
            f"No file sample was found for hash {file_hash} in {INTEGRATION_DISPLAY_NAME}.",
            False,
            EXECUTION_STATE_COMPLETED,
        )
    except Exception as e:
        siemplify.LOGGER.exception(f"Failed to download sample for hash {file_hash}")
        return f'Error executing action "{ACTION_NAME}". Reason: {e}', False, EXECUTION_STATE_FAILED

    try:
        download_path = _save_sample_to_disk(siemplify, file_hash, sample["filename"], sample["content"])
    except OSError as e:
        siemplify.LOGGER.exception(f"Failed to save sample for hash {file_hash} to disk")
        return (
            f'Error executing action "{ACTION_NAME}". Reason: Failed to save sample for hash {file_hash} to disk: {e}',
            False,
            EXECUTION_STATE_FAILED,
        )

    siemplify.LOGGER.info(f"Saved sample for hash {file_hash} to {download_path}")
    b64_content = base64.b64encode(sample["content"]).decode("utf-8")
    siemplify.result.add_attachment(f"WildFire sample {file_hash}", sample["filename"], b64_content)

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.FILEHASH and entity.identifier.lower() == file_hash.lower():
            siemplify.result.add_entity_attachment(entity.identifier, sample["filename"], b64_content)

    json_results = [
        {
            "file_hash": file_hash,
            "filename": sample["filename"],
            "download_path": download_path,
            "downloaded": True,
        }
    ]
    siemplify.result.add_result_json(json_results)
    return (
        f"Successfully downloaded file sample for {file_hash} using {INTEGRATION_DISPLAY_NAME}.",
        True,
        EXECUTION_STATE_COMPLETED,
    )


def _format_entity_results(
    enriched_entities: list[Any],
    not_found_entities: list[str],
    failed_entities: list[str],
    errors: list[str],
) -> tuple[str, bool, int]:
    if enriched_entities:
        entities_str = ", ".join(entity.identifier for entity in enriched_entities)
        msg = (
            f"Successfully downloaded files for the following entities using "
            f"{INTEGRATION_DISPLAY_NAME}: {entities_str}."
        )
        unsuccessful = not_found_entities + failed_entities
        if unsuccessful:
            msg += (
                f"\nAction wasn't able to download files for the following entities using "
                f"{INTEGRATION_DISPLAY_NAME}: {', '.join(unsuccessful)}."
            )
        if errors:
            msg += "\nErrors:\n" + "\n".join(errors)
        return msg, True, EXECUTION_STATE_COMPLETED

    if errors:
        reasons = "; ".join(errors)
        return f'Error executing action "{ACTION_NAME}". Reason: {reasons}', False, EXECUTION_STATE_FAILED

    msg = f"No files were downloaded using {INTEGRATION_DISPLAY_NAME}."
    if not_found_entities:
        msg += (
            f"\nAction wasn't able to download files for the following entities using "
            f"{INTEGRATION_DISPLAY_NAME}: {', '.join(not_found_entities)}."
        )
    return msg, False, EXECUTION_STATE_COMPLETED


def _process_entities(
    siemplify: SiemplifyAction,
    wildfire_manager: WildfireManager,
) -> tuple[str, bool, int]:
    enriched_entities: list[Any] = []
    not_found_entities: list[str] = []
    failed_entities: list[str] = []
    errors: list[str] = []
    json_results: list[dict[str, Any]] = []

    for entity in siemplify.target_entities:
        if entity.entity_type != EntityTypes.FILEHASH or len(entity.identifier) not in {32, 64}:
            continue
        try:
            sample = wildfire_manager.get_sample(entity.identifier)
        except WildfireNotFoundError:
            siemplify.LOGGER.info(f"Sample not found for entity {entity.identifier}")
            not_found_entities.append(entity.identifier)
            continue
        except Exception as e:
            siemplify.LOGGER.exception(f"Failed to download sample for entity {entity.identifier}")
            failed_entities.append(entity.identifier)
            errors.append(f"{entity.identifier}: {e}")
            continue

        try:
            download_path = _save_sample_to_disk(siemplify, entity.identifier, sample["filename"], sample["content"])
        except OSError as e:
            siemplify.LOGGER.exception(f"Failed to save sample for entity {entity.identifier} to disk")
            failed_entities.append(entity.identifier)
            errors.append(f"{entity.identifier}: Failed to save sample to disk: {e}")
            continue

        siemplify.LOGGER.info(f"Saved sample for entity {entity.identifier} to {download_path}")
        b64_content = base64.b64encode(sample["content"]).decode("utf-8")
        siemplify.result.add_entity_attachment(entity.identifier, sample["filename"], b64_content)
        enriched_entities.append(entity)
        json_results.append({
            "file_hash": entity.identifier,
            "filename": sample["filename"],
            "download_path": download_path,
            "downloaded": True,
        })

    if json_results:
        siemplify.result.add_result_json(json_results)

    return _format_entity_results(enriched_entities, not_found_entities, failed_entities, errors)


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {ACTION_NAME}"

    file_hash = extract_action_param(
        siemplify,
        param_name="File Hash",
        is_mandatory=False,
        print_value=True,
    )

    try:
        wildfire_manager = WildfireManager.from_siemplify(siemplify)
    except Exception as e:
        siemplify.LOGGER.exception("Failed to initialize Wildfire manager")
        siemplify.end(f'Error executing action "{ACTION_NAME}". Reason: {e}', False, EXECUTION_STATE_FAILED)
        return

    if file_hash:
        msg, is_success, status = _process_file_hash(siemplify, wildfire_manager, file_hash)
    else:
        msg, is_success, status = _process_entities(siemplify, wildfire_manager)

    siemplify.end(msg, is_success, status)


if __name__ == "__main__":
    main()
