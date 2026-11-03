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

from base64 import b64encode
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from typing import TYPE_CHECKING
import xml.etree.ElementTree as ET

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
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
from ..core.UtilsManager import convert_comma_separated_to_list

if TYPE_CHECKING:
    from soar_sdk.SiemplifyLogger import SiemplifyLogger

INTEGRATION_NAME: str = "FireEyeHX"
SCRIPT_NAME: str = "Create Bulk Acquisition"
DEFAULT_HOST_SET_NAME: str = "all_hosts"
DEFAULT_COMMENT: str = "Created by Google SecOps"
SCHEMA_NAMESPACES: str = (
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"'
)


def is_json_script(script_content: str) -> bool:
    """Check if script content appears to be a JSON script.

    Args:
        script_content: Raw script string.

    Returns:
        True if script content appears to be JSON, False otherwise.
    """
    stripped = script_content.strip()
    if stripped.startswith(("{", "[")):
        return True
    openers = [idx for idx in (stripped.find("{"), stripped.find("[")) if idx != -1]
    if openers and not stripped.startswith("<") and "<script" not in stripped:
        start_idx = min(openers)
        prefix = stripped[:start_idx].strip().rstrip("\"'").strip()
        if prefix.endswith("=") and prefix[:-1].strip().isidentifier():
            return True
    return False


def extract_script_json(script_content: str, logger: SiemplifyLogger | None = None) -> str:
    """Extract JSON script from string, trimming Python wrapper if present.

    Args:
        script_content: Raw script string.
        logger: Optional SiemplifyLogger instance for logging trim operations.

    Returns:
        Trimmed JSON script string.

    Raises:
        ValueError: If script content is empty.
    """
    if not script_content or not script_content.strip():
        raise ValueError("Script Content must not be empty.")

    script_text = script_content.strip()
    openers = [index for index in (script_text.find("{"), script_text.find("[")) if index != -1]
    if not openers:
        return script_text
    start_idx = min(openers)
    try:
        _, end_idx = json.JSONDecoder().raw_decode(script_text, start_idx)
    except json.JSONDecodeError:
        return script_text[start_idx:]
    if logger and (start_idx > 0 or end_idx < len(script_text)):
        logger.info("Trimmed Python wrapper / assignment from Script Content JSON.")
    return script_text[start_idx:end_idx]


def validate_json_script(script_text: str) -> str:
    """Validate JSON script syntax.

    Args:
        script_text: JSON script string to validate.

    Returns:
        Validated JSON script string.

    Raises:
        ValueError: If JSON syntax is invalid.
    """
    try:
        json.loads(script_text)
    except json.JSONDecodeError as json_err:
        raise ValueError(f"Script Content contains invalid JSON: {json_err}.") from json_err
    return script_text


def extract_script_xml(script_content: str, logger: SiemplifyLogger | None = None) -> str:
    """Extract XML script from string, trimming Python wrapper if present.

    Args:
        script_content: Raw script string.
        logger: Optional SiemplifyLogger instance for logging trim operations.

    Returns:
        Trimmed XML script string.

    Raises:
        ValueError: If script content is empty.
    """
    if not script_content or not script_content.strip():
        raise ValueError("Script Content must not be empty.")

    script_text = script_content.strip()

    if "<?xml" in script_text:
        start_idx = script_text.find("<?xml")
        end_idx = script_text.rfind("</script>")
        if end_idx != -1:
            script_text = script_text[start_idx : end_idx + len("</script>")]
        else:
            script_text = script_text[start_idx:]
    elif "<script" in script_text:
        start_idx = script_text.find("<script")
        end_idx = script_text.rfind("</script>")
        if end_idx != -1:
            script_text = script_text[start_idx : end_idx + len("</script>")]

    if logger and len(script_text) < len(script_content.strip()):
        logger.info("Trimmed Python wrapper / assignment from Script Content XML.")

    return script_text


def validate_iso_timestamp(timestamp_str: str, param_name: str) -> str:
    """Validate an ISO-8601 formatted timestamp string.

    Args:
        timestamp_str: Timestamp string to validate.
        param_name: Parameter display name for error reporting.

    Returns:
        Cleaned timestamp string.

    Raises:
        ValueError: If timestamp string cannot be parsed as ISO-8601.
    """
    cleaned = timestamp_str.strip()
    try:
        datetime.fromisoformat(cleaned)
    except ValueError as val_err:
        raise ValueError(f"{param_name} must be a valid ISO timestamp, got: {timestamp_str}.") from val_err
    return cleaned


def substitute_interval_macros(script_text: str, timeframe_start: str | None, timeframe_stop: str | None) -> str:
    """Substitute dynamic interval macros in a script with ISO timestamps.

    Args:
        script_text: Script template containing optional interval macros.
        timeframe_start: Optional start timestamp override.
        timeframe_stop: Optional stop timestamp override.

    Returns:
        Script text with __INTERVAL_START__ and __INTERVAL_STOP__ resolved.
    """
    if "__INTERVAL_START__" in script_text or "__INTERVAL_STOP__" in script_text:
        utc_yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        utc_yesterday_str = utc_yesterday.strftime("%Y-%m-%d")

        if timeframe_start and timeframe_start.strip():
            start_val = validate_iso_timestamp(timeframe_start, "Timeframe Start")
        else:
            start_val = f"{utc_yesterday_str}T00:00:00"

        if timeframe_stop and timeframe_stop.strip():
            stop_val = validate_iso_timestamp(timeframe_stop, "Timeframe Stop")
        else:
            stop_val = f"{utc_yesterday_str}T23:59:59"

        script_text = script_text.replace("__INTERVAL_START__", start_val).replace("__INTERVAL_STOP__", stop_val)

    return script_text


def add_missing_schema_namespaces(script_text: str, logger: SiemplifyLogger | None = None) -> str:
    """Inject missing XML schema namespaces onto the root script tag if needed.

    Args:
        script_text: XML script string to validate and repair.
        logger: Optional SiemplifyLogger instance for logging.

    Returns:
        Repaired XML script string.

    Raises:
        ValueError: If XML cannot be parsed even after schema injection.
    """
    try:
        ET.fromstring(script_text)
    except ET.ParseError as xml_err:
        if "unbound prefix" in str(xml_err) and ("<script " in script_text or "<script>" in script_text):
            if logger:
                logger.info("Injecting missing XML schema namespaces (xsi, xsd) onto root <script> tag.")
            if "<script " in script_text:
                script_text = script_text.replace("<script ", f"<script {SCHEMA_NAMESPACES} ", 1)
            elif "<script>" in script_text:
                script_text = script_text.replace("<script>", f"<script {SCHEMA_NAMESPACES}>", 1)
            try:
                ET.fromstring(script_text)
            except ET.ParseError as retry_err:
                raise ValueError(f"Script Content contains invalid XML: {retry_err}.") from retry_err
        else:
            raise ValueError(f"Script Content contains invalid XML: {xml_err}.") from xml_err

    return script_text


@dataclass(slots=True)
class CreateBulkAcquisitionParams:
    """Action parameters for CreateBulkAcquisition."""

    script_content: str
    host_set_name: str
    host_set_id_param: str | None
    agent_ids_param: str | None
    comment: str
    timeframe_start: str | None
    timeframe_stop: str | None


def _init_manager(siemplify: SiemplifyAction) -> FireEyeHXManager:
    """Initialize and return a FireEyeHXManager instance using action configuration."""
    api_root: str = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    username: str = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password: str = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl: bool = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )
    return FireEyeHXManager(
        api_root=api_root,
        username=username,
        password=password,
        verify_ssl=verify_ssl,
    )


def _extract_action_params(siemplify: SiemplifyAction) -> CreateBulkAcquisitionParams:
    """Extract action parameters from SiemplifyAction."""
    return CreateBulkAcquisitionParams(
        script_content=extract_action_param(
            siemplify,
            param_name="Script Content",
            is_mandatory=True,
            print_value=False,
        ),
        host_set_name=extract_action_param(
            siemplify,
            param_name="Host Set Name",
            is_mandatory=False,
            default_value=DEFAULT_HOST_SET_NAME,
        ),
        host_set_id_param=extract_action_param(
            siemplify,
            param_name="Host Set ID",
            is_mandatory=False,
        ),
        agent_ids_param=extract_action_param(
            siemplify,
            param_name="Agent IDs",
            is_mandatory=False,
        ),
        comment=extract_action_param(
            siemplify,
            param_name="Comment",
            is_mandatory=False,
            default_value=DEFAULT_COMMENT,
        ),
        timeframe_start=extract_action_param(
            siemplify,
            param_name="Timeframe Start",
            is_mandatory=False,
        ),
        timeframe_stop=extract_action_param(
            siemplify,
            param_name="Timeframe Stop",
            is_mandatory=False,
        ),
    )


def _prepare_script_b64(
    params: CreateBulkAcquisitionParams,
    logger: SiemplifyLogger | None = None,
) -> str:
    """Process, validate, macro-substitute, and base64-encode acquisition script.

    Args:
        params: Extracted action parameters containing script and timeframes.
        logger: Optional logger for diagnostic messages.

    Returns:
        Base64-encoded script string.

    Raises:
        ValueError: If script content is empty or malformed.
    """
    if not params.script_content or not params.script_content.strip():
        raise ValueError("Script Content must not be empty.")

    if is_json_script(params.script_content):
        script_text = extract_script_json(params.script_content, logger)
        script_text = substitute_interval_macros(script_text, params.timeframe_start, params.timeframe_stop)
        script_text = validate_json_script(script_text)
    else:
        script_text = extract_script_xml(params.script_content, logger)
        script_text = substitute_interval_macros(script_text, params.timeframe_start, params.timeframe_stop)
        script_text = add_missing_schema_namespaces(script_text, logger)

    return b64encode(script_text.encode("utf-8")).decode("utf-8")


def _resolve_acquisition_targets(
    manager: FireEyeHXManager,
    params: CreateBulkAcquisitionParams,
    logger: SiemplifyLogger | None = None,
) -> tuple[int | None, list[str] | None]:
    """Resolve target host set ID or agent ID list for bulk acquisition.

    Args:
        manager: Authenticated FireEyeHXManager instance.
        params: Extracted action parameters containing target specifications.
        logger: Optional logger for warnings.

    Returns:
        Tuple of (host_set_id, agent_ids).

    Raises:
        ValueError: If targeting parameters are invalid or empty.
        FireEyeHXNotFoundError: If named host set cannot be found.
    """
    if params.agent_ids_param and params.agent_ids_param.strip():
        agent_ids = [aid for aid in convert_comma_separated_to_list(params.agent_ids_param) if aid]
        if not agent_ids:
            raise ValueError("Agent IDs must contain at least one agent ID.")
        if params.host_set_id_param and str(params.host_set_id_param).strip() and logger:
            logger.warn("Both Agent IDs and Host Set ID were provided; targeting specific Agent IDs.")
        return None, agent_ids

    if params.host_set_id_param and str(params.host_set_id_param).strip():
        try:
            return int(str(params.host_set_id_param).strip()), None
        except ValueError as val_err:
            raise ValueError(f"Host Set ID must be an integer, got: {params.host_set_id_param}.") from val_err

    if params.host_set_name and params.host_set_name.strip():
        resolved_id = manager.get_host_set_id_by_name(params.host_set_name.strip())
        if resolved_id is None:
            raise FireEyeHXNotFoundError(f"Host set '{params.host_set_name}' was not found.")
        return resolved_id, None

    raise ValueError("Provide Agent IDs, Host Set ID or Host Set Name to target the bulk acquisition.")


@output_handler
def main() -> None:
    """Create a bulk acquisition job on FireEye HX."""
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    params = _extract_action_params(siemplify)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status: int = EXECUTION_STATE_COMPLETED
    result_value: str = "false"
    manager: FireEyeHXManager | None = None

    try:
        script_b64: str = _prepare_script_b64(params, siemplify.LOGGER)
        manager = _init_manager(siemplify)
        host_set_id, agent_ids = _resolve_acquisition_targets(
            manager,
            params,
            siemplify.LOGGER,
        )

        acquisition_data = manager.create_bulk_acquisition(
            script_b64=script_b64,
            host_set_id=host_set_id,
            agent_ids=agent_ids,
            comment=params.comment,
        )

        bulk_id = acquisition_data.get("_id")
        if bulk_id is None:
            raise FireEyeHXManagerError("FireEye HX did not return a bulk acquisition ID.")
        state = acquisition_data.get("state", "UNKNOWN")
        result_value = str(bulk_id)
        siemplify.result.add_result_json(acquisition_data)
        output_message = f"Successfully created bulk acquisition {bulk_id}. State: {state}."

    except Exception as err:
        output_message = f"Error executing {SCRIPT_NAME}: {err}"
        siemplify.LOGGER.exception(output_message)
        status = EXECUTION_STATE_FAILED
        result_value = "false"

    finally:
        if manager:
            try:
                manager.logout()
            except Exception as logout_err:
                siemplify.LOGGER.warn(f"Failed to log out: {logout_err}")

    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
