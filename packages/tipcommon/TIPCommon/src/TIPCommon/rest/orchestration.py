# Copyright 2025 Google LLC
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

"""Orchestration client for managing and executing manual actions and playbook tasks."""

from __future__ import annotations

import base64
import contextlib
import io
import json
import logging
import re
import time
from typing import Any

from api_client_factory import get_soar_client
from requests import HTTPError, Response

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionJsonOutput, ActionOutput
from TIPCommon.data_models import ApiActionResult
from TIPCommon.exceptions import InternalJSONDecoderError
from TIPCommon.rest.soar_api import (
    get_env_action_def_files,
    get_installed_integrations_of_environment,
)

LARGE_JSON_THRESHOLD_BYTES = 2 * 1024 * 1024  # 2MB
PLACEHOLDER_PATTERN = re.compile(r"^<%\s*(.*?)\s*%>$")


def validate_response(
    response: Response,
    validate_json: bool = False,
) -> None:
    """Validate response and optionally verify it can be parsed as JSON.

    Args:
        response: The HTTP response to validate.
        validate_json: Whether to verify that the response content is valid JSON.

    Raises:
        HTTPError: If the response status code indicates an error.
        InternalJSONDecoderError: If validate_json is True and the response cannot
            be parsed as JSON.
    """
    try:
        response.raise_for_status()

        if validate_json:
            response.json()

    except HTTPError as he:
        msg = f"An error happened while requesting API, {he}"
        raise HTTPError(msg, response=he.response) from he

    except json.JSONDecodeError as je:
        msg = f"Failed to parse response as JSON.\nError: {je}\nRaw response: {response.text}"
        raise InternalJSONDecoderError(
            msg,
            response=je.response if hasattr(je, "response") else None,
        ) from je


def execute_manual_action(
    chronicle_soar: Any,
    case_id: int,
    action_name: str,
    action_properties: dict[str, Any],
    alert_group_identifiers: list[str] | None = None,
    scope: str | None = None,
    target_entities: list[dict[str, Any]] | None = None,
    is_predefined_scope: bool = False,
    action_provider: str = "Scripts",
) -> Response:
    """Execute a manual action on a case."""
    api_client = get_soar_client(chronicle_soar)
    api_client.params.case_id = case_id
    api_client.params.action_name = action_name
    api_client.params.action_provider = action_provider
    api_client.params.action_properties = action_properties
    api_client.params.alert_group_identifiers = alert_group_identifiers or []
    api_client.params.scope = scope
    api_client.params.target_entities = target_entities or []
    api_client.params.is_predefined_scope = is_predefined_scope

    response = api_client.execute_manual_action()
    validate_response(response)
    return response


def get_action_result_by_id(
    chronicle_soar: Any,
    result_id: str,
) -> Response:
    """Get the result of an action execution by its ID."""
    api_client = get_soar_client(chronicle_soar)
    response = api_client.get_action_result_by_id(result_id)
    validate_response(response)
    return response


_LOGGER = logging.getLogger(__name__)


def _determine_execution_state(status: Any) -> ExecutionState:
    """Determines the execution state based on the status code or name.

    Args:
        status: The status code (int) or status name (str).

    Returns:
        ExecutionState: The determined execution state.
    """
    if isinstance(status, str) and status.isdigit():
        status = int(status)

    if isinstance(status, int):
        if status in {1, 5}:  # 1: ASYNC_PENDING, 5: STARTED
            return ExecutionState.IN_PROGRESS
        if status in {2, 7}:  # 2: COMPLETED, 7: HANDLED_TIMEDOUT
            return ExecutionState.COMPLETED
    elif isinstance(status, str):
        status_upper = status.upper()
        if status_upper in {"ASYNC_PENDING", "STARTED", "PENDING_USER_INPUT"}:
            return ExecutionState.IN_PROGRESS
        if status_upper in {"COMPLETED", "HANDLED_TIMEDOUT"}:
            return ExecutionState.COMPLETED
    return ExecutionState.FAILED


def _fetch_inflated_resource(
    resource_path: str,
    chronicle_soar: Any,
    logger: logging.Logger,
) -> Any | None:
    """Fetches and inflates a placeholder resource blob using get_action_result_by_id."""
    parts = [p for p in resource_path.strip("/").split("/") if p]
    if not parts:
        return None

    result_id = parts[-1]
    logger.info(f"Fetching action result by ID '{result_id}' for resource '{resource_path}'")
    try:
        api_client = get_soar_client(chronicle_soar)
        response = api_client.get_action_result_by_id(result_id)
        response.raise_for_status()
        resp_json = response.json()

        if isinstance(resp_json, dict) and "blob" in resp_json:
            with contextlib.suppress(Exception):
                decoded_bytes = base64.b64decode(resp_json["blob"])
                return json.load(io.StringIO(decoded_bytes.decode("utf-8")))
        return resp_json
    except Exception as e:
        logger.error(f"Failed to fetch action result ID '{result_id}': {e}")
        return None


def _get_case_insensitive(d: dict[str, Any], key: str) -> Any:
    """Helper to get a value from a dictionary case-insensitively.

    Args:
        d: The dictionary.
        key: The lowercase key to search for.

    Returns:
        The value if found, otherwise None.
    """
    for k, v in d.items():
        if k.lower() == key:
            return v
    return None


def _get_result_json_data(
    result_model: ApiActionResult,
    chronicle_soar: Any | None,
    logger: logging.Logger,
) -> Any | None:
    """Retrieves resultJsonObject, checks JsonResult.RawJson for resource placeholders, inflates if needed, and extracts clean JSON.

    Args:
        result_model: The ApiActionResult model.
        chronicle_soar: The Chronicle SOAR client object, or None.
        logger: The logger to use.

    Returns:
        The extracted clean JSON data, or None.
    """
    raw_obj = result_model.result_json_object
    if not raw_obj:
        logger.info("result_json_object is empty or None, returning None")
        return None

    if isinstance(raw_obj, str):
        msg = (
            f"raw_obj is a string of length {len(raw_obj)}, attempting to parse as JSON"
        )
        logger.info(msg)
        with contextlib.suppress(Exception):
            raw_obj = json.loads(raw_obj)
            logger.info("Successfully parsed raw_obj string as JSON")

    if isinstance(raw_obj, dict):
        logger.info("raw_obj is a dictionary, checking for jsonresult")
        jr = _get_case_insensitive(raw_obj, "jsonresult")
        if isinstance(jr, dict):
            logger.info("Found jsonresult dict, retrieving rawjson")
            raw_json_val = _get_case_insensitive(jr, "rawjson")
            if isinstance(raw_json_val, str):
                msg = f"rawjson is a string of length {len(raw_json_val)}"
                logger.info(msg)
                match = PLACEHOLDER_PATTERN.match(raw_json_val.strip())
                # The field contains a url to actual json instead of json itself
                if match and chronicle_soar:
                    resource_path = match.group(1).strip()
                    msg = f"Inflating JsonResult.RawJson resource: {resource_path}"
                    logger.info(msg)
                    inflated = _fetch_inflated_resource(
                        resource_path, chronicle_soar, logger
                    )
                    if inflated is not None:
                        logger.info("Successfully inflated resource, updating raw_obj")
                        raw_obj = inflated
                else:
                    msg = (
                        "No placeholder match or no chronicle_soar client, "
                        "parsing rawjson string"
                    )
                    logger.info(msg)
                    with contextlib.suppress(Exception):
                        raw_obj = json.loads(raw_json_val)
                        logger.info("Successfully parsed rawjson string as JSON")
            elif raw_json_val is not None:
                logger.info("rawjson is not a string but not None, updating raw_obj")
                raw_obj = raw_json_val
        else:
            logger.info("jsonresult was not found or is not a dictionary")

    return raw_obj


def _build_action_output(
    response_json: dict[str, Any],
    chronicle_soar: Any = None,
    logger: logging.Logger | None = None,
) -> ActionOutput:
    logger = logger or _LOGGER

    result_model = ApiActionResult(response_json)

    status = result_model.status
    exec_state = _determine_execution_state(status)

    clean_json_data = _get_result_json_data(result_model, chronicle_soar, logger)
    json_output = None
    if clean_json_data is not None:
        if not isinstance(clean_json_data, dict):
            clean_json_data = {"result": clean_json_data}
        json_output = ActionJsonOutput(
            title="JsonResult",
            content="",
            is_for_entity=False,
            json_result=clean_json_data,
        )

    action_output = ActionOutput(
        output_message=result_model.message or "",
        result_value=result_model.result_value or "",
        execution_state=exec_state,
        json_output=json_output,
        debug_output="",
    )

    # Dynamically attach raw response and id for polling/backward-compatibility
    action_output.raw = response_json
    action_output.id = result_model.id
    action_output.status = status
    return action_output


def get_action_result(
    siemplify: Any,
    result_id: str,
    logger: logging.Logger | None = None,
    wait_for_result: bool = True,
    timeout_sec: int = 120,
    poll_interval_sec: int = 30,
) -> ActionOutput:
    """Gets the action execution result by its ID.

    Args:
        siemplify: ChronicleSOAR/SiemplifyAction object.
        result_id (str): The ID of the action result.
        logger: Optional logger to use.
        wait_for_result: Whether to wait/poll internally if result is pending.
        timeout_sec: Maximum time to wait in seconds.
        poll_interval_sec: Interval between poll requests in seconds.

    Returns:
        ActionOutput: Action execution output object.
    """
    response = get_action_result_by_id(chronicle_soar=siemplify, result_id=result_id)
    action_output = _build_action_output(response.json(), chronicle_soar=siemplify, logger=logger)
    if wait_for_result:
        action_output = _wait_for_completion(
            siemplify,
            action_output,
            timeout_sec,
            poll_interval_sec,
            logger or _LOGGER,
        )
    return action_output


def _wait_for_completion(
    siemplify: Any,
    action_output: ActionOutput,
    timeout_sec: int,
    poll_interval_sec: int,
    logger: logging.Logger,
) -> ActionOutput:
    """Polls the action result until it is completed or timeout is reached."""
    if action_output.execution_state != ExecutionState.IN_PROGRESS:
        return action_output

    result_id = action_output.id
    if not result_id:
        return action_output

    logger.info(
        f"Action is in progress. Waiting internally for up to {timeout_sec} seconds "
        f"(polling every {poll_interval_sec} seconds)..."
    )
    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        time.sleep(poll_interval_sec)
        logger.info(f"Polling action result ID '{result_id}'...")
        action_output = get_action_result(
            siemplify,
            result_id,
            logger=logger,
            wait_for_result=False,
        )
        if action_output.execution_state != ExecutionState.IN_PROGRESS:
            logger.info(f"Action finished with state: {action_output.execution_state}")
            return action_output

    logger.info("Timeout reached while waiting for action completion internally.")
    return action_output


def _resolve_integration_instance(siemplify: Any, integration_identifier: str, instance: str) -> str:
    """Resolves the correct integration instance identifier based on the provided strategy."""
    if instance == "auto":
        # Determine environment to query
        env = getattr(siemplify.current_alert, "environment", None) or siemplify.environment
        instances = get_installed_integrations_of_environment(siemplify, env, integration_identifier)
        if not instances:
            # Fall back to shared
            instances = get_installed_integrations_of_environment(siemplify, "Shared Instances", integration_identifier)

        if not instances:
            raise RuntimeError(f"Could not find any installed instance for integration '{integration_identifier}'")
        return instances[0].identifier
    elif instance == "shared":
        instances = get_installed_integrations_of_environment(siemplify, "Shared Instances", integration_identifier)
        if not instances:
            raise RuntimeError(f"Could not find any installed instance for integration '{integration_identifier}'")
        return instances[0].identifier

    # Explicit instance identifier provided
    return instance


def _build_entity_payload(siemplify: Any, case_id: int, ent: Any) -> dict[str, Any]:
    """Constructs the entity payload dictionary from a given entity object."""
    return {
        "caseId": case_id,
        "identifier": ent.identifier,
        "entityType": ent.entity_type,
        "isInternal": ent.is_internal,
        "isSuspicious": ent.is_suspicious,
        "isArtifact": ent.is_artifact,
        "isEnriched": getattr(ent, "is_enriched", False),
        "isVulnerable": getattr(ent, "is_vulnerable", False),
        "isPivot": getattr(ent, "is_pivot", False),
        "environment": getattr(ent, "environment", None)
        or getattr(siemplify.current_alert, "environment", None)
        or siemplify.environment,
    }


def _validate_and_populate_action_parameters(
    siemplify: Any,
    integration_identifier: str,
    full_action_name: str,
    action_parameters: dict[str, Any],
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """Validates required action parameters and populates missing ones with default values."""
    logger = logger or _LOGGER
    action_params_copy = action_parameters.copy()
    try:
        action_defs = get_env_action_def_files(siemplify)
        matching_action_def = None

        if isinstance(action_defs, list):
            for action_def in action_defs:
                if (
                    isinstance(action_def, dict)
                    and action_def.get("IntegrationIdentifier") == integration_identifier
                    and action_def.get("Name") == full_action_name
                ):
                    matching_action_def = action_def
                    break

        if matching_action_def:
            for param in matching_action_def.get("Parameters", []):
                param_name = param.get("Name")
                default_val = param.get("DefaultValue")
                is_mandatory = param.get("IsMandatory", False)

                if param_name:
                    if param_name not in action_params_copy:
                        # If mandatory and no default value is defined, raise exception
                        if is_mandatory and (default_val is None or default_val == ""):
                            raise ValueError(
                                f"Mandatory parameter '{param_name}' is missing for action '{full_action_name}'."
                            )

                        # Populate with default value if it exists, otherwise empty string
                        if default_val is not None:
                            action_params_copy[param_name] = default_val
                        else:
                            action_params_copy[param_name] = ""
                    else:
                        # Param is present, check if it's empty and mandatory
                        param_value = action_params_copy[param_name]
                        if is_mandatory and (param_value is None or param_value == ""):
                            raise ValueError(
                                f"Mandatory parameter '{param_name}' has an empty "
                                f"value for action '{full_action_name}'."
                            )
    except ValueError:
        # Mandatory parameter missing should propagate as an error
        logger.exception("Validation of action parameters failed.")
        raise
    except Exception as e:
        logger.warn(
            "Failed to fetch action definitions to populate default parameters: %s. "
            "Proceeding with provided action parameters.",
            e,
        )
    return action_params_copy


def execute_orchestrated_action(
    siemplify: Any,
    integration_identifier: str,
    action_name: str,
    *,
    instance: str = "auto",
    action_parameters: dict[str, Any] | None = None,
    entity_scope: str = "inherit",
    entity_identifiers: str | None = None,
    action_provider: str = "Scripts",
    logger: logging.Logger | None = None,
    wait_for_result: bool = True,
    timeout_sec: int = 120,
    poll_interval_sec: int = 30,
) -> ActionOutput:
    """Resolves correct integration instance and triggers the manual action.

    Args:
        siemplify: ChronicleSOAR/SiemplifyAction object.
        integration_identifier (str): Identifier of the integration (e.g. 'GoogleThreatIntelligence').
        action_name (str): Name of the action to execute (e.g. 'Ping').
        instance (str): Instance selection mode ('auto', 'shared' or explicit instance name). Defaults to 'auto'.
        action_parameters (dict[str, Any] | None): Dictionary of action parameters. Defaults to empty dict.
        entity_scope (str): Scope of entities ('inherit', 'custom' or predefined scope like 'All entities'). Defaults to 'inherit'.
        entity_identifiers (str | None): CSV list of entity identifiers to use if entity_scope is 'custom'. Defaults to None.
        action_provider (str): Action provider name. Defaults to 'Scripts'.
        logger: Optional logger to use.
        wait_for_result: Whether to wait/poll internally if result is pending.
        timeout_sec: Maximum time to wait in seconds.
        poll_interval_sec: Interval between poll requests in seconds.

    Returns:
        ActionOutput: Action execution output object.
    """
    logger = logger or _LOGGER
    if action_parameters is None:
        action_parameters = {}
    # 1. Resolve integration instance
    instance_id = _resolve_integration_instance(siemplify, integration_identifier, instance)

    # 2. Extract Alert / Case details
    case_id = siemplify.case_id
    alert_group_identifier = siemplify.current_alert.alert_group_identifier

    # 3. Handle entities
    payload_entities = []
    scope = ""
    is_predefined_scope = False

    if entity_scope == "inherit":
        scope = ""
        is_predefined_scope = False
        for ent in siemplify.current_alert.entities:
            payload_entities.append(_build_entity_payload(siemplify, case_id, ent))
    elif entity_scope == "custom":
        scope = ""
        is_predefined_scope = False
        if not entity_identifiers:
            raise ValueError("entity_identifiers must be provided when entity_scope is 'custom'")

        identifiers = [e.strip() for e in entity_identifiers.split(",")]
        alert_entities_map = {ent.identifier: ent for ent in siemplify.current_alert.entities}

        for identifier in identifiers:
            if identifier not in alert_entities_map:
                raise ValueError(f"entity not found in the scope of the alert: {identifier}")
            ent = alert_entities_map[identifier]
            payload_entities.append(_build_entity_payload(siemplify, case_id, ent))
    else:
        # Predefined scope like "All entities", "Internal entities", etc.
        scope = entity_scope
        is_predefined_scope = True
        payload_entities = []

    full_action_name = f"{integration_identifier}_{action_name}"

    # Fetch action definitions and populate default parameter values if missing
    action_parameters = _validate_and_populate_action_parameters(
        siemplify, integration_identifier, full_action_name, action_parameters, logger
    )

    action_properties = {
        "ScriptName": full_action_name,
        "ScriptParametersEntityFields": json.dumps({k: str(v) for k, v in action_parameters.items()}),
        "IntegrationInstance": instance_id,
    }

    # 4. Trigger manual action
    try:
        response = execute_manual_action(
            chronicle_soar=siemplify,
            case_id=case_id,
            action_name=full_action_name,
            action_properties=action_properties,
            alert_group_identifiers=[alert_group_identifier],
            scope=scope,
            target_entities=payload_entities,
            is_predefined_scope=is_predefined_scope,
            action_provider=action_provider,
        )
        response_json = response.json()
        logger.info(
            "Manual action triggered successfully. Response details: %s",
            json.dumps(response_json),
        )
        action_output = _build_action_output(response_json, chronicle_soar=siemplify, logger=logger)
        if wait_for_result:
            action_output = _wait_for_completion(
                siemplify,
                action_output,
                timeout_sec,
                poll_interval_sec,
                logger or _LOGGER,
            )
        return action_output
    except Exception as e:
        error_details = {
            "error_message": str(e),
            "case_id": case_id,
            "action_name": full_action_name,
            "action_properties": action_properties,
            "alert_group_identifiers": [alert_group_identifier],
            "scope": scope,
            "is_predefined_scope": is_predefined_scope,
            "payload_entities": payload_entities,
            "action_provider": action_provider,
        }
        if hasattr(e, "response") and e.response is not None:
            error_details["response_status_code"] = getattr(e.response, "status_code", None)
            with contextlib.suppress(Exception):
                error_details["response_text"] = e.response.text

        logger.exception(
            "Execution call failed. API response/error details: %s",
            json.dumps(error_details),
        )
        raise
