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

import contextlib
import dataclasses
import gzip
import hashlib
import re
import zlib
from typing import TYPE_CHECKING

import requests
from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.consts import BLACKLIST_FILTER, WHITELIST_FILTER
from TIPCommon.exceptions import ActionSetupError, ParameterExtractionError

from .constants import (
    ABSOLUTE_PATH_PATTERN,
    GZIP_MAGIC_BYTES,
    HTTP_STATUS_ERROR_TYPES,
    LIVE_RESPONSE_FILE_NOT_FOUND_MARKER,
    LIVE_RESPONSE_STATUS_ERROR_TYPES,
    SUMMARY_NONE,
    SYSTEM_ROOT_PATH,
    TOKEN_ERROR_MARKER,
    ErrorType,
)
from .exceptions import DefenderActiveRequestExistsException, DefenderException, DefenderNotFoundException
from .MicrosoftDefenderATPManager import (
    MicrosoftDefenderATPError,
    MicrosoftDefenderATPForbiddenError,
    MicrosoftDefenderATPManager,
    MicrosoftDefenderATPManagerV2,
    MicrosoftDefenderATPValidationError,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping

    from soar_sdk.SiemplifyAction import SiemplifyAction
    from soar_sdk.SiemplifyDataModel import DomainEntityInfo
    from soar_sdk.SiemplifyLogger import SiemplifyLogger
    from TIPCommon.types import ChronicleSOAR, SingleJson

    from .datamodels import MachineTask

UNIX_FORMAT = 1
DATETIME_FORMAT = 2


def pass_whitelist_filter(
    siemplify, whitelist_as_a_blacklist, model, model_key, whitelist=None
):
    # whitelist filter
    whitelist = whitelist or siemplify.whitelist
    whitelist_filter_type = (
        BLACKLIST_FILTER if whitelist_as_a_blacklist else WHITELIST_FILTER
    )
    model_value = getattr(model, model_key)
    model_values = model_value if isinstance(model_value, list) else [model_value]

    if whitelist:
        for value in model_values:
            if whitelist_filter_type == BLACKLIST_FILTER and value in whitelist:
                siemplify.LOGGER.info(f"'{value}' did not pass blacklist filter.")
                return False

            if whitelist_filter_type == WHITELIST_FILTER and value not in whitelist:
                siemplify.LOGGER.info(f"'{value}' did not pass whitelist filter.")
                return False

    return True


def is_valid_domain(domain_name):
    regex = "^((?!-)[A-Za-z0-9-]" + "{1,63}(?<!-)\\.)" + "+[A-Za-z]{2,6}"
    p = re.compile(regex)

    if domain_name is None:
        return False

    if re.search(p, domain_name):
        return True
    else:
        return False


def get_entity_original_identifier(entity):
    """
    Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


def normalize_mde_file_path(path: str) -> str:
    """Normalize an endpoint path for the Live Response GetFile command.

    Expands %systemroot% (case-insensitive) and collapses repeated backslashes,
    preserving a leading UNC prefix.

    Args:
        path: File path on the endpoint.

    Returns:
        The normalized absolute path.

    Raises:
        ValueError: If the normalized path is not a drive-letter, UNC or POSIX path.
    """
    expanded = re.sub(r"%systemroot%", lambda _: SYSTEM_ROOT_PATH, path.strip(), flags=re.IGNORECASE)
    collapsed = re.sub(r"\\{2,}", r"\\", expanded)
    normalized = f"\\{collapsed}" if expanded.startswith("\\\\") else collapsed
    if not re.match(ABSOLUTE_PATH_PATTERN, normalized):
        raise ValueError(f"File path must be an absolute path: {path}")

    return normalized


def hash_acquired_file(raw: bytes) -> SingleJson:
    """Compute hashes of a file acquired via Live Response.

    Gzip payloads (the MDE GetFile format) are hashed after decompression.

    Args:
        raw: Downloaded file bytes.

    Returns:
        The md5, sha1, sha256, size and is_gzip of the (decompressed) content.

    Raises:
        DefenderException: If a gzip payload cannot be decompressed.
    """
    is_gzip = raw[:2] == GZIP_MAGIC_BYTES
    content = raw
    if is_gzip:
        try:
            content = gzip.decompress(raw)
        except (gzip.BadGzipFile, EOFError, zlib.error) as error:
            raise DefenderException(f"Failed to decompress the acquired file: {error}") from error

    return {
        "md5": hashlib.md5(content).hexdigest(),
        "sha1": hashlib.sha1(content).hexdigest(),
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
        "is_gzip": is_gzip,
    }


@dataclasses.dataclass(slots=True)
class ContainmentTaskSpec:
    """Inputs for starting or reusing a machine containment task.

    Attributes:
        action_type: Containment action type (Isolate or Unisolate).
        start_task: Callable that starts the task for a resolved machine ID.
        logger: Siemplify logger.
    """

    action_type: str
    start_task: Callable[[str], MachineTask]
    logger: SiemplifyLogger


@dataclasses.dataclass(slots=True)
class ContainmentByMachineIdResult:
    """Result of creating or reusing a containment task by Machine ID.

    Attributes:
        tasks: Created or reused containment tasks.
        output_messages: Output messages for the action result.
        result_value: Action result value ("true" or "false").
        error_type: Error type if failed, else None.
    """

    tasks: list[MachineTask]
    output_messages: list[str]
    result_value: str
    error_type: str | None = None


def start_or_reuse_containment_task(
    manager: MicrosoftDefenderATPManager,
    machine_id: str,
    spec: ContainmentTaskSpec,
) -> tuple[MachineTask, str]:
    """Start a containment task, reusing an active task of the same type if one exists.

    Args:
        manager: Defender manager instance.
        machine_id: Target machine ID.
        spec: Containment task specification.

    Returns:
        A tuple of (task, outcome), where outcome describes whether the task
        was created or reused.
    """
    try:
        return spec.start_task(machine_id), "was created successfully"
    except DefenderActiveRequestExistsException:
        return manager.get_active_containment_task(machine_id, spec.action_type), "already exists"


def create_containment_task_by_machine_id(
    manager: MicrosoftDefenderATPManager,
    machine_id: str,
    spec: ContainmentTaskSpec,
) -> ContainmentByMachineIdResult:
    """Look up a machine by Machine ID and start an isolate or unisolate task on it.

    Args:
        manager: Defender manager instance.
        machine_id: Target machine ID.
        spec: Containment task specification.

    Returns:
        The containment result containing tasks, output messages, result value,
        and error type.
    """
    try:
        try:
            machine = manager.get_machine_by_id(machine_id)
        except DefenderNotFoundException:
            msg = f"Failed to find machine ATP by Machine ID: {machine_id}"
            spec.logger.warn(msg)

            return ContainmentByMachineIdResult(
                tasks=[],
                output_messages=[msg, "1 entities were not found in ATP"],
                result_value="false",
                error_type=ErrorType.ENDPOINT_NOT_FOUND,
            )
        task, outcome = start_or_reuse_containment_task(manager, machine.id, spec)
    except (MicrosoftDefenderATPError, DefenderException) as error:
        spec.logger.exception(f"Failed to process Machine ID {machine_id}: {error}")

        return ContainmentByMachineIdResult(
            tasks=[],
            output_messages=[f"Failed to process Machine ID {machine_id}. {error}"],
            result_value="false",
            error_type=classify_exception(error)[0],
        )

    msg = f"{spec.action_type} machine task {task.id} {outcome} on Defender ATP Server for {machine_id}"
    spec.logger.info(msg)

    return ContainmentByMachineIdResult(tasks=[task], output_messages=[msg], result_value="true")


@dataclasses.dataclass(slots=True)
class DefenderATPManagerConfig:
    client_id: str
    client_secret: str
    tenant_id: str
    resource: str
    chronicle_soar: ChronicleSOAR
    login_api_root: str = None
    defender_api_resource: str = None
    verify_ssl: bool = False
    entities_scope: bool = False
    microsoft_graph_url: str = None


def init_defender_atp_manager(
    config: DefenderATPManagerConfig,
) -> MicrosoftDefenderATPManager | MicrosoftDefenderATPManagerV2:
    """Returns the correct Microsoft Defender ATP Manager based on API version.
    Args:
        config(DefenderATPManagerConfig): Configuration params.

    Returns:
        MicrosoftDefenderATPManager | MicrosoftDefenderATPManagerV2: Microsoft Defender
        ATP Manager.
    """
    if config.microsoft_graph_url:
        manager_class = MicrosoftDefenderATPManagerV2
    else:
        manager_class = MicrosoftDefenderATPManager

    kwargs = {
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "tenant_id": config.tenant_id,
        "resource": config.resource,
        "login_api_root": config.login_api_root,
        "defender_api_resource": config.defender_api_resource,
        "verify_ssl": config.verify_ssl,
        "entities_scope": config.entities_scope,
        "siemplify": config.chronicle_soar,
    }

    if config.microsoft_graph_url and manager_class == MicrosoftDefenderATPManagerV2:
        return manager_class(microsoft_graph_url=config.microsoft_graph_url, **kwargs)

    return manager_class(**kwargs)


# Wrappers whose inner exception holds the real failure reason.
_UNWRAPPED_EXCEPTIONS: tuple[type[Exception], ...] = (ActionSetupError, ParameterExtractionError)
_EXCEPTION_ERROR_TYPES: tuple[tuple[type[Exception], ErrorType], ...] = (
    (DefenderNotFoundException, ErrorType.ENDPOINT_NOT_FOUND),
    (MicrosoftDefenderATPForbiddenError, ErrorType.PERMISSION_DENIED),
    (MicrosoftDefenderATPValidationError, ErrorType.INVALID_INPUT),
    (requests.ConnectionError, ErrorType.CONNECTION_ERROR),
    (requests.Timeout, ErrorType.CONNECTION_ERROR),
    (ActionSetupError, ErrorType.CONFIGURATION_ERROR),
    (ParameterExtractionError, ErrorType.INVALID_INPUT),
)


def _get_http_status(error: BaseException) -> int | None:
    """Return the HTTP status tied to an exception.

    Args:
        error: Exception to inspect.

    Returns:
        Status from the exception, its response, or the response of the exception it was raised from.
    """
    inner = error.__cause__ or error.__context__
    for source in (error, getattr(error, "response", None), getattr(inner, "response", None)):
        status: object = getattr(source, "status_code", None)
        if isinstance(status, int) and not isinstance(status, bool):
            return status

    return None


def _get_class_error_type(error: BaseException) -> ErrorType | None:
    """Return the error type mapped to the exception class.

    Args:
        error: Exception to classify.

    Returns:
        Mapped error type, or None if the class is not mapped.
    """
    return next((error_type for cls, error_type in _EXCEPTION_ERROR_TYPES if isinstance(error, cls)), None)


def classify_exception(error: BaseException) -> tuple[str, str, int | None]:
    """Classify an exception for failure tagging and the action result summary.

    Setup and parameter wrappers are unwrapped first. If the inner exception is a plain
    Exception, or a not-found error raised during setup, the wrapper's type is used.

    Args:
        error: Exception to classify.

    Returns:
        Tuple of (error_type, exception class name, HTTP status or None).
    """
    wrapper_type: ErrorType | None = None
    while isinstance(error, _UNWRAPPED_EXCEPTIONS) and (error.__cause__ or error.__context__):
        wrapper_type = _get_class_error_type(error)
        error = error.__cause__ or error.__context__

    http_status = _get_http_status(error)
    error_type = _get_class_error_type(error)
    if error_type is None and http_status in HTTP_STATUS_ERROR_TYPES:
        error_type = HTTP_STATUS_ERROR_TYPES[http_status]
    is_server_error = http_status is not None and http_status >= 500
    if error_type is None and not is_server_error and TOKEN_ERROR_MARKER in str(error).lower():
        error_type = ErrorType.AUTHENTICATION_FAILED
    if error_type is None and http_status is not None and http_status >= 400:
        error_type = ErrorType.VENDOR_ERROR
    if error_type is None and isinstance(error, (MicrosoftDefenderATPError, DefenderException)):
        error_type = ErrorType.VENDOR_ERROR
    if wrapper_type and (
        error_type == ErrorType.ENDPOINT_NOT_FOUND or (not error_type and error.__class__ is Exception)
    ):
        error_type = wrapper_type

    return error_type or ErrorType.UNKNOWN_ERROR, type(error).__name__, http_status


def classify_live_response_failure(status: str, reason: str) -> ErrorType:
    """Classify a Live Response action that finished without success.

    Args:
        status: Final machine action status.
        reason: Command errors, or the status message if there are none.

    Returns:
        FILE_NOT_FOUND, TIMEOUT, CANCELLED, or VENDOR_ERROR for any other failure.
    """
    if LIVE_RESPONSE_FILE_NOT_FOUND_MARKER in reason.lower():
        return ErrorType.FILE_NOT_FOUND

    return LIVE_RESPONSE_STATUS_ERROR_TYPES.get(status, ErrorType.VENDOR_ERROR)


_ERROR_PRECEDENCE: dict[str, int] = {member.value: idx for idx, member in enumerate(ErrorType)}


def dominant_error_type(error_types: Iterable[str]) -> str | None:
    """Return the highest-precedence error type.

    Args:
        error_types: Error types of the failed targets and the run.

    Returns:
        The highest-precedence error type, or None if there is none. A type that is not in ErrorType
        ranks as, and is returned as, UNKNOWN_ERROR.
    """
    fallback_rank = _ERROR_PRECEDENCE[ErrorType.UNKNOWN_ERROR]
    dominant = min(error_types, key=lambda etype: _ERROR_PRECEDENCE.get(etype, fallback_rank), default=None)

    return dominant if dominant is None or dominant in _ERROR_PRECEDENCE else ErrorType.UNKNOWN_ERROR


@dataclasses.dataclass(slots=True)
class ActionResultSummaryInput:
    """Inputs required to format an ACTION_RESULT_SUMMARY log line.

    Attributes:
        execution_state: Final execution state.
        target_results: Target key to error type, or None for a successful target.
        skipped: Targets that were not attempted.
        unfinished: Targets in scope that have no result. They count as failed.
        error: Exception that ended the run, if any.
        error_type: Error type to report instead of the dominant one.
        fallback_error_type: Run-level error type to report if nothing succeeded and no failure has a
            reason. Defaults to INVALID_INPUT.
    """

    execution_state: ExecutionState | int
    target_results: Mapping[str, str | None]
    skipped: int = 0
    unfinished: int = 0
    error: BaseException | None = None
    error_type: str | None = None
    fallback_error_type: str | None = None


def build_action_result_summary(summary: ActionResultSummaryInput) -> str:
    """Build the ACTION_RESULT_SUMMARY log line.

    Args:
        summary: Execution state, per-target results, and run-level error of the finished run.

    Returns:
        The summary line. It holds only enums and counts.
    """
    run_type, exc_type, http_status = classify_exception(summary.error) if summary.error else (None, SUMMARY_NONE, None)
    failed_types = [etype for etype in summary.target_results.values() if etype]
    succeeded = len(summary.target_results) - len(failed_types)
    failed = len(failed_types) + summary.unfinished
    reason = summary.error_type or dominant_error_type([*failed_types, run_type] if run_type else failed_types)
    if reason is None and not succeeded:
        reason = summary.fallback_error_type or ErrorType.INVALID_INPUT
    outcome = "FAILURE" if not succeeded else "PARTIAL_SUCCESS" if failed else "SUCCESS"
    state = ExecutionState(summary.execution_state)
    state_name = "TIMEDOUT" if state is ExecutionState.TIMED_OUT else state.name

    return (
        f"ACTION_RESULT_SUMMARY v=1 outcome={outcome} error_type={reason or SUMMARY_NONE} "
        f"execution_state={state_name} targets={len(summary.target_results) + summary.unfinished} failed={failed} "
        f"skipped={summary.skipped} exc_type={exc_type} "
        f"http_status={SUMMARY_NONE if http_status is None else http_status}"
    )


def get_summary_scope(
    entities: Iterable[DomainEntityInfo],
    supported_types: Iterable[str],
    target_id: str | None,
) -> tuple[int, int]:
    """Count the targets in scope and the skipped entities for the result summary line.

    Args:
        entities: Target entities of the action.
        supported_types: Entity types that the action processes.
        target_id: Machine ID parameter. If set, it overrides the entities.

    Returns:
        A tuple of (targets in scope, skipped entities). A Machine ID is one target and no entity is skipped.
    """
    if target_id:
        return 1, 0

    entities = list(entities)
    supported = sum(entity.entity_type in supported_types for entity in entities)

    return supported, len(entities) - supported


def log_action_result_summary(logger: SiemplifyLogger, get_summary: Callable[[], ActionResultSummaryInput]) -> None:
    """Log the ACTION_RESULT_SUMMARY line. Never raise.

    Args:
        logger: Action logger.
        get_summary: Return the summary inputs for the finished run.
    """
    try:
        logger.info(build_action_result_summary(get_summary()))
    except Exception as err:
        with contextlib.suppress(Exception):
            logger.warn(f"Failed to log action result summary: {err}")


@dataclasses.dataclass(slots=True)
class ScopedSummaryLogger:
    """Log an ACTION_RESULT_SUMMARY line for a sync action's target scope.

    Attributes:
        siemplify: SiemplifyAction instance providing entities and logger.
        supported_types: Entity types handled by the action.
        machine_id: Optional Machine ID override.
        target_results: Target key to error type, or None for succeeded targets.
    """

    siemplify: SiemplifyAction
    supported_types: tuple[str, ...]
    machine_id: str | None
    target_results: dict[str, str | None] = dataclasses.field(default_factory=dict)

    def log(self, execution_state: ExecutionState | int, error: BaseException | None = None) -> None:
        """Build and log the ACTION_RESULT_SUMMARY line.

        Args:
            execution_state: Final execution state of the run.
            error: Exception that ended the run, if any.
        """
        def _build() -> ActionResultSummaryInput:
            targets, skipped = get_summary_scope(self.siemplify.target_entities, self.supported_types, self.machine_id)
            unfinished = max(targets - len(self.target_results), 0) if error else 0

            return ActionResultSummaryInput(
                execution_state=execution_state,
                target_results=self.target_results,
                skipped=skipped,
                unfinished=unfinished,
                error=error,
            )

        log_action_result_summary(self.siemplify.LOGGER, _build)
