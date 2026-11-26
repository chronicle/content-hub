"""Shared TIPCommon BaseAction subclasses for the Rubrik Security Cloud actions."""

from __future__ import annotations

import base64
import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from TIPCommon.base.action import Action
from TIPCommon.base.action.data_models import Attachment, ExecutionState
from TIPCommon.exceptions import ActionSetupError
from TIPCommon.extraction import extract_action_param

from .api_manager import APIManager
from .constants import FILE_STATE_FAILED, FILE_STATE_READY
from .rubrik_exceptions import (
    ConnectionTimeoutException,
    GraphQLQueryException,
    InternalServerError,
    ItemNotFoundException,
    RateLimitException,
    RubrikException,
    UnauthorizedErrorException,
)
from .utils import get_integration_params, validate_required_string, validate_uuid_format

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

AUTHENTICATION_FAILURE_PREFIX: str = "Authentication failed"
MISSING_POLLING_STATE_MESSAGE: str = "Missing async polling state in additional_data."

# How long after triggering to keep looking for the file (and to keep retrying RSC calls
# that fail transiently) before giving up. Each async run makes one attempt; the step's
# async polling interval sets how often that happens.
FILE_LISTING_TIMEOUT_SECONDS: int = 600

# RSC errors worth another attempt on the next async run rather than failing the action.
TRANSIENT_EXCEPTIONS: tuple[type[Exception], ...] = (
    ConnectionTimeoutException,
    RateLimitException,
    InternalServerError,
)


class RubrikAction(Action, ABC):
    """Base action: integration parameters, the RSC client and failure messages.

    On failure TIPCommon reports "<error_output_message>\\nReason: <error>"; the
    prefix is chosen here from the exception type so every action words
    authentication and API errors the same way.

    Attributes:
        graphql_error_prefix: Prefix for GraphQL errors, e.g. "API error during
            Search DSPM Violations". "GraphQL errors" is appended to it.
        rubrik_error_prefix: Prefix for any other RSC error, e.g. "Failed to
            generate remediation log".
    """

    graphql_error_prefix: str | None = None
    rubrik_error_prefix: str | None = None

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.error_output_message = f"Error while executing action {name}"

    def _extract_action_parameters(self) -> None:
        service_account_json, verify_ssl = get_integration_params(self.soar_action)
        self.params.service_account_json = service_account_json
        self.params.verify_ssl = verify_ssl

    def _init_api_clients(self) -> APIManager:
        return APIManager(
            self.params.service_account_json,
            verify_ssl=self.params.verify_ssl,
            siemplify=self.soar_action,
        )

    def _extract_string_param(self, param_name: str, is_mandatory: bool = False) -> str | None:
        """Extract a string action parameter and print its value to the log."""
        return extract_action_param(
            self.soar_action,
            param_name=param_name,
            input_type=str,
            is_mandatory=is_mandatory,
            print_value=True,
        )

    def _finalize_action_on_failure(self, error: Exception) -> None:
        cause = error.__cause__ if isinstance(error, ActionSetupError) else error
        if isinstance(cause, UnauthorizedErrorException):
            self.error_output_message = AUTHENTICATION_FAILURE_PREFIX
        elif isinstance(cause, GraphQLQueryException) and self.graphql_error_prefix:
            self.error_output_message = f"{self.graphql_error_prefix}: GraphQL errors"
        elif isinstance(cause, RubrikException) and self.rubrik_error_prefix:
            self.error_output_message = self.rubrik_error_prefix


def validate_uuid_param(value: str | None, param_name: str) -> str:
    """Validate a mandatory UUID parameter and return it stripped."""
    return validate_uuid_format(validate_required_string(value, param_name), param_name)


class RubrikFileDownloadAction(RubrikAction, ABC):
    """Async action: trigger an RSC file export, wait for it, attach it to the case.

    Run 1 validates the inputs against the violation and triggers generation.
    Each later run makes one attempt to locate the file in allUserFiles (by
    filename, created after the action started), then checks its state by
    externalId, and downloads + attaches it once READY. State between runs is
    carried in the action's result value as JSON.

    Subclasses set the class attributes below and implement _trigger_generation
    and _success_message.

    Attributes:
        file_type: allUserFiles type of the generated file.
        file_label: Human-readable name used in messages, e.g. "remediation log".
        default_filename: Attachment name when RSC returns no filename.
    """

    file_type: str
    file_label: str
    default_filename: str

    def __init__(self, name: str, is_first_run: bool | None = None) -> None:
        super().__init__(name)
        if is_first_run is not None:
            self._is_first_run = is_first_run
        self.context: SingleJson = {}

    @Action.result_value.setter
    def result_value(self, value: bool | str) -> None:
        """Allow the JSON polling state to be returned as the result value."""
        self._result_value = value

    def _extract_action_parameters(self) -> None:
        super()._extract_action_parameters()
        self.params.object_id = self._extract_string_param("Object ID", is_mandatory=True)
        self.params.violation_id = self._extract_string_param("Violation ID", is_mandatory=True)
        self.params.object_name = self._extract_string_param("Object Name")
        self.context = json.loads(
            extract_action_param(
                self.soar_action,
                param_name="additional_data",
                default_value="{}",
                print_value=True,
            )
            or "{}"
        )

    def _validate_params(self) -> None:
        self.params.object_id = validate_uuid_param(self.params.object_id, "Object ID")
        self.params.violation_id = validate_uuid_param(self.params.violation_id, "Violation ID")
        self.params.object_name = (self.params.object_name or "").strip()

    @abstractmethod
    def _trigger_generation(self) -> str:
        """Validate the inputs against the violation and trigger file generation.

        Returns:
            The filename fragment that identifies the triggered file.
        """

    @abstractmethod
    def _success_message(self, filename: str) -> str:
        """Output message once the file is attached to the case."""

    def _perform_action(self, _: object = None) -> None:
        if self.is_first_run:
            self._start_generation()
            return

        file_entry = self._poll_file()
        file_state = file_entry.get("state") if file_entry else None
        if file_state == FILE_STATE_READY:
            self._attach_file(file_entry)
        elif file_state == FILE_STATE_FAILED:
            raise RubrikException(f"File generation failed for type={self.file_type}.")
        else:
            self._wait(
                f"Waiting for {self.file_label} to be generated..."
                if self.context.get("external_id")
                else f"Waiting for RSC to list the {self.file_label}..."
            )

    def _fetch_violation(self) -> SingleJson:
        """Fetch the violation and check Object ID against its resourceId.

        Runs BEFORE triggering any generation, so mismatched inputs fail without
        creating a file in RSC. The same response also supplies the other
        details (object name, snapshotId) subclasses validate.
        """
        object_id: str = self.params.object_id
        violation_id: str = self.params.violation_id
        self.logger.info(
            "Step 1: Fetching violation details to validate inputs before triggering."
        )
        details_data = self.api_client.get_dspm_violation_details(violation_id)
        violation_raw = details_data.get("policyViolation") or {}

        expected_resource_id = violation_raw.get("resourceId") or ""
        if object_id.strip().lower() != expected_resource_id.strip().lower():
            raise ItemNotFoundException(
                f"Object ID '{object_id}' does not match the resource of violation ID "
                f"{violation_id} (expected '{expected_resource_id}')."
            )
        return violation_raw

    def _resolve_object_name(self, violation_raw: SingleJson) -> None:
        """Check Object Name against the violation, or fill it in when not given."""
        metadata = (violation_raw.get("resourceMetadata") or {}).get("metadata") or {}
        expected_object_name = metadata.get("name") or ""
        object_name = self.params.object_name
        if not object_name:
            self.params.object_name = expected_object_name
        elif object_name.strip().lower() != expected_object_name.strip().lower():
            raise ItemNotFoundException(
                f"No object found with name: '{object_name}'. "
                f"Expected object name for violation ID {self.params.violation_id}: "
                f"'{expected_object_name}'."
            )

    def _start_generation(self) -> None:
        # Captured BEFORE triggering generation: only files created after this
        # instant are considered ours when locating the externalId, which excludes
        # files from earlier triggers for the same object but another violation.
        action_started_at = datetime.now(timezone.utc)
        self.context["target_file_name"] = self._trigger_generation()
        self.context["started_at"] = action_started_at.isoformat()
        # RSC does not list a newly triggered file straight away, so it is located
        # on the following async runs instead of after a fixed wait.
        self._wait(f"Waiting for RSC to list the {self.file_label}...")

    def _poll_file(self) -> SingleJson | None:
        """Make this run's single attempt to locate the file and read its state."""
        started_at_raw = self.context.get("started_at")
        if not started_at_raw or not self.context.get("target_file_name"):
            raise RubrikException(MISSING_POLLING_STATE_MESSAGE)
        started_at = datetime.fromisoformat(started_at_raw)
        elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
        try:
            external_id = self.context.get("external_id") or self._locate_file(
                started_at, elapsed
            )
            if not external_id:
                return None
            self.logger.info(
                f"Step 4: Checking readiness of located file (externalId={external_id})."
            )
            return self.api_client.get_user_file_by_external_id(external_id)
        except TRANSIENT_EXCEPTIONS as e:
            if elapsed > FILE_LISTING_TIMEOUT_SECONDS:
                raise
            self.logger.warn(f"Transient RSC error, retrying on the next run: {e}")
            return None

    def _locate_file(self, started_at: datetime, elapsed: float) -> str | None:
        """Find the triggered file's externalId in allUserFiles, if listed yet."""
        target_file_name = self.context.get("target_file_name")
        if not target_file_name:
            raise RubrikException(MISSING_POLLING_STATE_MESSAGE)
        self.logger.info(
            f"Step 3: Locating triggered {self.file_label} (matching filename "
            f"containing '{target_file_name}', {elapsed:.0f}s after trigger)."
        )
        # RSC reports createdAt to the whole second, so a file created in the same
        # second the action started would look older than started_at and never
        # match. Compare against the start of that second instead.
        file_entry = self.api_client.find_user_file_by_filename(
            file_type=self.file_type,
            filename_contains=target_file_name,
            created_after=started_at.replace(microsecond=0) - timedelta(microseconds=1),
        )
        external_id = file_entry.get("externalId") if file_entry else None
        if external_id:
            self.context["external_id"] = external_id
            self.logger.info(f"Step 3 complete: File located (externalId={external_id}).")
        elif elapsed > FILE_LISTING_TIMEOUT_SECONDS:
            raise RubrikException(
                f"RSC did not list the {self.file_label} "
                f"('{target_file_name}') within {FILE_LISTING_TIMEOUT_SECONDS}s."
            )
        return external_id

    def _attach_file(self, file_entry: SingleJson) -> None:
        external_id = file_entry.get("externalId")
        filename = file_entry.get("filename") or self.default_filename
        self.logger.info(
            f"Step 4 complete: File ready. externalId={external_id} filename={filename}"
        )
        self.logger.info(f"Step 5: Downloading {self.file_label} externalId={external_id}.")
        file_bytes = self.api_client.download_file(external_id)
        self.logger.info(
            f"Step 5 complete: Downloaded {len(file_bytes)} bytes for '{filename}'."
        )
        self.attachments.append(
            Attachment(
                title=filename,
                filename=filename,
                file_contents=base64.b64encode(file_bytes).decode("utf-8"),
            )
        )
        self.output_message = self._success_message(filename)
        self.execution_state = ExecutionState.COMPLETED
        self.result_value = True

    def _wait(self, message: str) -> None:
        """End this run in progress, carrying the polling state to the next one."""
        self.output_message = message
        self.execution_state = ExecutionState.IN_PROGRESS
        self.result_value = json.dumps(self.context)
