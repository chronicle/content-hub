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
from datetime import datetime, timedelta, timezone
from typing import Any
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

INTEGRATION_NAME = "FireEyeHX"
SCRIPT_NAME = "Create Bulk Acquisition"
DEFAULT_HOST_SET_NAME = "all_hosts"
DEFAULT_COMMENT = "Created by Google SecOps"
SCHEMA_NAMESPACES = 'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"'


def extract_script_xml(script_content: str, logger: Any = None) -> str:
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
    cleaned = timestamp_str.strip()
    try:
        datetime.fromisoformat(cleaned)
    except ValueError as val_err:
        raise ValueError(f"{param_name} must be a valid ISO timestamp, got: {timestamp_str}.") from val_err
    return cleaned


def substitute_interval_macros(
    script_text: str,
    timeframe_start: str | None,
    timeframe_stop: str | None,
) -> str:
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


def add_missing_schema_namespaces(script_text: str, logger: Any = None) -> str:
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


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )

    script_content = extract_action_param(
        siemplify,
        param_name="Script Content",
        is_mandatory=True,
        print_value=False,
    )

    host_set_name = extract_action_param(
        siemplify,
        param_name="Host Set Name",
        is_mandatory=False,
        default_value=DEFAULT_HOST_SET_NAME,
    )

    host_set_id_param = extract_action_param(
        siemplify,
        param_name="Host Set ID",
        is_mandatory=False,
    )

    agent_ids_param = extract_action_param(
        siemplify,
        param_name="Agent IDs",
        is_mandatory=False,
    )

    comment = extract_action_param(
        siemplify,
        param_name="Comment",
        is_mandatory=False,
        default_value=DEFAULT_COMMENT,
    )

    timeframe_start = extract_action_param(
        siemplify,
        param_name="Timeframe Start",
        is_mandatory=False,
    )

    timeframe_stop = extract_action_param(
        siemplify,
        param_name="Timeframe Stop",
        is_mandatory=False,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = "false"
    manager = None

    try:
        script_text = extract_script_xml(script_content, siemplify.LOGGER)
        script_text = substitute_interval_macros(script_text, timeframe_start, timeframe_stop)
        script_text = add_missing_schema_namespaces(script_text, siemplify.LOGGER)

        script_b64 = b64encode(script_text.encode("utf-8")).decode("utf-8")

        manager = FireEyeHXManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        agent_ids = None
        host_set_id = None

        if agent_ids_param and agent_ids_param.strip():
            agent_ids = [aid for aid in convert_comma_separated_to_list(agent_ids_param) if aid]
            if not agent_ids:
                raise ValueError("Agent IDs must contain at least one agent ID.")
            if host_set_id_param and str(host_set_id_param).strip():
                siemplify.LOGGER.warning("Both Agent IDs and Host Set ID were provided; targeting specific Agent IDs.")
        elif host_set_id_param and str(host_set_id_param).strip():
            try:
                host_set_id = int(str(host_set_id_param).strip())
            except ValueError as val_err:
                raise ValueError(f"Host Set ID must be an integer, got: {host_set_id_param}.") from val_err
        elif host_set_name and host_set_name.strip():
            resolved_id = manager.get_host_set_id_by_name(host_set_name.strip())
            if resolved_id is None:
                raise FireEyeHXNotFoundError(f"Host set '{host_set_name}' was not found.")
            host_set_id = resolved_id
        else:
            raise ValueError("Provide Agent IDs, Host Set ID or Host Set Name to target the bulk acquisition.")

        acquisition_data = manager.create_bulk_acquisition(
            script_b64=script_b64,
            host_set_id=host_set_id,
            agent_ids=agent_ids,
            comment=comment,
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
                siemplify.LOGGER.warning(f"Failed to log out: {logout_err}")

    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
