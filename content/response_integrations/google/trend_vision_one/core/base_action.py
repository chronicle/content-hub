# Copyright 2026 Google LLC
# ruff: file-ignore[verbose-log-message]
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

import abc
import json
import sys
import time
from typing import TYPE_CHECKING, NoReturn

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon import (
    extract_action_param,
    extract_configuration_param,
    is_approaching_timeout,
)

from .constants import (
    DEFAULT_SLEEP_TIME,
    DEFAULT_TIMEOUT,
    ENRICHMENT_PREFIX,
    IN_BLOCKLIST_KEY,
    IN_PROGRESS_STATUSES,
    INTEGRATION_NAME,
    PARAM_DESCRIPTION,
    PAYLOAD_CHUNK_SIZE,
    SUCCESS_STATUS,
)
from .TrendVisionOneExceptions import TrendVisionOneTimeoutException
from .TrendVisionOneManager import TrendVisionOneManager
from .UtilsManager import (
    SUPPORTED_BLOCKLIST_ENTITY_TYPES,
    build_blocklist_payloads,
    get_entity_original_identifier,
    is_async_action_global_timeout_approaching,
)

if TYPE_CHECKING:
    from soar_sdk.SiemplifyDataModel import DomainEntityInfo
    from TIPCommon.types import SingleJson

    from . import datamodels

MIN_ARGV_FOR_ITERATION = 3

try:
    from TIPCommon.base.action import Action
except ImportError:

    class Action(abc.ABC):
        """Base SOAR Action class providing standard lifecycle hooks."""

        def __init__(self, name: str) -> None:
            self.name = name
            self.soar_action = SiemplifyAction()
            self.soar_action.script_name = name
            self.logger = self.soar_action.LOGGER
            self.api_client: TrendVisionOneManager | None = None
            self.params: SingleJson = {}
            self.execution_state: int = EXECUTION_STATE_COMPLETED
            self.output_message: str = ""
            self.result_value: bool | str = False
            self.action_start_time: int = unix_now()

        @abc.abstractmethod
        def _init_api_clients(self) -> TrendVisionOneManager:
            """Initialize and return the API client instance."""

        @abc.abstractmethod
        def _extract_action_parameters(self) -> None:
            """Extract action parameters into self.params."""

        @abc.abstractmethod
        def _perform_action(self, current_iteration: int = 0) -> None:
            """Execute the core action logic."""

        @output_handler
        def run(self) -> NoReturn:
            """Run the action lifecycle and terminate via soar_action.end."""
            is_first_run = (
                len(sys.argv) < MIN_ARGV_FOR_ITERATION or sys.argv[2] == "True"
            )
            self.logger.info("----------------- Main - Param Init -----------------")
            self._extract_action_parameters()
            self.logger.info("----------------- Main - Started -----------------")
            try:
                self.api_client = self._init_api_clients()
                self._perform_action(0 if is_first_run else 1)
            except Exception as error:
                self.execution_state = EXECUTION_STATE_FAILED
                self.result_value = False
                if not self.output_message:
                    self.output_message = (
                        f'Error executing action "{self.name}". Reason: {error}'
                    )
                self.logger.exception(error)

            self.logger.info("----------------- Main - Finished -----------------")
            self.logger.info(
                f"\n  status: {self.execution_state}"
                f"\n  results: {self.result_value}"
                f"\n  output_message: {self.output_message}"
            )
            self.soar_action.end(
                self.output_message, self.result_value, self.execution_state
            )


class BaseBlocklistAction(Action, abc.ABC):
    """Abstract base action encapsulating shared Trend Vision One blocklist workflow."""

    SCRIPT_NAME: str = ""
    ACTION_DISPLAY_NAME: str = ""
    ACTION_VERB: str = "added"
    ACTION_INFINITIVE: str = "add"
    ACTION_PREPOSITION: str = "to"
    RESULT_JSON_KEY: str = "added"
    ENRICHMENT_VALUE: bool = True
    INCLUDE_DESCRIPTION: bool = True

    def __init__(self) -> None:
        super().__init__(self.SCRIPT_NAME)
        self.entity_map: dict[str, str] = {}
        self.result_data: SingleJson = {}

    def _init_api_clients(self) -> TrendVisionOneManager:
        """Initialize and verify the TrendVisionOneManager client.

        Returns:
            Initialized TrendVisionOneManager instance.

        """
        api_root = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="API Root",
            is_mandatory=True,
            print_value=True,
        )
        api_token = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="API Token",
            is_mandatory=True,
            remove_whitespaces=False,
        )
        verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="Verify SSL",
            is_mandatory=True,
            input_type=bool,
            print_value=True,
        )
        manager = TrendVisionOneManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify=self.soar_action,
        )
        manager.test_connectivity()
        return manager

    def _extract_action_parameters(self) -> None:
        """Extract action-specific parameters."""
        self.params["description"] = (
            extract_action_param(
                self.soar_action,
                param_name=PARAM_DESCRIPTION,
                is_mandatory=False,
            )
            if self.INCLUDE_DESCRIPTION
            else None
        )
        self.params["additional_data"] = extract_action_param(
            self.soar_action,
            param_name="additional_data",
            default_value="{}",
        )

    @abc.abstractmethod
    def _submit_chunk(
        self, chunk: list[SingleJson]
    ) -> list[datamodels.BlocklistResponse]:
        """Submit a batch of suspicious objects to the appropriate manager method."""

    def _perform_action(self, current_iteration: int = 0) -> None:
        """Execute either initial submission or async task polling."""
        suitable_entities = [
            entity
            for entity in self.soar_action.target_entities
            if entity.entity_type in SUPPORTED_BLOCKLIST_ENTITY_TYPES
        ]
        try:
            if current_iteration == 0:
                self._start_blocklist_operation(suitable_entities)
            else:
                self.result_data = json.loads(
                    self.params.get("additional_data") or "{}"
                )
                self._poll_and_finalize(suitable_entities)
        except TrendVisionOneTimeoutException as error:
            self.output_message = f"{error}"
            self.execution_state = EXECUTION_STATE_FAILED
            self.result_value = False
            if self.result_data:
                self.soar_action.result.add_result_json(
                    {
                        self.RESULT_JSON_KEY: self.result_data.get("completed", []),
                        "failed": self.result_data.get("failed", []),
                    }
                )
            self.logger.exception(error)
        except Exception as error:
            self.output_message = (
                f'Error executing action "{self.ACTION_DISPLAY_NAME}". Reason: {error}'
            )
            self.execution_state = EXECUTION_STATE_FAILED
            self.result_value = False
            self.logger.exception(error)

    def _start_blocklist_operation(
        self, suitable_entities: list[DomainEntityInfo]
    ) -> None:
        """Build suspicious object payloads, submit chunks, and begin status polling."""
        payloads, self.entity_map = build_blocklist_payloads(
            siemplify=self.soar_action,
            suitable_entities=suitable_entities,
            description=self.params.get("description"),
            include_description=self.INCLUDE_DESCRIPTION,
        )
        if not payloads:
            self.output_message = (
                "No supported entities or parameters were provided "
                f"to be {self.ACTION_VERB}."
            )
            self.soar_action.result.add_result_json(
                {self.RESULT_JSON_KEY: [], "failed": []}
            )
            self.result_value = False
            self.execution_state = EXECUTION_STATE_COMPLETED
            return

        self.result_data = {
            "result_urls": {},
            "json_results": {},
            "completed": [],
            "failed": [],
            "pending": [],
        }
        # Submit in chunks of PAYLOAD_CHUNK_SIZE
        for idx in range(0, len(payloads), PAYLOAD_CHUNK_SIZE):
            chunk = payloads[idx : idx + PAYLOAD_CHUNK_SIZE]
            self._process_single_chunk(chunk)

        if self.result_data.get("result_urls"):
            time.sleep(DEFAULT_SLEEP_TIME)

        self._poll_and_finalize(suitable_entities)

    def _process_single_chunk(self, chunk: list[SingleJson]) -> None:
        """Submit a single chunk of payloads and record per-item responses."""
        try:
            responses = self._submit_chunk(chunk)
        except Exception as error:
            self.logger.exception(error)
            for item in chunk:
                norm_val = next(v for k, v in item.items() if k != "description")
                orig_id = self.entity_map.get(norm_val, norm_val)
                self.result_data["failed"].append(orig_id)
            return

        if len(responses) == 1 and len(chunk) > 1:
            responses *= len(chunk)
        self._record_chunk_responses(chunk, responses)

    def _record_chunk_responses(
        self,
        chunk: list[SingleJson],
        responses: list[datamodels.BlocklistResponse],
    ) -> None:
        """Record task URLs, immediate completions, or failures for a submitted chunk."""
        for item, response in zip(chunk, responses, strict=False):
            norm_val = next(v for k, v in item.items() if k != "description")
            orig_id = self.entity_map.get(norm_val, norm_val)
            if response.url or response.id:
                self.result_data["result_urls"][orig_id] = response.url or response.id
                self.result_data["pending"].append(orig_id)
            elif getattr(response, "is_success", False):
                self.logger.info(f"Successfully {self.ACTION_VERB} entity {orig_id}")
                if orig_id not in self.result_data["completed"]:
                    self.result_data["completed"].append(orig_id)
            else:
                self.logger.error(
                    f"Failed to submit {orig_id} to blocklist. Error: {response.error_message}"
                )
                self.result_data["failed"].append(orig_id)

        for item in chunk[len(responses) :]:
            norm_val = next(v for k, v in item.items() if k != "description")
            orig_id = self.entity_map.get(norm_val, norm_val)
            self.logger.error(
                f"Missing response for {orig_id} when submitting to blocklist."
            )
            self.result_data["failed"].append(orig_id)

    def _poll_and_finalize(self, suitable_entities: list[DomainEntityInfo]) -> None:
        """Poll pending tasks once and finalize or defer execution."""
        self._poll_pending_tasks(self.result_data)
        self._finalize_blocklist_operation(self.result_data, suitable_entities)

    def _poll_pending_tasks(self, result_data: SingleJson) -> None:
        """Query each pending task URL once per async execution pass."""
        for entity_id, task_ref in list(result_data.get("result_urls", {}).items()):
            if not task_ref:
                continue
            self._check_timeout(result_data)
            try:
                task_details = self.api_client.get_task_by_id_or_url(task_ref)
            except Exception as error:
                self.logger.exception(error)
                self._mark_task_terminal(result_data, entity_id, is_success=False)
                continue

            result_data["json_results"][entity_id] = {
                "task_id": task_details.id,
                "status": task_details.status,
            }
            if task_details.status == SUCCESS_STATUS:
                self.logger.info(f"Successfully {self.ACTION_VERB} entity {entity_id}")
                self._mark_task_terminal(result_data, entity_id, is_success=True)
            elif task_details.status not in IN_PROGRESS_STATUSES:
                # Catch failed, rejected, cancelled, expired, etc.
                self.logger.error(
                    f"Task {task_details.id} for entity {entity_id} "
                    f"ended with status: {task_details.status}"
                )
                self._mark_task_terminal(result_data, entity_id, is_success=False)

        result_data["result_urls"] = {
            k: v for k, v in result_data["result_urls"].items() if v
        }

    def _check_timeout(self, result_data: SingleJson) -> None:
        """Raise TrendVisionOneTimeoutException if global or action timeout is approaching.

        Args:
            result_data: Action execution state tracking pending URLs and results.

        Raises:
            TrendVisionOneTimeoutException: If the execution deadline is approaching.

        """
        if is_async_action_global_timeout_approaching(
            self.soar_action, self.action_start_time
        ) or is_approaching_timeout(self.action_start_time, DEFAULT_TIMEOUT):
            pending_ids = [
                t_ref for t_ref in result_data["result_urls"].values() if t_ref
            ]
            msg = (
                f"action ran into a timeout during execution. Pending tasks: {pending_ids}. "
                "Please increase the timeout in IDE."
            )
            raise TrendVisionOneTimeoutException(msg)

    @staticmethod
    def _mark_task_terminal(
        result_data: SingleJson, entity_id: str, *, is_success: bool
    ) -> None:
        """Move an entity from pending to completed or failed."""
        result_data["result_urls"][entity_id] = None
        target_bucket = "completed" if is_success else "failed"
        if entity_id not in result_data[target_bucket]:
            result_data[target_bucket].append(entity_id)
        if entity_id in result_data["pending"]:
            result_data["pending"].remove(entity_id)

    def _finalize_blocklist_operation(
        self, result_data: SingleJson, suitable_entities: list[DomainEntityInfo]
    ) -> None:
        """Set final output message, JSON result, entity enrichment, and execution state."""
        if any(result_data["result_urls"].values()):
            pending_tasks = [v for v in result_data["result_urls"].values() if v]
            self.output_message = f"Pending tasks to finish: {', '.join(pending_tasks)}"
            self.result_value = json.dumps(result_data)
            self.execution_state = EXECUTION_STATE_INPROGRESS
            return

        self.execution_state = EXECUTION_STATE_COMPLETED
        if (
            result_data["json_results"]
            or result_data["completed"]
            or result_data["failed"]
        ):
            self.soar_action.result.add_result_json(
                {
                    self.RESULT_JSON_KEY: result_data["completed"],
                    "failed": result_data["failed"],
                }
            )

        # Enrich entities
        self._enrich_completed_entities(result_data["completed"], suitable_entities)
        self.output_message, self.result_value = self._build_completion_message(
            result_data
        )

    def _enrich_completed_entities(
        self, completed_items: list[str], suitable_entities: list[DomainEntityInfo]
    ) -> None:
        """Enrich completed Chronicle entities and update them only when modified."""
        completed_lower = {str(x).strip().lower() for x in completed_items}
        enrichment_key = f"{ENRICHMENT_PREFIX}_{IN_BLOCKLIST_KEY}"
        updated_entities: list[DomainEntityInfo] = []
        for entity in suitable_entities:
            entity_id = get_entity_original_identifier(entity).strip()
            if entity_id in completed_items or entity_id.lower() in completed_lower:
                entity.additional_properties.update(
                    {enrichment_key: self.ENRICHMENT_VALUE}
                )
                entity.is_enriched = True
                updated_entities.append(entity)

        if updated_entities:
            self.soar_action.update_entities(updated_entities)

    def _build_completion_message(
        self, result_data: SingleJson
    ) -> tuple[str, bool]:
        """Build human-readable output message and boolean result value.

        Args:
            result_data: Action execution state containing completed and failed items.

        Returns:
            Tuple of (output_message, result_value).

        """
        if result_data["completed"]:
            completed_str = ", ".join(result_data["completed"])
            output_message = (
                f"Successfully {self.ACTION_VERB} the following entities "
                f"{self.ACTION_PREPOSITION} the blocklist in Trend Vision One: "
                f"{completed_str}."
            )
            if result_data["failed"]:
                failed_str = ", ".join(result_data["failed"])
                output_message += (
                    f"\nAction wasn't able to {self.ACTION_INFINITIVE} the following "
                    f"entities in Trend Vision One: {failed_str}."
                )
                return output_message, False
            return output_message, True

        output_message = (
            f"None of the provided entities were {self.ACTION_VERB} "
            f"{self.ACTION_PREPOSITION} the blocklist in Trend Vision One."
        )
        return output_message, False
